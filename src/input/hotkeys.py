import threading
import time
import Quartz
from src.utils.logger import logger

class HotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.thread = None
        self.last_state = False
        
        # Modifier masks
        # kCGEventFlagMaskAlternate (Option) = 0x00080000
        self.OPTION_MASK = 0x00080000
        # Specifically Right Option usually has this bit in the NX_DEVICERIGHTALTBIT
        # but CGEventSourceFlagsState often just gives the general Alternate mask.
        
        # We also keep the key code polling as a backup
        # 61 is Right Option, 58 is Left Option
        self.RIGHT_OPTION_KEY = 61

    def start(self):
        if self.running:
            return
        
        logger.info("Starting Global Hotkey Listener (Quartz Flags Polling)...")
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info("Hotkey Listener started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def _poll_loop(self):
        """Poll the hardware modifier state directly from Quartz."""
        while self.running:
            try:
                # Method 1: Check Global Flags (Works best for global modifiers)
                # kCGEventSourceStateHIDSystemState = 1
                current_flags = Quartz.CGEventSourceFlagsState(1)
                
                # Check if Option (Alternate) is pressed
                is_option_pressed = bool(current_flags & self.OPTION_MASK)
                
                # Method 2: Check specifically for Right Option key code 61
                is_key_61_down = Quartz.CGEventSourceKeyState(1, self.RIGHT_OPTION_KEY)
                
                # We trigger if EITHER the right-option key is down OR the alternate flag is active
                # (You can tune this to be specific to Right Option if needed)
                is_down = is_option_pressed or is_key_61_down
                
                if is_down and not self.last_state:
                    logger.info(f"Global Option Key Detected! (Flags: {hex(current_flags)}, Key61: {is_key_61_down})")
                    if self.callback:
                        self.callback()
                
                self.last_state = is_down
                
            except Exception as e:
                logger.error(f"Error in hotkey poll loop: {e}")
            
            time.sleep(0.05)
