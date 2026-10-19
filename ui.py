import os
import sys
import queue
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

import config_manager
import audio_engine
from transcription_engine import TranscriptionWorker

# Tailwind-inspired dark theme configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("MeetScript - Live Transcription")
        self.root.geometry("980x720")
        self.root.minsize(820, 600)
        self.root.configure(fg_color="#0f172a")  # Tailwind Slate-900

        # Set window icon from favicon.ico
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "favicon.ico")
        if not os.path.exists(icon_path) and hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "favicon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Core decoupled workers and communication queue
        self.audio_queue = queue.Queue(maxsize=10)
        self.audio_worker = audio_engine.AudioCaptureWorker()
        self.transcribe_worker = TranscriptionWorker()
        self.running = False

        # Build UI layout immediately for zero-delay launch
        self._build_ui()

        # Load persisted settings from config_manager
        self.load_saved_settings()

        # Enumerate audio devices (fast, non-blocking to user)
        self.load_devices()

        # Start asynchronous Whisper model loading in background
        self.transcribe_worker.load_model_async(
            on_ready_cb=self._on_model_ready,
            on_error_cb=self._on_model_error
        )

    def _build_ui(self):
        # Top Header Card (Tailwind Slate-800 with Slate-700 border)
        header_card = ctk.CTkFrame(
            self.root,
            corner_radius=12,
            fg_color="#1e293b",
            border_width=1,
            border_color="#334155"
        )
        header_card.pack(fill="x", padx=16, pady=(14, 8))

        # Title & Status Badge inside header
        title_row = ctk.CTkFrame(header_card, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(12, 10))

        title_label = ctk.CTkLabel(
            title_row,
            text="MeetScript - Live Transcription",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#f8fafc"  # Tailwind Slate-50
        )
        title_label.pack(side="left")

        self.status_badge = ctk.CTkLabel(
            title_row,
            text="● Loading model...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#334155",
            text_color="#94a3b8",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.status_badge.pack(side="right")

        # Controls Grid inside header card
        controls = ctk.CTkFrame(header_card, fg_color="transparent")
        controls.pack(fill="x", padx=16, pady=(0, 14))
        controls.columnconfigure(1, weight=1)

        # Row 0: Playback Device & Action Buttons
        dev_lbl = ctk.CTkLabel(
            controls,
            text="Playback Device:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#94a3b8"  # Tailwind Slate-400
        )
        dev_lbl.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)

        dev_frame = ctk.CTkFrame(controls, fg_color="transparent")
        dev_frame.grid(row=0, column=1, sticky="ew", pady=4)

        self.combo = ctk.CTkComboBox(
            dev_frame,
            values=["Detecting audio devices..."],
            width=280,
            state="readonly",
            corner_radius=8,
            border_color="#334155",
            fg_color="#0f172a",
            button_color="#334155",
            dropdown_fg_color="#1e293b"
        )
        self.combo.pack(side="left", fill="x", expand=True)

        self.refresh_btn = ctk.CTkButton(
            dev_frame,
            text="🔄 Refresh",
            command=lambda: self.load_devices(show_status=True),
            width=88,
            fg_color="#334155",       # Tailwind Slate-700
            hover_color="#475569",    # Tailwind Slate-600
            font=ctk.CTkFont(weight="bold"),
            corner_radius=8
        )
        self.refresh_btn.pack(side="left", padx=(8, 0))

        btn_row = ctk.CTkFrame(controls, fg_color="transparent")
        btn_row.grid(row=0, column=2, sticky="e", padx=(12, 0), pady=4)

        self.start = ctk.CTkButton(
            btn_row,
            text="▶ Start",
            command=self.start_capture,
            width=78,
            fg_color="#10b981",       # Tailwind Emerald-500
            hover_color="#059669",    # Tailwind Emerald-600
            font=ctk.CTkFont(weight="bold"),
            corner_radius=8,
            state="disabled"
        )
        self.start.pack(side="left", padx=3)

        self.pause_btn = ctk.CTkButton(
            btn_row,
            text="⏸ Pause",
            command=self.toggle_pause,
            width=78,
            fg_color="#f59e0b",       # Tailwind Amber-500
            hover_color="#d97706",    # Tailwind Amber-600
            font=ctk.CTkFont(weight="bold"),
            corner_radius=8,
            state="disabled"
        )
        self.pause_btn.pack(side="left", padx=3)

        self.stop = ctk.CTkButton(
            btn_row,
            text="⏹ Stop",
            command=self.stop_capture,
            width=78,
            fg_color="#ef4444",       # Tailwind Red-500
            hover_color="#dc2626",    # Tailwind Red-600
            font=ctk.CTkFont(weight="bold"),
            corner_radius=8,
            state="disabled"
        )
        self.stop.pack(side="left", padx=3)

        self.save_btn = ctk.CTkButton(
            btn_row,
            text="💾 Save",
            command=self.save,
            width=74,
            fg_color="#3b82f6",       # Tailwind Blue-500
            hover_color="#2563eb",    # Tailwind Blue-600
            font=ctk.CTkFont(weight="bold"),
            corner_radius=8
        )
        self.save_btn.pack(side="left", padx=3)

        self.clear_btn = ctk.CTkButton(
            btn_row,
            text="🗑 Clear",
            command=self.clear,
            width=74,
            fg_color="#475569",       # Tailwind Slate-600
            hover_color="#334155",    # Tailwind Slate-700
            font=ctk.CTkFont(weight="bold"),
            corner_radius=8
        )
        self.clear_btn.pack(side="left", padx=3)

        # Row 1: Save Folder & Browse Button
        folder_lbl = ctk.CTkLabel(
            controls,
            text="Save Folder:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#94a3b8"
        )
        folder_lbl.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)

        self.folder_combo = ctk.CTkComboBox(
            controls,
            values=[],
            width=380,
            command=self.on_folder_selected,
            corner_radius=8,
            border_color="#334155",
            fg_color="#0f172a",
            dropdown_fg_color="#1e293b"
        )
        self.folder_combo.grid(row=1, column=1, sticky="ew", pady=4)
        if hasattr(self.folder_combo, "_entry"):
            self.folder_combo._entry.bind("<FocusOut>", lambda e: self.on_folder_change())
            self.folder_combo._entry.bind("<Return>", lambda e: self.on_folder_change())

        self.browse_btn = ctk.CTkButton(
            controls,
            text="📁 Browse...",
            command=self.browse_folder,
            width=100,
            fg_color="#6366f1",       # Tailwind Indigo-500
            hover_color="#4f46e5",    # Tailwind Indigo-600
            font=ctk.CTkFont(weight="bold"),
            corner_radius=8
        )
        self.browse_btn.grid(row=1, column=2, sticky="w", padx=(12, 0), pady=4)

        # Row 2: Meeting Name & Format Hint
        meet_lbl = ctk.CTkLabel(
            controls,
            text="Meeting Name:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#94a3b8"
        )
        meet_lbl.grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)

        self.meet_name_entry = ctk.CTkEntry(
            controls,
            placeholder_text="Enter meeting name (e.g. Daily Standup)...",
            width=380,
            corner_radius=8,
            border_color="#334155",
            fg_color="#0f172a"
        )
        self.meet_name_entry.grid(row=2, column=1, sticky="ew", pady=4)
        self.meet_name_entry.bind("<FocusOut>", lambda e: self.persist_meeting_name())
        self.meet_name_entry.bind("<Return>", lambda e: self.persist_meeting_name())
        self.meet_name_entry.bind("<KeyRelease>", lambda e: self.persist_meeting_name())

        hint_lbl = ctk.CTkLabel(
            controls,
            text="(Saved as: <Meeting Name> MM-DD-YYYY.txt)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748b"  # Tailwind Slate-500
        )
        hint_lbl.grid(row=2, column=2, sticky="w", padx=(12, 0), pady=4)

        # Transcript Area Card
        text_card = ctk.CTkFrame(
            self.root,
            corner_radius=12,
            fg_color="#1e293b",
            border_width=1,
            border_color="#334155"
        )
        text_card.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        text_header = ctk.CTkLabel(
            text_card,
            text="📝 Live Transcript",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#cbd5e1"  # Tailwind Slate-300
        )
        text_header.pack(anchor="w", padx=16, pady=(12, 6))

        self.text = ctk.CTkTextbox(
            text_card,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#0f172a",
            text_color="#f1f5f9",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.text.tag_config("time", foreground="#38bdf8")  # Tailwind Sky-400

        # Footer Bar
        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            footer,
            text="Initializing Whisper model...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8"
        )
        self.status_label.pack(side="left")

        footer_hint = ctk.CTkLabel(
            footer,
            text="Captures Windows loopback audio • Speaker labels not inferred",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#475569"
        )
        footer_hint.pack(side="right")

    @property
    def is_paused(self):
        return self.audio_worker.is_paused

    @property
    def lines(self):
        return self.transcribe_worker.lines

    def set_badge(self, text, bg="#334155", fg="#94a3b8"):
        self.status_badge.configure(text=text, fg_color=bg, text_color=fg)

    def set_status(self, text):
        self.status_label.configure(text=text)

    def load_devices(self, show_status=False):
        try:
            current_choice = self.combo.get().strip() if hasattr(self, "combo") else ""
            names = audio_engine.get_audio_devices()
            if names:
                self.combo.configure(values=names)
                default_name = audio_engine.get_default_device_name()
                if current_choice in names:
                    self.combo.set(current_choice)
                elif default_name and default_name in names:
                    self.combo.set(default_name)
                else:
                    self.combo.set(names[0])
                if show_status:
                    self.set_status(f"Audio devices refreshed ({len(names)} detected).")
            else:
                self.combo.configure(values=["No playback device found"])
                self.combo.set("No playback device found")
                if show_status:
                    self.set_status("No playback devices detected.")
        except Exception as e:
            messagebox.showerror("Audio devices", str(e), parent=self.root)

    def load_saved_settings(self):
        paths, selected = config_manager.get_saved_folders()
        if paths:
            self.folder_combo.configure(values=paths)
        if selected:
            self.folder_combo.set(selected)
        elif paths:
            self.folder_combo.set(paths[0])

        saved_meet_name = config_manager.get_saved_meeting_name()
        if saved_meet_name:
            self.meet_name_entry.delete(0, "end")
            self.meet_name_entry.insert(0, saved_meet_name)

    def persist_meeting_name(self):
        meet_name = self.meet_name_entry.get().strip()
        config_manager.save_meeting_name(meet_name)

    def persist_folder(self, path):
        config_manager.save_folder_selection(path)
        paths, selected = config_manager.get_saved_folders()
        if paths:
            self.folder_combo.configure(values=paths)
        if selected:
            self.folder_combo.set(selected)

    def on_folder_selected(self, choice):
        if choice and choice.strip():
            self.persist_folder(choice.strip())

    def on_folder_change(self):
        path = self.folder_combo.get().strip()
        self.persist_folder(path)

    def browse_folder(self):
        try:
            initial = self.folder_combo.get().strip()
            if not initial or not os.path.isdir(initial):
                initial = os.path.expanduser("~")

            self.root.update()
            self.root.lift()
            self.root.focus_force()

            chosen = filedialog.askdirectory(
                parent=self.root,
                title="Select Folder to Save Transcripts",
                initialdir=initial
            )
            self.root.update()
        except Exception as e:
            messagebox.showerror("Folder Selection Error", f"Unable to open folder picker: {e}", parent=self.root)
            return

        if chosen:
            chosen = os.path.normpath(chosen)
            self.folder_combo.set(chosen)
            self.persist_folder(chosen)

    def _on_model_ready(self):
        self.root.after(0, lambda: self.set_badge("● Ready", bg="#064e3b", fg="#34d399"))
        self.root.after(0, lambda: self.set_status("Whisper model loaded. Ready to transcribe."))
        self.root.after(0, lambda: self.start.configure(state="normal"))

    def _on_model_error(self, err):
        self.root.after(0, lambda: self.set_badge("● Model Error", bg="#7f1d1d", fg="#f87171"))
        self.root.after(0, lambda: self.set_status(f"Model error: {err}"))
        self.root.after(0, lambda: messagebox.showerror("Whisper model", str(err), parent=self.root))

    def _on_segment(self, stamp, text):
        self.root.after(0, self.add_line, stamp, text)

    def _on_capture_error(self, err_msg):
        self.root.after(0, lambda: self.set_status(f"Capture error: {err_msg}"))
        self.root.after(0, lambda: self.stop_capture_on_error(err_msg))

    def _on_transcribe_error(self, err_msg):
        self.root.after(0, lambda: self.set_status(f"Transcription error: {err_msg}"))

    def add_line(self, stamp, text):
        self.text.insert("end", f"[{stamp}] ", "time")
        self.text.insert("end", f"{text}\n\n")
        self.text.see("end")
        self.set_status("Listening and transcribing...")

    def toggle_pause(self):
        if not self.running:
            return
        if not self.audio_worker.is_paused:
            self.audio_worker.pause()
            self.pause_btn.configure(
                text="▶ Resume",
                fg_color="#10b981",       # Tailwind Emerald-500
                hover_color="#059669"
            )
            self.set_badge("● Paused", bg="#78350f", fg="#fcd34d")
            self.set_status("Recording paused. Audio is not being transcribed.")
        else:
            self.audio_worker.resume()
            self.pause_btn.configure(
                text="⏸ Pause",
                fg_color="#f59e0b",       # Tailwind Amber-500
                hover_color="#d97706"
            )
            self.set_badge("● Recording", bg="#881337", fg="#fb7185")
            self.set_status("Listening to system audio...")

    def start_capture(self):
        if self.running:
            return
        if not self.transcribe_worker.is_ready:
            messagebox.showwarning("Model Loading", "Whisper model is still loading. Please wait a moment.", parent=self.root)
            return
        device_name = self.combo.get().strip()
        if not device_name or device_name in ["Detecting audio devices...", "No playback device found"]:
            messagebox.showwarning("Device", "Please select a playback device.", parent=self.root)
            return

        self.running = True
        self.start.configure(state="disabled")
        self.pause_btn.configure(
            state="normal",
            text="⏸ Pause",
            fg_color="#f59e0b",
            hover_color="#d97706"
        )
        self.stop.configure(state="normal")
        self.set_badge("● Recording", bg="#881337", fg="#fb7185")
        self.set_status("Listening to system audio...")

        self.audio_worker.start(
            device_name,
            self.audio_queue,
            on_error_cb=self._on_capture_error
        )
        self.transcribe_worker.start(
            self.audio_queue,
            on_segment_cb=self._on_segment,
            on_error_cb=self._on_transcribe_error
        )

    def stop_capture_on_error(self, err_msg=None):
        self.running = False
        self.audio_worker.stop()
        self.transcribe_worker.stop()
        self.start.configure(state="normal")
        self.pause_btn.configure(
            state="disabled",
            text="⏸ Pause",
            fg_color="#f59e0b",
            hover_color="#d97706"
        )
        self.stop.configure(state="disabled")
        self.set_badge("● Error", bg="#7f1d1d", fg="#f87171")
        if err_msg:
            messagebox.showerror(
                "Audio Capture Error",
                f"Failed to capture audio from the playback device:\n\n{err_msg}\n\n"
                "Please make sure your headphones or speaker is plugged in and playing sound, then try clicking '🔄 Refresh' and 'Start' again.",
                parent=self.root
            )

    def stop_capture(self):
        if not self.running:
            return

        self.running = False
        self.audio_worker.stop()
        self.transcribe_worker.stop()

        self.start.configure(state="normal")
        self.pause_btn.configure(
            state="disabled",
            text="⏸ Pause",
            fg_color="#f59e0b",
            hover_color="#d97706"
        )
        self.stop.configure(state="disabled")
        self.set_badge("● Stopped", bg="#1e293b", fg="#94a3b8")

        folder = self.folder_combo.get().strip()
        if not folder:
            self.set_status("Stopped (transcript not saved - no folder specified).")
            return

        lines = self.transcribe_worker.lines
        if not lines:
            self.set_status("Stopped (no speech detected / nothing to save).")
            return

        self.set_status("Saving transcript...")

        try:
            meet_name = self.meet_name_entry.get().strip()
            filepath = config_manager.build_unique_filepath(folder, meet_name)
            config_manager.write_transcript_to_file(filepath, lines)

            self.persist_folder(folder)
            self.persist_meeting_name()
            self.set_status(f"Stopped. Transcript saved: {filepath}")

            messagebox.showinfo(
                "Transcript Saved",
                f"Transcript automatically saved to:\n\n{filepath}",
                parent=self.root
            )
        except Exception as e:
            self.set_status(f"Save error: {e}")
            messagebox.showerror("Save Error", str(e), parent=self.root)

    def clear(self):
        self.transcribe_worker.clear()
        self.text.delete("1.0", "end")
        self.set_status("Transcript cleared.")

    def save(self):
        lines = self.transcribe_worker.lines
        if not lines:
            return
        initial_folder = self.folder_combo.get().strip()
        meet_name = self.meet_name_entry.get().strip()
        clean_name = config_manager.sanitize_filename_part(meet_name)
        date_str = datetime.now().strftime("%m-%d-%Y")
        default_file = f"{clean_name} {date_str}.txt"

        try:
            self.root.update()
            self.root.lift()
            self.root.focus_force()
            p = filedialog.asksaveasfilename(
                parent=self.root,
                title="Save Transcript",
                initialdir=initial_folder if (initial_folder and os.path.isdir(initial_folder)) else os.path.expanduser("~"),
                initialfile=default_file,
                defaultextension=".txt",
                filetypes=[("Text", "*.txt"), ("Markdown", "*.md")]
            )
            self.root.update()
        except Exception as e:
            messagebox.showerror("Save Error", str(e), parent=self.root)
            return

        if p:
            config_manager.write_transcript_to_file(p, lines)
            self.persist_meeting_name()
            messagebox.showinfo("Saved", p, parent=self.root)
