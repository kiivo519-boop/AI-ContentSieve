"""AI ContentSieve desktop UI; only the main thread touches Tk widgets."""

from datetime import datetime
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    raise SystemExit("Missing CustomTkinter. Run: python -m pip install -r requirements.txt")

from core.downloader import validate_url
from core.pipeline import JobResult, run_pipeline
from core.transcriber import WhisperTranscriber


APP_DIR = Path(__file__).resolve().parent


class ContentSieveApp(ctk.CTk):
    """Single-job controller with queue-based worker-to-UI communication."""

    def __init__(self) -> None:
        super().__init__()
        self.title("AI ContentSieve")
        self.geometry("1000x820")
        self.minsize(760, 650)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.events: queue.Queue = queue.Queue()
        self.busy = False
        self.last_folder: Path | None = None
        self.last_message = ""
        self.progress_value = 0.0
        self.transcriber = WhisperTranscriber()
        self.url = ctk.StringVar()
        self.output = ctk.StringVar(value=str(APP_DIR / "outputs"))
        self.model = ctk.StringVar(value="base")
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._poll)

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 12))
        ctk.CTkLabel(header, text="AI ContentSieve", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text="Turn short-form video into a reusable content script.",
                     text_color="#A6B0C3").pack(anchor="w")
        panel = ctk.CTkFrame(self, corner_radius=14)
        panel.grid(row=1, column=0, sticky="ew", padx=26)
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(panel, text="VIDEO URL · YouTube / Instagram / TikTok").grid(
            row=0, column=0, sticky="w", padx=18, pady=(14, 4))
        self.url_entry = ctk.CTkEntry(panel, textvariable=self.url, height=42,
                                     placeholder_text="Paste a public short-video URL")
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18)
        ctk.CTkLabel(panel, text="SAVE RESULTS TO").grid(row=2, column=0, sticky="w", padx=18, pady=(12, 4))
        self.path_entry = ctk.CTkEntry(panel, textvariable=self.output, height=36)
        self.path_entry.grid(row=3, column=0, sticky="ew", padx=(18, 8))
        self.browse_button = ctk.CTkButton(panel, text="Browse…", width=110, command=self._browse)
        self.browse_button.grid(row=3, column=1, padx=(0, 18))
        controls = ctk.CTkFrame(panel, fg_color="transparent")
        controls.grid(row=4, column=0, columnspan=2, sticky="ew", padx=18, pady=16)
        ctk.CTkLabel(controls, text="Whisper model:").pack(side="left", padx=(0, 8))
        self.model_menu = ctk.CTkOptionMenu(controls, variable=self.model, values=["tiny", "base"], width=100)
        self.model_menu.pack(side="left")
        self.start_button = ctk.CTkButton(controls, text="Download & Analyze", height=40,
                                         font=ctk.CTkFont(weight="bold"), command=self._start)
        self.start_button.pack(side="right")
        progress_panel = ctk.CTkFrame(self, fg_color="transparent")
        progress_panel.grid(row=2, column=0, sticky="ew", padx=26, pady=14)
        self.status = ctk.CTkLabel(progress_panel, text="Ready · local transcription · no API key", anchor="w")
        self.status.pack(fill="x")
        self.progress = ctk.CTkProgressBar(progress_panel)
        self.progress.pack(fill="x", pady=(5, 0))
        self.progress.set(0)
        tabs = ctk.CTkTabview(self)
        tabs.grid(row=3, column=0, sticky="nsew", padx=26)
        self.boxes = {}
        for name in ("Activity", "Transcript", "Analysis"):
            tab = tabs.add(name)
            box = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=13))
            box.pack(fill="both", expand=True)
            box.configure(state="disabled")
            self.boxes[name] = box
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=26, pady=16)
        ctk.CTkLabel(footer, text="Speech-based analysis • Review AI transcripts before publishing",
                     text_color="#A6B0C3").pack(side="left")
        self.open_button = ctk.CTkButton(footer, text="Open results", width=110,
                                        state="disabled", command=self._open_results)
        self.open_button.pack(side="right")
        self._log("Choose an output folder and paste a public video URL. First use downloads model weights.")

    def _browse(self) -> None:
        selected = filedialog.askdirectory(parent=self, title="Choose output folder", mustexist=True)
        if selected:
            self.output.set(selected)

    def _log(self, message: str) -> None:
        box = self.boxes["Activity"]
        box.configure(state="normal")
        box.insert("end", f"[{datetime.now():%H:%M:%S}] {message}\n")
        box.see("end")
        box.configure(state="disabled")

    def _text(self, name: str, value: str) -> None:
        box = self.boxes[name]
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", value)
        box.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        for widget in (self.url_entry, self.path_entry, self.browse_button,
                       self.model_menu, self.start_button):
            widget.configure(state="disabled" if busy else "normal")
        self.open_button.configure(state="normal" if self.last_folder and not busy else "disabled")

    def _start(self) -> None:
        if self.busy:
            return
        try:
            url = validate_url(self.url.get())
            if not self.output.get().strip():
                raise ValueError("Choose an output folder.")
            output = Path(self.output.get().strip()).expanduser().resolve()
        except (ValueError, OSError) as exc:
            messagebox.showerror("Check your input", str(exc), parent=self)
            return
        self.last_folder = None
        self.last_message = ""
        self.progress_value = 0
        self.progress.set(0)
        self._text("Transcript", "")
        self._text("Analysis", "")
        self._set_busy(True)
        self.status.configure(text="Starting…")
        self._log("Starting a new job. Progress indicates stages, not remaining time.")
        # Snapshot every Tk variable on the main thread before starting work.
        threading.Thread(target=self._worker, args=(url, output, self.model.get()),
                         daemon=False, name="contentsieve-worker").start()

    def _worker(self, url: str, output: Path, model: str) -> None:
        last_update = 0.0
        last_message = ""

        def report(value: float, message: str) -> None:
            nonlocal last_update, last_message
            now = time.monotonic()
            if message != last_message or now - last_update >= 0.15 or value >= 1:
                self.events.put(("progress", (value, message)))
                last_update, last_message = now, message

        try:
            result = run_pipeline(url, output, model, self.transcriber, report)
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def _poll(self) -> None:
        # Limit per tick so a stream of progress events cannot starve Tk.
        for _ in range(100):
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "progress":
                value, message = payload
                self.progress_value = max(self.progress_value, value)
                self.progress.set(self.progress_value)
                self.status.configure(text=message[:115])
                if message != self.last_message:
                    self._log(message)
                    self.last_message = message
            elif event == "done":
                result: JobResult = payload
                self.last_folder = result.folder
                self._text("Transcript", result.transcript)
                self._text("Analysis", result.analysis)
                self._log(f"Saved to {result.folder}")
                self.status.configure(text="Complete · MP4, transcript, subtitles, analysis, and metadata saved")
                self.progress.set(1)
                self._set_busy(False)
            elif event == "error":
                self._log(payload)
                self.status.configure(text="Job failed · see Activity for details")
                self._set_busy(False)
                messagebox.showerror("Processing failed", payload, parent=self)
        self.after(100, self._poll)

    def _open_results(self) -> None:
        if not self.last_folder:
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(self.last_folder))
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open",
                                  str(self.last_folder)])
        except OSError as exc:
            messagebox.showerror("Cannot open folder", str(exc), parent=self)

    def _close(self) -> None:
        if self.busy:
            messagebox.showinfo("Processing in progress", "Please wait for this job to finish before closing. "
                                "This protects result files and temporary-file cleanup.", parent=self)
            return
        self.destroy()


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    ContentSieveApp().mainloop()


if __name__ == "__main__":
    main()