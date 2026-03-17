import time
import threading
from src.utils.logger import logger

# Right Option key hardware keycode (Quartz CGEvent keycode 61 = 0x3D)
_RIGHT_OPTION_KEYCODE = 61

class HotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.tap = None
        self._loop = None
        self.last_trigger_time = 0.0

    def start(self):
        # Check Accessibility permission — kCGEventTapOptionDefault requires it.
        try:
            import HIServices
            if not HIServices.AXIsProcessTrusted():
                logger.warning(
                    "Accessibility permission not granted. "
                    "Grant it in System Settings > Privacy & Security > Accessibility, "
                    "then restart the app."
                )
        except Exception as e:
            logger.warning(f"Could not check Accessibility permission: {e}")

        logger.info("Starting Quartz CGEventTap hotkey listener...")
        threading.Thread(target=self._run_tap, daemon=True).start()

    def _run_tap(self):
        try:
            from Quartz import (
                CGEventTapCreate,
                CGEventTapEnable,
                CFMachPortCreateRunLoopSource,
                CFRunLoopAddSource,
                CFRunLoopGetCurrent,
                CFRunLoopRunInMode,
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionDefault,
                kCGEventFlagsChanged,
                CGEventGetIntegerValueField,
                CGEventGetFlags,
                kCGKeyboardEventKeycode,
                kCGEventFlagMaskAlternate,
                kCFRunLoopDefaultMode,
                kCFRunLoopRunTimedOut,
            )
        except ImportError as e:
            logger.error(f"Quartz not available for hotkey listener: {e}")
            return

        def _callback(_proxy, event_type, event, _refcon):
            try:
                if event_type == kCGEventFlagsChanged:
                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    if keycode == _RIGHT_OPTION_KEYCODE:
                        flags = CGEventGetFlags(event)
                        # Trigger on key-press (flag newly set), not release
                        if flags & kCGEventFlagMaskAlternate:
                            now = time.time()
                            if now - self.last_trigger_time > 0.3:
                                self.last_trigger_time = now
                                logger.info("Hotkey Toggle Triggered (Right Option)!")
                                if self.callback:
                                    self.callback()
            except Exception as e:
                logger.error(f"Error in CGEventTap callback: {e}")
            # Must return event unmodified to not block other applications
            return event

        # Store reference to prevent GC while tap is alive
        self._callback_fn = _callback

        mask = 1 << kCGEventFlagsChanged  # CGEventMaskBit(kCGEventFlagsChanged)
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,   # Active tap — requires Accessibility, works globally
            mask,
            _callback,
            None,
        )

        if tap is None:
            logger.warning(
                "CGEventTap (active) creation failed — trying passive tap (Input Monitoring)..."
            )
            from Quartz import kCGEventTapOptionListenOnly
            tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionListenOnly,
                mask,
                _callback,
                None,
            )

        if tap is None:
            logger.warning(
                "CGEventTap creation failed. Global hotkeys will not work. "
                "Grant Accessibility permission in "
                "System Settings > Privacy & Security > Accessibility, then restart."
            )
            return

        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        self._loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._loop, source, kCFRunLoopDefaultMode)
        CGEventTapEnable(tap, True)
        self.tap = tap
        logger.info("CGEventTap listener running (global).")

        try:
            while True:
                result = CFRunLoopRunInMode(kCFRunLoopDefaultMode, 1.0, False)
                if result != kCFRunLoopRunTimedOut:
                    break
        except Exception as e:
            logger.error(f"CFRunLoop error in hotkey listener: {e}")
        finally:
            self._loop = None
            self.tap = None
            self._callback_fn = None

    def stop(self):
        loop = self._loop
        if loop is not None:
            try:
                from Quartz import CFRunLoopStop
                CFRunLoopStop(loop)
            except Exception as e:
                logger.error(f"Error stopping hotkey listener: {e}")
