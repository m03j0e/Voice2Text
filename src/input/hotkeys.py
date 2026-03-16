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
        self.last_trigger_time = 0
        
        # Modifier masks
        self.OPTION_MASK = 0x00080000 # kCGEventFlagMaskAlternate
        self.RIGHT_OPTION_KEY = 61

    def start(self):
        if self.running:
            return
        
        logger.info("Starting Reliable Toggle Hotkey Listener (Quartz Polling)...")
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def _poll_loop(self):
        """Poll the hardware key state to toggle on Press."""
        while self.running:
            try:
                # Check for Option flag or specific Right Option hardware key
                current_flags = Quartz.CGEventSourceFlagsState(1) # HID System State
                is_option_down = bool(current_flags & self.OPTION_MASK)
                is_key_61_down = Quartz.CGEventSourceKeyState(1, self.RIGHT_OPTION_KEY)
                
                is_down = is_option_down or is_key_61_down
                
                # We trigger a toggle on the "Press" edge (False -> True)
                if is_down and not self.last_state:
                    current_time = time.time()
                    # 300ms debounce to prevent double-toggles from a single physical press
                    if current_time - self.last_trigger_time > 0.3:
                        logger.info("Hotkey Toggle Triggered!")
                        if self.callback:
                            self.callback()
                        self.last_trigger_time = current_time
                
                self.last_state = is_down
                
            except Exception as e:
                logger.error(f"Error in hotkey loop: {e}")
            
            time.sleep(0.05) # 20Hz is plenty for toggle detection
