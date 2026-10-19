import queue
import threading
from datetime import datetime

MODEL_SIZE = "small.en"
DEVICE = "cpu"
COMPUTE = "int8"


class TranscriptionWorker:
    """
    Decoupled background worker for faster-whisper transcription.
    Uses lazy importing so the UI starts instantly without waiting on ML libraries.
    """

    def __init__(self):
        self.model = None
        self.is_ready = False
        self.is_loading = False
        self.lines = []
        self._stop_event = threading.Event()
        self._transcribe_thread = None

    def load_model_async(self, on_ready_cb=None, on_error_cb=None):
        """Load Whisper model in background thread with lazy import."""
        if self.is_ready or self.is_loading:
            return
        self.is_loading = True

        def _loader():
            try:
                # Lazy import faster_whisper here to ensure zero startup delay for UI
                from faster_whisper import WhisperModel
                self.model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE)
                self.is_ready = True
                self.is_loading = False
                if on_ready_cb:
                    on_ready_cb()
            except Exception as e:
                self.is_loading = False
                if on_error_cb:
                    on_error_cb(str(e) or type(e).__name__)

        threading.Thread(target=_loader, daemon=True).start()

    def start(self, audio_queue, on_segment_cb=None, on_error_cb=None):
        """Start transcription loop reading from audio_queue."""
        self._stop_event.clear()
        self._transcribe_thread = threading.Thread(
            target=self._transcribe_loop,
            args=(audio_queue, on_segment_cb, on_error_cb),
            daemon=True
        )
        self._transcribe_thread.start()

    def stop(self):
        """Signal transcription worker to stop."""
        self._stop_event.set()
        self._transcribe_thread = None

    def clear(self):
        """Clear accumulated transcript lines."""
        self.lines.clear()

    def _transcribe_loop(self, audio_queue, on_segment_cb, on_error_cb):
        while not self._stop_event.is_set() or not audio_queue.empty():
            try:
                x = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if self.model is None:
                    continue

                segs, _ = self.model.transcribe(
                    x,
                    beam_size=1,
                    vad_filter=True,
                    language="en",
                    condition_on_previous_text=False,
                    temperature=0
                )
                text = " ".join(s.text.strip() for s in segs).strip()
                if text:
                    stamp = datetime.now().strftime("%H:%M:%S")
                    self.lines.append((stamp, text))
                    if on_segment_cb:
                        on_segment_cb(stamp, text)
            except Exception as e:
                if on_error_cb:
                    on_error_cb(str(e))
