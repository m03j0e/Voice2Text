import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import queue
from src.utils.logger import logger
from src.input.hotkeys import HotkeyListener
from src.utils.text_processing import remove_filler_words


class AppWindow:
    def __init__(self, root, outputs=None):
        self.root = root
        self.root.title("Voice to Text")
        self.root.geometry("600x340")

        try:
            from src.audio.capture import get_audio_devices
            self.available_devices = get_audio_devices()
        except Exception:
            self.available_devices = {}

        self.selected_device_name = tk.StringVar()
        self.is_recording = False
        self.queue = queue.Queue()
        self.outputs = outputs or []
        self.inject_var = tk.BooleanVar(value=True)

        self.audio_capture = None
        self.recognizer = None

        self.hotkeys = HotkeyListener(callback=lambda: self.root.after(0, self.toggle_recording))
        self.current_text = ""
        self.setup_ui()

        self.root.after(800, self._initialize_recognizer)
        self.root.after(1500, self._safe_start_hotkeys)
        self.root.after(100, self.process_queue)

    def _safe_start_hotkeys(self):
        try:
            import HIServices
            if not HIServices.AXIsProcessTrusted():
                self.status_label.config(
                    text="Status: Grant Accessibility permission, then restart",
                    foreground="#e74c3c"
                )
                self._prompt_accessibility_permission()
        except Exception:
            pass
        try:
            self.hotkeys.start()
        except Exception as e:
            logger.error(f"Failed to start hotkeys: {e}")
            self.status_label.config(
                text="Status: Hotkeys Disabled (Check Accessibility in System Settings)",
                foreground="#e74c3c"
            )

    def _prompt_accessibility_permission(self):
        import subprocess
        try:
            real_path = os.path.realpath(sys.executable)
        except Exception:
            real_path = sys.executable

        msg = (
            "Voice2Text needs Accessibility permission for global hotkeys.\n\n"
            "Add this exact file to Accessibility:\n\n"
            f"{real_path}\n\n"
            "Steps:\n"
            "1. Click OK — System Settings > Accessibility will open\n"
            "2. Click the '+' button\n"
            "3. Press \u2318\u21e7G (Cmd+Shift+G) in the file picker\n"
            f"4. Paste the path above and press Enter, then click Open\n"
            "5. Make sure the toggle next to it is ON\n"
            "6. Quit and restart Voice2Text"
        )
        messagebox.showinfo("Accessibility Permission Required", msg)
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        ], check=False)

    def _initialize_recognizer(self):
        logger.info("Initializing Speech Recognizer...")
        from src.speech.recognizer import Recognizer
        try:
            self.recognizer = Recognizer(result_callback=self.on_recognition_result)
            logger.info("Speech Recognizer initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Speech Recognizer: {e}")

    def setup_ui(self):
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        bg_color = "#f4f6f8"
        fg_color = "#333333"
        accent_color = "#27ae60"
        accent_hover = "#2ecc71"
        select_bg = "#d5f5e3"
        select_fg = "#1e8449"

        self.root.configure(bg=bg_color)
        style.configure(".", background=bg_color, foreground=fg_color,
                        fieldbackground="#ffffff", troughcolor=bg_color,
                        selectbackground=select_bg, selectforeground=select_fg,
                        font=("Helvetica", 12))
        style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor="#cccccc")
        style.configure("TLabelframe.Label", background=bg_color, foreground=accent_color, font=("Helvetica", 12, "bold"))
        style.configure("TButton", background=accent_color, foreground="#ffffff", font=("Helvetica", 12, "bold"), borderwidth=0)
        style.map("TButton", background=[("active", accent_hover)], foreground=[("active", "#ffffff")])
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
        style.map("TCheckbutton", background=[("active", bg_color)])
        style.configure("TCombobox", fieldbackground="#ffffff", background="#ffffff", foreground=fg_color,
                        selectbackground=select_bg, selectforeground=select_fg)
        style.configure("TLabel", background=bg_color, foreground=fg_color)

        # Microphone selection
        frame_device = ttk.LabelFrame(self.root, text="Microphone Selection", padding=10)
        frame_device.pack(fill="x", padx=10, pady=5)

        self.device_combo = ttk.Combobox(frame_device, textvariable=self.selected_device_name, state="readonly")
        if self.available_devices:
            self.device_combo['values'] = list(self.available_devices.keys())
            try:
                import sounddevice as sd
                default_index = sd.default.device[0]
                default_name = next((n for n, i in self.available_devices.items() if i == default_index), None)
                if default_name:
                    self.device_combo.set(default_name)
                else:
                    self.device_combo.current(0)
            except Exception:
                self.device_combo.current(0)
        else:
            self.device_combo['values'] = ["No Input Devices Found"]
            self.device_combo.current(0)
        self.device_combo.pack(fill="x", pady=5)

        # Output options
        frame_options = ttk.LabelFrame(self.root, text="Output Options", padding=10)
        frame_options.pack(fill="x", padx=10, pady=5)
        ttk.Checkbutton(frame_options, text="Inject Text into Active App", variable=self.inject_var).pack(side="left", padx=5)

        # Controls
        ctrl_frame = ttk.Frame(self.root)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        self.btn_toggle = ttk.Button(ctrl_frame, text="Start Recording", command=self.toggle_recording)
        self.btn_toggle.pack(side="left", padx=5)
        self.status_label = ttk.Label(ctrl_frame, text="Status: Ready (Press Right Option)", foreground="#27ae60")
        self.status_label.pack(side="left", padx=5)

        # Transcription area
        frame_text = ttk.LabelFrame(self.root, text="Transcription", padding=10)
        frame_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.text_area = tk.Text(frame_text, height=8, wrap="word", bg="#ffffff", fg="#333333",
                                 insertbackground="#27ae60", selectbackground="#d5f5e3",
                                 selectforeground="#1e8449", font=("Helvetica", 12))
        self.text_area.pack(fill="both", expand=True)

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.is_recording:
            return

        if not self.recognizer:
            self.queue.put(("status", "Status: Initializing, please wait...", "#e74c3c"))
            return

        logger.info("Starting recording session...")
        self.is_recording = True
        self.current_text = ""

        for output in self.outputs:
            output.reset()

        self.btn_toggle.config(text="Stop Recording")
        self.queue.put(("status", "Status: Recording...", "#e74c3c"))

        if sys.platform == 'darwin':
            os.system("afplay /System/Library/Sounds/Ping.aiff &")

        try:
            device_name = self.selected_device_name.get()
            device_id = self.available_devices.get(device_name)
            self.recognizer.start()
            from src.audio.capture import AudioCapture
            self.audio_capture = AudioCapture(device_id=device_id, callback=self.on_audio_data)
            self.audio_capture.start()
        except Exception as e:
            logger.error(f"Error starting recognition: {e}", exc_info=True)
            self.is_recording = False
            self.btn_toggle.config(text="Start Recording")
            self.queue.put(("status", f"Error: {e}", "#e74c3c"))

    def stop_recording(self):
        if not self.is_recording:
            return

        logger.debug("Stopping recording...")
        final_text = self.current_text
        self.is_recording = False

        if self.audio_capture:
            self.audio_capture.stop()
            self.audio_capture = None

        self.recognizer.stop()
        self.btn_toggle.config(text="Start Recording")

        if sys.platform == 'darwin':
            os.system("afplay /System/Library/Sounds/Pop.aiff &")

        self.queue.put(("final_stop", final_text))
        self.queue.put(("status", "Status: Ready (Press Right Option to Record)", "#27ae60"))

    def on_audio_data(self, numpy_data, status):
        if status:
            logger.debug(f"SoundDevice Status Code: {status}")
        if self.is_recording:
            self.recognizer.process_audio(numpy_data)

    def on_recognition_result(self, transcription, is_final):
        if not self.is_recording:
            logger.debug(f"Discarding post-stop transcription: {transcription}")
            return
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
                    if not self.is_recording:
                        continue
                    new_text, is_final = msg[1], msg[2]
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.insert(tk.END, new_text)
                    if self.inject_var.get():
                        for output in self.outputs:
                            output.output(new_text, is_final)
                elif msg_type == "final_stop":
                    final_text = msg[1]
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.insert(tk.END, final_text)
                    if self.inject_var.get():
                        for output in self.outputs:
                            output.output(final_text, True)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
