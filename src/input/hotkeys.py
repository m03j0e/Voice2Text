import time
import threading
from src.utils.logger import logger

class HotkeyListener:
    """
    Detects the Right Option key using pynput.
    """

    def __init__(self, callback):
        self.callback = callback
        self.last_trigger_time = 0.0
        self.listener = None

    def start(self):
        # We start the pynput listener in a background thread
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

    def _run(self):
        try:
            from pynput import keyboard
        except ImportError as e:
            logger.error(f"pynput not available — hotkey polling disabled: {e}")
            return

        logger.info("Hotkey listener active (using pynput).")

        def on_press(key):
            # Check for Right Option (alt_r)
            if key == keyboard.Key.alt_r:
                now = time.time()
                # Simple debounce
                if now - self.last_trigger_time > 0.3:
                    self.last_trigger_time = now
                    logger.info("Hotkey Toggle Triggered (Right Option)!")
                    if self.callback:
                        self.callback()

        try:
            with keyboard.Listener(on_press=on_press) as listener:
                self.listener = listener
                listener.join()
        except Exception as e:
            logger.error(f"Error in hotkey listener: {e}")

        logger.info("Hotkey polling stopped.")
