import time
import threading
from src.utils.logger import logger

# Right Option key hardware keycode (Quartz CGEvent keycode 61 = 0x3D)
_RIGHT_OPTION_KEYCODE = 61

# macOS sends these synthetic event types to the callback when a CGEventTap is
# auto-disabled.  They are defined in CGEventTypes.h but are not always exported
# by name in PyObjC, so we use the raw uint32 values as a fallback.
try:
    from Quartz import kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput
except ImportError:
    kCGEventTapDisabledByTimeout    = 0xFFFFFFFE
    kCGEventTapDisabledByUserInput  = 0xFFFFFFFF

_TAP_DISABLED_EVENTS = {kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput}


class HotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.tap = None
        self._loop = None
        self.last_trigger_time = 0.0
        self._should_run = False

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

        self._should_run = True
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
                kCFRunLoopRunStopped,
            )
        except ImportError as e:
            logger.error(f"Quartz not available for hotkey listener: {e}")
            return

        def _callback(_proxy, event_type, event, _refcon):
            try:
                # macOS disables the tap on sleep/wake, timeout, or permission changes.
                # Re-enable immediately so hotkeys survive these events.
                if event_type in _TAP_DISABLED_EVENTS:
                    reason = "timeout" if event_type == kCGEventTapDisabledByTimeout else "user-input"
                    logger.warning(f"CGEventTap was auto-disabled ({reason}) — re-enabling...")
                    if self.tap is not None:
                        CGEventTapEnable(self.tap, True)
                    return event

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

        # Assign self.tap BEFORE enabling so the disable-event handler in the
        # callback can immediately call CGEventTapEnable(self.tap, True).
        self.tap = tap
        CGEventTapEnable(tap, True)
        logger.info("CGEventTap listener running (global).")

        try:
            while True:
                result = CFRunLoopRunInMode(kCFRunLoopDefaultMode, 1.0, False)
                if result == kCFRunLoopRunStopped:
                    # Intentional stop via stop() — clean exit, no restart.
                    break
                if result != kCFRunLoopRunTimedOut:
                    # kCFRunLoopRunFinished (1): the tap source was removed (e.g.
                    # permission revoked).  Log and fall through to the restart path.
                    logger.warning(
                        f"CFRunLoop exited with unexpected result {result} "
                        "(tap source may have been invalidated). "
                        "Hotkey listener will restart."
                    )
                    break
        except Exception as e:
            logger.error(f"CFRunLoop error in hotkey listener: {e}")
        finally:
            self._loop = None
            self.tap = None
            self._callback_fn = None

        # Auto-restart if the thread died for any reason other than an explicit stop().
        if self._should_run:
            logger.warning("Hotkey listener exited unexpectedly — restarting in 3 seconds...")
            time.sleep(3)
            if self._should_run:
                logger.info("Restarting hotkey listener...")
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
