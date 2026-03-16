import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import queue
import threading
import sounddevice as sd
import numpy as np
from src.utils.logger import logger
from src.audio.capture import get_audio_devices, AudioCapture
from src.input.hotkeys import HotkeyListener
from src.utils.text_processing import remove_filler_words

from src.utils.prompts import PromptManager

class AppWindow:
    def __init__(self, root, outputs=None):
        self.root = root
        self.root.title("Voice to Text")
        self.root.geometry("600x450")

        self.available_devices = get_audio_devices()
        self.selected_device_name = tk.StringVar()
        self.is_recording = False
        self.queue = queue.Queue()
        self.outputs = outputs or []
        self.inject_var = tk.BooleanVar(value=False)
        self.obsidian_var = tk.BooleanVar(value=False)

        # AI Feature Vars
        self.ai_var = tk.BooleanVar(value=False)
        self.prompt_var = tk.StringVar()

        # Defer AI client initialization to avoid trace trap via macOS Security framework during TK startup
        self.ai_client = None
        self.prompt_manager = None
        self.floating_indicator = None
        
        # Schedule it once the Tkinter mainloop has safely started
        self.root.after(500, self._initialize_ai)

        self.audio_capture = None
        self.recognizer = None
        
        # Schedule everything else with slightly more delay to avoid race conditions with macOS security/UI frameworks
        self.hotkeys = HotkeyListener(callback=self.toggle_recording)
        self.current_text = ""
        self.setup_ui()

        self.root.after(800, self._initialize_recognizer)
        self.root.after(1500, self.hotkeys.start)

        # Start checking the queue for GUI updates
        self.root.after(100, self.process_queue)

    def _initialize_recognizer(self):
        logger.info("Initializing Speech Recognizer...")
        from src.speech.recognizer import Recognizer
        try:
            self.recognizer = Recognizer(result_callback=self.on_recognition_result)
            logger.info("Speech Recognizer initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Speech Recognizer: {e}")

    def _initialize_ai(self):
        logger.info("Initializing AI components...")
        from src.ai.gemini import GeminiClient
        from src.utils.prompts import PromptManager
        from src.ui.floating_indicator import FloatingIndicator
        
        logger.debug("Creating GeminiClient...")
        self.ai_client = GeminiClient(defer_init=True)
        logger.debug("Creating PromptManager...")
        self.prompt_manager = PromptManager()
        logger.debug("Creating FloatingIndicator...")
        try:
            self.floating_indicator = FloatingIndicator(self.root)
            logger.debug("FloatingIndicator created.")
        except Exception as e:
            logger.error(f"Failed to create FloatingIndicator: {e}")
        
        # Update combo box now that prompt manager is loaded
        if hasattr(self, 'prompt_combo'):
            self.prompt_combo['values'] = self.prompt_manager.prompts
            self.prompt_combo.set(self.prompt_manager.default_prompt)
        logger.info("AI components initialized.")

    def setup_ui(self):
        # Configure Hacker Outrun style
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        bg_color = "#0a0a0c"
        fg_color = "#00ff41"
        accent_color = "#ff0055"
        select_bg = "#00ffff"

        self.root.configure(bg=bg_color)

        style.configure(".",
                        background=bg_color,
                        foreground=fg_color,
                        fieldbackground=bg_color,
                        troughcolor=bg_color,
                        selectbackground=select_bg,
                        selectforeground=bg_color,
                        font=("Courier", 12))

        style.configure("TLabelframe", background=bg_color, foreground=accent_color, bordercolor=fg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=accent_color, font=("Courier", 12, "bold"))
        style.configure("TButton", background=bg_color, foreground=accent_color)
        style.map("TButton", background=[("active", accent_color)], foreground=[("active", bg_color)])
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
        style.map("TCheckbutton", background=[("active", bg_color)])
        style.configure("TCombobox", fieldbackground=bg_color, background=bg_color, foreground=fg_color, selectbackground=select_bg, selectforeground=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)

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
        frame_options = ttk.LabelFrame(self.root, text="Output Options", padding=10)
        frame_options.pack(fill="x", padx=10, pady=5)

        chk_inject = ttk.Checkbutton(frame_options, text="Inject Text into Active App", variable=self.inject_var)
        chk_inject.pack(side="left", padx=5)

        chk_obsidian = ttk.Checkbutton(frame_options, text="Export to Obsidian", variable=self.obsidian_var)
        chk_obsidian.pack(side="left", padx=5)

        # AI Polishing
        frame_ai = ttk.LabelFrame(self.root, text="AI Polishing (Google Gemini)", padding=10)
        frame_ai.pack(fill="x", padx=10, pady=5)

        ai_top_frame = ttk.Frame(frame_ai)
        ai_top_frame.pack(fill="x")

        chk_ai = ttk.Checkbutton(ai_top_frame, text="Enable AI Polish", variable=self.ai_var, command=self.on_ai_toggle)
        chk_ai.pack(side="left", padx=5)

        btn_apikey = ttk.Button(ai_top_frame, text="Set API Key", command=self.prompt_api_key)
        btn_apikey.pack(side="right", padx=5)

        ai_bot_frame = ttk.Frame(frame_ai)
        ai_bot_frame.pack(fill="x", pady=5)
        lbl_prompt = ttk.Label(ai_bot_frame, text="Prompt:")
        lbl_prompt.pack(side="left", padx=5)

        self.prompt_combo = ttk.Combobox(ai_bot_frame, textvariable=self.prompt_var)
        self.prompt_combo.pack(side="left", fill="x", expand=True, padx=5)

        # Status
        self.status_label = ttk.Label(self.root, text="Status: Ready (Press Right Option to Record)", foreground="#00ff41")
        self.status_label.pack(pady=5)

        # Output Area
        frame_text = ttk.LabelFrame(self.root, text="Transcription", padding=10)
        frame_text.pack(fill="both", expand=True, padx=10, pady=5)

        self.text_area = tk.Text(frame_text, height=8, wrap="word", bg="#0a0a0c", fg="#00ff41", insertbackground="#ff0055", selectbackground="#00ffff", selectforeground="#0a0a0c", font=("Courier", 12))
        self.text_area.pack(fill="both", expand=True)

    def prompt_api_key(self):
        key = simpledialog.askstring("API Key", "Enter Google Gemini API Key:", show='*')
        if key:
            success = self.ai_client.set_api_key(key)
            if success:
                messagebox.showinfo("Success", "API Key saved securely.")
            else:
                messagebox.showerror("Error", "Failed to save API Key.")

    def on_ai_toggle(self):
        if self.ai_var.get():
            if not self.ai_client.has_key:
                success = self.ai_client.initialize()
                if not success:
                    messagebox.showwarning("API Key Required", "Please set your Gemini API Key first.")
                    self.ai_var.set(False)

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
        self.queue.put(("status", "Status: Recording... (Press Right Option to Stop)", "#ff0055"))

        self.is_recording = True
        self.current_text = ""

        for output in self.outputs:
            output.reset()

        self.floating_indicator.show()

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
            self.queue.put(("status", f"Error: {e}", "#ff0055"))
            self.floating_indicator.hide()

    def stop_recording(self):
        if not self.is_recording:
            return

        logger.debug("Stopping recording...")

        if self.audio_capture:
            self.audio_capture.stop()
            self.audio_capture = None

        self.recognizer.stop()
        self.is_recording = False

        self.floating_indicator.hide()

        if self.ai_var.get():
            self.queue.put(("status", "Status: Polishing with AI...", "#00ffff"))

            # Save prompt if custom
            current_prompt = self.prompt_var.get()
            self.prompt_manager.save(current_prompt)
            # Update combobox values
            self.prompt_combo['values'] = self.prompt_manager.prompts

            # Dispatch to background thread for API call
            threading.Thread(target=self.polish_and_dispatch, args=(self.current_text, current_prompt)).start()
        else:
            # Standard real-time flow
            self.queue.put(("final", self.current_text))
            self.queue.put(("status", "Status: Ready (Press Right Option to Record)", "#00ff41"))

    def polish_and_dispatch(self, raw_text, prompt):
        try:
            if not raw_text.strip():
                self.queue.put(("final_ai", raw_text))
                return

            polished_text = self.ai_client.polish_text(raw_text, prompt)
            self.queue.put(("final_ai", polished_text))
        except Exception as e:
            logger.error(f"Failed AI polish thread: {e}")
            self.queue.put(("final_ai", raw_text))
        finally:
            self.queue.put(("status", "Status: Ready (Press Right Option to Record)", "#00ff41"))

    def on_audio_data(self, numpy_data, status):
        if status:
            logger.debug(f"SoundDevice Status Code: {status}")

        if not self.is_recording:
            return

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

                    # Only inject if AI is OFF
                    if not self.ai_var.get():
                        self.dispatch_outputs(new_text, is_final)
                elif msg_type == "final":
                    final_text = msg[1]
                    if not self.ai_var.get():
                        self.dispatch_outputs(final_text, True)
                elif msg_type == "final_ai":
                    polished_text = msg[1]
                    # Update text area with polished text
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.insert(tk.END, polished_text)
                    # For AI, we dump the whole text at once as final
                    self.dispatch_outputs(polished_text, True)

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
