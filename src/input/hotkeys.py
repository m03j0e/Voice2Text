from pynput import keyboard

class HotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.listener = None

    from src.utils.logger import logger

    def start(self):
        logger.info("Starting HotkeyListener...")
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()
        logger.info("HotkeyListener started.")

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    def on_key_press(self, key):
        if key == keyboard.Key.alt_r:  # Right Option
            if self.callback:
                self.callback()
