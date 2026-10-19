import ctypes
import queue
import threading
import numpy as np
import soundcard as sc

RATE = 16000
CHUNK = 3


def init_com_thread():
    """Initialize Windows COM (MTA) for the calling thread."""
    try:
        res = ctypes.windll.ole32.CoInitializeEx(None, 0)  # COINIT_MULTITHREADED = 0
        return res in (0, 1)  # S_OK (0) or S_FALSE (1)
    except Exception:
        return False


def uninit_com_thread(inited):
    """Uninitialize Windows COM if it was initialized by init_com_thread."""
    if inited:
        try:
            ctypes.windll.ole32.CoUninitialize()
        except Exception:
            pass


def get_audio_devices():
    """Return names of available audio playback devices."""
    try:
        return [sp.name for sp in sc.all_speakers()]
    except Exception:
        return []


def get_default_device_name():
    """Return the name of the default audio playback device."""
    try:
        d = sc.default_speaker()
        return d.name if d else None
    except Exception:
        return None


def find_loopback_mic(device_name):
    """
    Locate or wrap a loopback recording endpoint for the given playback device.
    Uses a 4-step resolution strategy.
    """
    speakers = sc.all_speakers()
    sp = next((x for x in speakers if x.name == device_name), None)
    if sp is None:
        sp = sc.default_speaker()
    if sp is None and speakers:
        sp = speakers[0]
    if sp is None:
        raise RuntimeError(f"No audio playback device found matching '{device_name}'.")

    # Method 1: Match by ID in loopback microphones
    try:
        loopback_mics = [m for m in sc.all_microphones(include_loopback=True) if getattr(m, 'isloopback', False)]
        for m in loopback_mics:
            if getattr(m, 'id', None) == getattr(sp, 'id', None):
                return m
        for m in loopback_mics:
            if getattr(m, 'name', None) == getattr(sp, 'name', None):
                return m
    except Exception:
        pass

    # Method 2: Direct _Microphone wrapper on the speaker
    try:
        from soundcard.mediafoundation import _Microphone
        return _Microphone(sp, isloopback=True)
    except Exception:
        pass

    # Method 3: sc.get_microphone with ID
    try:
        return sc.get_microphone(id=str(sp.id), include_loopback=True)
    except Exception:
        pass

    # Method 4: sc.get_microphone with Name
    try:
        return sc.get_microphone(id=str(sp.name), include_loopback=True)
    except Exception:
        pass

    raise RuntimeError(f"No loopback audio endpoint available for '{sp.name}'.")


class AudioCaptureWorker:
    """Decoupled background worker for Windows loopback audio capture."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self.is_paused = False
        self.is_running = False

    def start(self, device_name, audio_queue, on_error_cb=None):
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(device_name, audio_queue, on_error_cb),
            daemon=True
        )
        self._thread.start()

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.is_paused = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run(self, device_name, audio_queue, on_error_cb):
        com_inited = init_com_thread()
        try:
            mic = find_loopback_mic(device_name)
            channels = min(mic.channels, 2) if mic.channels > 0 else 2
            with mic.recorder(samplerate=RATE, channels=channels) as rec:
                while not self._stop_event.is_set():
                    x = rec.record(numframes=RATE * CHUNK)
                    if self.is_paused:
                        continue
                    if x.ndim > 1 and x.shape[1] > 1:
                        mono = np.mean(x[:, :2], axis=1).astype(np.float32)
                    elif x.ndim > 1:
                        mono = x[:, 0].astype(np.float32)
                    else:
                        mono = x.astype(np.float32)
                    try:
                        audio_queue.put(mono, timeout=0.5)
                    except queue.Full:
                        pass
        except Exception as e:
            self.is_running = False
            err_msg = str(e) or type(e).__name__
            if on_error_cb:
                on_error_cb(err_msg)
        finally:
            uninit_com_thread(com_inited)
