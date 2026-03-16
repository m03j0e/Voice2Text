import time
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
        
        logger.info("Starting Reliable Toggle Hotkey Listener (pynput)...")
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

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
