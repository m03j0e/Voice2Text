import time
import threading
from src.utils.logger import logger

# Right Option key hardware keycode
_RIGHT_OPTION_KEYCODE = 61

# Poll interval in seconds.  10 ms gives ≤10 ms trigger latency at negligible CPU cost.
_POLL_INTERVAL = 0.01


class HotkeyListener:
    """
    Detects the Right Option key by polling CGEventSourceKeyState every 10 ms.

    CGEventSourceKeyState reads raw HID hardware state — it does NOT require
    Accessibility or Input Monitoring TCC permissions, and works regardless of
    which application currently has focus.  This avoids the macOS 26 behavior
    where CGEventTap / NSEvent global monitors are silently restricted for
    ad-hoc-signed processes.
    """

    def __init__(self, callback):
        self.callback = callback
        self.last_trigger_time = 0.0
        self._should_run = False

    def start(self):
        self._should_run = True
        threading.Thread(target=self._poll, daemon=True).start()

    def stop(self):
        self._should_run = False

    def _poll(self):
        try:
            from Quartz import (
                CGEventSourceKeyState,
                kCGEventSourceStateHIDSystemState,
            )
        except ImportError as e:
            logger.error(f"Quartz not available — hotkey polling disabled: {e}")
            return

        logger.info("Hotkey listener active (polling CGEventSourceKeyState).")
        was_pressed = False

        while self._should_run:
            is_pressed = bool(CGEventSourceKeyState(kCGEventSourceStateHIDSystemState, _RIGHT_OPTION_KEYCODE))

            if is_pressed and not was_pressed:
                # Rising edge — Right Option just went down
                now = time.time()
                if now - self.last_trigger_time > 0.3:
                    self.last_trigger_time = now
                    logger.info("Hotkey Toggle Triggered (Right Option)!")
                    if self.callback:
                        self.callback()

            was_pressed = is_pressed
            time.sleep(_POLL_INTERVAL)

        logger.info("Hotkey polling stopped.")
