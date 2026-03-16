with open("src/input/hotkeys.py", "r") as f:
    content = f.read()

new_content = """import time
import threading
from pynput import keyboard
from src.utils.logger import logger

class HotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.listener = None
        self.last_trigger_time = 0

    def start(self):
        if self.listener is not None:
            return

        logger.info("Starting Reliable Toggle Hotkey Listener (pynput) in background thread...")
        # To completely avoid BPT trap 5 on macOS with Tkinter,
        # we can't even initialize the Listener in the main thread.
        # However, sometimes starting it in a Python Thread isn't enough if Cocoa is involved.
        # Pynput has a known issue where it must be on the MAIN thread to tap events securely,
        # BUT Tkinter must also be on the main thread.
        # The best workaround for pynput + Tkinter is often using GlobalHotKeys or just a raw listener,
        # but importing it very late or letting pynput handle its own loop.

        # Another approach: start the listener in the main thread BUT not in an 'after' callback.
        # Unfortunately we are in an after callback.
        # Let's try GlobalHotKeys, or simply catching the error if it's purely a startup crash.

        # Let's try the threading approach again but ensure we don't hold any Tkinter locks
        threading.Thread(target=self._run_listener, daemon=True).start()

    def _run_listener(self):
        try:
            # We must import keyboard inside the thread if it uses ObjC/Cocoa
            from pynput import keyboard

            # Using GlobalHotKeys if possible, but regular listener is fine.
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.start()
            self.listener.join()
        except Exception as e:
            logger.error(f"Error starting pynput listener: {e}")

    def stop(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

    def on_press(self, key):
        try:
            if key == keyboard.Key.alt_r:
                current_time = time.time()
                # 300ms debounce to prevent double-toggles from a single physical press
                if current_time - self.last_trigger_time > 0.3:
                    logger.info("Hotkey Toggle Triggered (Right Option)!")
                    if self.callback:
                        self.callback()
                    self.last_trigger_time = current_time
        except Exception as e:
            logger.error(f"Error in hotkey loop: {e}")
"""

with open("src/input/hotkeys.py", "w") as f:
    f.write(new_content)
print("Patched src/input/hotkeys.py v2")
