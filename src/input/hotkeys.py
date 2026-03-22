import time
import threading
from src.utils.logger import logger

# Right Option key hardware keycode (Quartz / CGEvent)
_RIGHT_OPTION_KEYCODE = 61

# macOS sends these synthetic event types to a CGEventTap callback when the tap
# is auto-disabled.  Use raw uint32 values as a fallback in case PyObjC doesn't
# export the named constants.
try:
    from Quartz import kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput
except ImportError:
    kCGEventTapDisabledByTimeout   = 0xFFFFFFFE
    kCGEventTapDisabledByUserInput = 0xFFFFFFFF

_TAP_DISABLED_EVENTS = {kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput}


class HotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.tap = None
        self._loop = None
        self.last_trigger_time = 0.0
        self._should_run = False

    def start(self):
        self._should_run = True
        logger.info("Starting CGEventTap hotkey listener...")
        threading.Thread(target=self._run_tap, daemon=True).start()

    def stop(self):
        self._should_run = False
        loop = self._loop
        if loop is not None:
            try:
                from Quartz import CFRunLoopStop
                CFRunLoopStop(loop)
            except Exception as e:
                logger.error(f"Error stopping hotkey listener: {e}")

    def _trigger(self, source=""):
        now = time.time()
        if now - self.last_trigger_time > 0.3:
            self.last_trigger_time = now
            label = f" [{source}]" if source else ""
            logger.info(f"Hotkey Toggle Triggered (Right Option){label}!")
            if self.callback:
                self.callback()

    def _run_tap(self):
        try:
            from Quartz import (
                CGEventTapCreate,
                CGEventTapEnable,
                CFMachPortCreateRunLoopSource,
                CFRunLoopAddSource,
                CFRunLoopGetCurrent,
                CFRunLoopRunInMode,
                CGEventSourceCreate,
                CGEventSourceKeyState,
                kCGEventSourceStateHIDSystemState,
                kCGHIDEventTap,
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionDefault,
                kCGEventTapOptionListenOnly,
                kCGEventFlagsChanged,
                CGEventGetIntegerValueField,
                CGEventGetFlags,
                kCGKeyboardEventKeycode,
                kCGEventFlagMaskAlternate,
                kCFRunLoopDefaultMode,
                kCFRunLoopRunTimedOut,
                kCFRunLoopRunStopped,
            )
        except ImportError as e:
            logger.error(f"Quartz not available: {e}")
            return

        def _callback(_proxy, event_type, event, _refcon):
            try:
                if event_type in _TAP_DISABLED_EVENTS:
                    reason = "timeout" if event_type == kCGEventTapDisabledByTimeout else "user-input"
                    logger.debug(f"CGEventTap disabled ({reason}) — re-enabling...")
                    if self.tap is not None:
                        CGEventTapEnable(self.tap, True)

                    # macOS 26 disables the listen-only tap on each key event from
                    # another process, consuming that event before our callback sees it.
                    # When disabled by user-input, check the hardware state immediately —
                    # if Right Option is still physically held, fire the hotkey now.
                    if event_type == kCGEventTapDisabledByUserInput:
                        try:
                            src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
                            if src and CGEventSourceKeyState(src, _RIGHT_OPTION_KEYCODE):
                                self._trigger("recovered")
                        except Exception:
                            pass
                    return event

                if event_type == kCGEventFlagsChanged:
                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    if keycode == _RIGHT_OPTION_KEYCODE:
                        flags = CGEventGetFlags(event)
                        if flags & kCGEventFlagMaskAlternate:
                            self._trigger()
            except Exception as e:
                logger.error(f"CGEventTap callback error: {e}")
            return event

        self._callback_fn = _callback
        mask = 1 << kCGEventFlagsChanged

        # Try taps from most-global to least.
        # kCGSessionEventTap + listen-only is intentionally skipped: macOS lets
        # creation succeed without Input Monitoring but silently restricts delivery
        # to the focused process (the "in-focus-only" bug).
        tap = None
        desc = None

        tap = CGEventTapCreate(kCGHIDEventTap, kCGHeadInsertEventTap,
                               kCGEventTapOptionDefault, mask, _callback, None)
        if tap is not None:
            desc = "HID active (Accessibility granted)"

        if tap is None:
            tap = CGEventTapCreate(kCGSessionEventTap, kCGHeadInsertEventTap,
                                   kCGEventTapOptionDefault, mask, _callback, None)
            if tap is not None:
                desc = "session active (Accessibility granted)"

        if tap is None:
            tap = CGEventTapCreate(kCGHIDEventTap, kCGHeadInsertEventTap,
                                   kCGEventTapOptionListenOnly, mask, _callback, None)
            if tap is not None:
                desc = "HID listen-only (Input Monitoring granted)"

        if tap is None:
            logger.warning(
                "CGEventTap creation failed — global hotkeys disabled.\n"
                "Grant Input Monitoring or Accessibility in System Settings > Privacy & Security."
            )
            return

        logger.info(f"CGEventTap active: {desc}.")
        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        self._loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._loop, source, kCFRunLoopDefaultMode)
        self.tap = tap
        CGEventTapEnable(tap, True)

        try:
            while True:
                result = CFRunLoopRunInMode(kCFRunLoopDefaultMode, 1.0, False)
                if result == kCFRunLoopRunStopped:
                    break
                if result != kCFRunLoopRunTimedOut:
                    logger.warning(f"CFRunLoop exited (result={result}), restarting listener.")
                    break
        except Exception as e:
            logger.error(f"CFRunLoop error: {e}")
        finally:
            self._loop = None
            self.tap = None
            self._callback_fn = None

        if self._should_run:
            logger.warning("Hotkey listener exited unexpectedly — restarting in 3 s...")
            time.sleep(3)
            if self._should_run:
                threading.Thread(target=self._run_tap, daemon=True).start()
