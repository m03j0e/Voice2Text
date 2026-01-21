import sys
import threading
import re
import queue
import time
import tkinter as tk
from tkinter import ttk

import sounddevice as sd
import numpy as np

import Cocoa
import AVFoundation
from AVFoundation import (
    AVAudioFormat,
    AVAudioPCMBuffer,
)
import Speech
from Speech import (
    SFSpeechRecognizer,
    SFSpeechAudioBufferRecognitionRequest,
    SFSpeechRecognitionTask,
)
from pynput import keyboard

if __name__ == "__main__":
    # Setup logging to file
    class Tee(object):
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        def flush(self):
            for f in self.files:
                f.flush()

    f_log = open('debug.log', 'w', buffering=1)
    sys.stdout = Tee(sys.stdout, f_log)
    sys.stderr = Tee(sys.stderr, f_log)

    print("--- Starting Application (SoundDevice) ---")

class VoiceToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice to Text")
        self.root.geometry("500x300")

        self.available_devices = self.get_audio_devices()
        self.selected_device_name = tk.StringVar()
        self.is_recording = False
        self.recognition_task = None
        self.request = None
        self.recognizer = SFSpeechRecognizer.new()
        self.queue = queue.Queue()
        self.stream = None
        self.keyboard_controller = keyboard.Controller()
        self.last_typed_text = ""
        self.inject_var = tk.BooleanVar(value=False)

        self.setup_ui()
        self.setup_hotkey()
        
        # Start checking the queue for GUI updates
        self.root.after(100, self.process_queue)

    def get_audio_devices(self):
        devices = sd.query_devices()
        device_map = {}
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                name = device['name']
                # Create a unique name if duplicates exist
                if name in device_map:
                    name = f"{name} ({i})"
                device_map[name] = i
        return device_map

    def setup_ui(self):
        # Device Selection
        frame_device = ttk.LabelFrame(self.root, text="Microphone Selection", padding=10)
        frame_device.pack(fill="x", padx=10, pady=5)

        self.device_combo = ttk.Combobox(frame_device, textvariable=self.selected_device_name, state="readonly")
        if self.available_devices:
            values = list(self.available_devices.keys())
            self.device_combo['values'] = values
            
            # Default to default input
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

        # Status
        self.status_label = ttk.Label(self.root, text="Status: Ready (Press Right Option to Record)", foreground="gray")
        self.status_label.pack(pady=10)

        # Output Area
        frame_text = ttk.LabelFrame(self.root, text="Transcription", padding=10)
        frame_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Controls in header of text frame? Or just above it.
        chk_inject = ttk.Checkbutton(frame_text, text="Inject Text into Active App", variable=self.inject_var)
        chk_inject.pack(anchor="w", pady=(0, 5))
        
        self.text_area = tk.Text(frame_text, height=10, wrap="word")
        self.text_area.pack(fill="both", expand=True)

    def setup_hotkey(self):
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

    def on_key_press(self, key):
        if key == keyboard.Key.alt_r:  # Right Option
            print("Debug: Right Option pressed")
            self.toggle_recording()

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.is_recording:
            return
        
        print("Debug: Starting recording...")    
        self.queue.put(("status", "Status: Recording... (Press Right Option to Stop)", "red"))
        
        self.is_recording = True
        try:
            self.start_recognition()
        except Exception as e:
            print(f"Error starting recognition: {e}")
            import traceback
            traceback.print_exc()
            self.is_recording = False
            self.queue.put(("status", f"Error: {e}", "red"))

    def stop_recording(self):
        if not self.is_recording:
            return
            
        print("Debug: Stopping recording...")
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        if self.request:
            self.request.endAudio()
        
        if self.recognition_task:
            self.recognition_task.cancel()
            self.recognition_task = None
            
        self.is_recording = False
        self.last_typed_text = "" # Reset state
        self.queue.put(("status", "Status: Ready (Press Right Option to Record)", "gray"))

    def start_recognition(self):
        print("Debug: Initializing SFSpeechRecognizer...")
        
        device_name = self.selected_device_name.get()
        device_id = self.available_devices.get(device_name)
        print(f"Debug: Selected SoundDevice ID: {device_id} ({device_name})")

        self.request = SFSpeechAudioBufferRecognitionRequest.new()
        
        # Audio Format for SFSpeechRecognizer
        self.samplerate = 16000
        
        # Define the audio format (Native PyObjC Object)
        self.audio_format = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(
            self.samplerate, 1
        )

        
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            device=device_id,
            channels=1,
            callback=self.audio_callback,
            dtype='int16'
        )
        self.stream.start()
        print("Debug: Audio stream started")
        
        # 4. Start Task
        self.recognition_task = self.recognizer.recognitionTaskWithRequest_resultHandler_(
            self.request, 
            self.recognition_result_handler
        )
        print("Debug: Recognition task started")

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Debug: SoundDevice Status Code: {status}")
        
        if not self.is_recording:
            return

        # Check amplitude
        amplitude = np.max(np.abs(indata))
        if not hasattr(self, '_silence_counter'):
            self._silence_counter = 0

        if amplitude == 0:
            self._silence_counter += 1
            if self._silence_counter % 50 == 0:
                print(f"Debug: Audio is silent (Max Amp: 0.0) - Frame {self._silence_counter}")
        else:
            self._silence_counter = 0
            if not hasattr(self, '_signal_log_counter'):
                self._signal_log_counter = 0
            self._signal_log_counter += 1
            if self._signal_log_counter % 50 == 0:
                 print(f"Debug: Audio Signal Detected! Max Amp: {amplitude}")
        
        # Convert int16 to float32
        data_float = indata.astype(np.float32) / 32768.0
        
        self.push_buffer(data_float)

    def push_buffer(self, numpy_data):
        # numpy_data is (frames, 1) float32
        frame_count = len(numpy_data)
        
        buffer = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(self.audio_format, frame_count)
        buffer.setFrameLength_(frame_count)
        
        # Helper: manual loop copy
        channels = buffer.floatChannelData()
        ptr = channels[0] # float* (varlist)
        
        flat_data = numpy_data.flatten()
        
        # Loop copy
        for i in range(frame_count):
            ptr[i] = flat_data[i]
            
        self.request.appendAudioPCMBuffer_(buffer)


    def recognition_result_handler(self, result, error):
        if error:
            if error.domain() == "kAFAssistantErrorDomain" and error.code() == 1110:
                 pass
            else:
                 print(f"Debug: Recognition error: {error}")
            
        if result:
            transcription = result.bestTranscription().formattedString()
            print(f"Debug: Transcription received: {transcription}")
            cleaned_text = self.remove_filler_words(transcription)
            # Pass raw and cleaned to queue? or just cleaned
            self.queue.put(("text", cleaned_text))

    def remove_filler_words(self, text):
        fillers = [r'\bum\b', r'\buh\b', r'\blike\b', r'\bso\b', r'\byou know\b']
        cleaned = text
        for filler in fillers:
            cleaned = re.sub(filler, '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def process_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                msg_type = msg[0]
                if msg_type == "status":
                    self.status_label.config(text=msg[1], foreground=msg[2])
                elif msg_type == "text":
                    new_text = msg[1]
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.insert(tk.END, new_text)
                    
                    if self.inject_var.get():
                        self.handle_typing(new_text)
                        
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
            
    def handle_typing(self, new_text):
        # Diff and Type
        current_len = len(self.last_typed_text)
        # Find common prefix
        common_len = 0
        min_len = min(current_len, len(new_text))
        
        # Simple optimization: if new_text is just an extension of last_typed_text
        if new_text.startswith(self.last_typed_text):
             to_type = new_text[current_len:]
             if to_type:
                 self.keyboard_controller.type(to_type)
             self.last_typed_text = new_text
             return

        # If we are here, there is a mismatch (correction) or completely new text
        # Find exactly where they diverge
        for i in range(min_len):
            if self.last_typed_text[i] != new_text[i]:
                break
            common_len += 1
            
        # If perfect match up to min_len, then common_len should be min_len
        # (covered by startswith usually, but strictly speaking:)
        if self.last_typed_text[:min_len] == new_text[:min_len]:
            common_len = min_len

        # Backspace execution
        backspaces_needed = current_len - common_len
        if backspaces_needed > 0:
             # Tap backspace N times
             for _ in range(backspaces_needed):
                 self.keyboard_controller.tap(keyboard.Key.backspace)
                 
        # Type new characters
        to_type = new_text[common_len:]
        if to_type:
            self.keyboard_controller.type(to_type)
            
        self.last_typed_text = new_text

if __name__ == "__main__":
    def auth_callback(status):
        pass
    SFSpeechRecognizer.requestAuthorization_(auth_callback)
    
    root = tk.Tk()
    app = VoiceToTextApp(root)
    root.mainloop()
