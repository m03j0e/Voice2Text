import tkinter as tk
from tkinter import ttk
import queue
import sounddevice as sd
import numpy as np
from src.utils.logger import logger
from src.audio.capture import get_audio_devices, AudioCapture
from src.speech.recognizer import Recognizer
from src.input.hotkeys import HotkeyListener
from src.utils.text_processing import remove_filler_words

class AppWindow:
    def __init__(self, root, outputs=None):
        self.root = root
        self.root.title("Voice to Text")
        self.root.geometry("500x300")

        self.available_devices = get_audio_devices()
        self.selected_device_name = tk.StringVar()
        self.is_recording = False
        self.queue = queue.Queue()
        self.outputs = outputs or []
        self.inject_var = tk.BooleanVar(value=False)
        self.obsidian_var = tk.BooleanVar(value=False)

        self.audio_capture = None
        self.recognizer = Recognizer(result_callback=self.on_recognition_result)
        self.hotkeys = HotkeyListener(callback=self.toggle_recording)
        self.current_text = ""

        self.setup_ui()
        self.hotkeys.start()

        # Start checking the queue for GUI updates
        self.root.after(100, self.process_queue)

    def setup_ui(self):
        # Device Selection
        frame_device = ttk.LabelFrame(self.root, text="Microphone Selection", padding=10)
        frame_device.pack(fill="x", padx=10, pady=5)

        self.device_combo = ttk.Combobox(frame_device, textvariable=self.selected_device_name, state="readonly")
        if self.available_devices:
            values = list(self.available_devices.keys())
            self.device_combo['values'] = values

            default_index = sd.default.device[0]
            default_name = None
            for name, idx in self.available_devices.items():
                if idx == default_index:
                    default_name = name
                    break

            if default_name:
                self.device_combo.set(default_name)
            else:
                self.device_combo.current(0)
        else:
            self.device_combo['values'] = ["No Input Devices Found"]
            self.device_combo.current(0)
        self.device_combo.pack(fill="x", pady=5)

        # Output options
        frame_options = ttk.Frame(self.root)
        frame_options.pack(fill="x", padx=10, pady=5)

        chk_inject = ttk.Checkbutton(frame_options, text="Inject Text into Active App", variable=self.inject_var)
        chk_inject.pack(side="left", padx=5)

        chk_obsidian = ttk.Checkbutton(frame_options, text="Export to Obsidian", variable=self.obsidian_var)
        chk_obsidian.pack(side="left", padx=5)

        # Status
        self.status_label = ttk.Label(self.root, text="Status: Ready (Press Right Option to Record)", foreground="gray")
        self.status_label.pack(pady=5)

        # Output Area
        frame_text = ttk.LabelFrame(self.root, text="Transcription", padding=10)
        frame_text.pack(fill="both", expand=True, padx=10, pady=5)

        self.text_area = tk.Text(frame_text, height=10, wrap="word")
        self.text_area.pack(fill="both", expand=True)

    def toggle_recording(self):
        logger.debug("Right Option pressed")
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.is_recording:
            return

        logger.debug("Starting recording...")
        self.queue.put(("status", "Status: Recording... (Press Right Option to Stop)", "red"))

        self.is_recording = True
        self.current_text = ""

        for output in self.outputs:
            output.reset()

        try:
            device_name = self.selected_device_name.get()
            device_id = self.available_devices.get(device_name)

            self.recognizer.start()
            self.audio_capture = AudioCapture(
                device_id=device_id,
                callback=self.on_audio_data
            )
            self.audio_capture.start()

        except Exception as e:
            logger.error(f"Error starting recognition: {e}", exc_info=True)
            self.is_recording = False
            self.queue.put(("status", f"Error: {e}", "red"))

    def stop_recording(self):
        if not self.is_recording:
            return

        logger.debug("Stopping recording...")

        if self.audio_capture:
            self.audio_capture.stop()
            self.audio_capture = None

        self.recognizer.stop()
        self.is_recording = False

        # Dispatch final event
        self.queue.put(("final",))
        self.queue.put(("status", "Status: Ready (Press Right Option to Record)", "gray"))

    def on_audio_data(self, numpy_data, status):
        if status:
            logger.debug(f"SoundDevice Status Code: {status}")

        if not self.is_recording:
            return

        # Check amplitude
        amplitude = np.max(np.abs(numpy_data))
        if not hasattr(self, '_silence_counter'):
            self._silence_counter = 0

        if amplitude == 0:
            self._silence_counter += 1
            if self._silence_counter % 50 == 0:
                logger.debug(f"Audio is silent (Max Amp: 0.0) - Frame {self._silence_counter}")
        else:
            self._silence_counter = 0
            if not hasattr(self, '_signal_log_counter'):
                self._signal_log_counter = 0
            self._signal_log_counter += 1
            if self._signal_log_counter % 50 == 0:
                 logger.debug(f"Audio Signal Detected! Max Amp: {amplitude}")

        self.recognizer.process_audio(numpy_data)

    def on_recognition_result(self, transcription, is_final):
        logger.debug(f"Transcription received: {transcription}")
        cleaned_text = remove_filler_words(transcription)
        self.current_text = cleaned_text
        self.queue.put(("text", cleaned_text, is_final))

    def process_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                msg_type = msg[0]
                if msg_type == "status":
                    self.status_label.config(text=msg[1], foreground=msg[2])
                elif msg_type == "text":
                    new_text = msg[1]
                    is_final = msg[2]
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.insert(tk.END, new_text)

                    self.dispatch_outputs(new_text, is_final)
                elif msg_type == "final":
                    self.dispatch_outputs(self.current_text, True)

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def dispatch_outputs(self, text, is_final):
        from src.output.keyboard import KeyboardInjector
        from src.output.obsidian import ObsidianExporter

        for output in self.outputs:
            if isinstance(output, KeyboardInjector) and self.inject_var.get():
                output.output(text, is_final)
            elif isinstance(output, ObsidianExporter) and self.obsidian_var.get():
                output.output(text, is_final)
