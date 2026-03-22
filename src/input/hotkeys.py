import time
import threading
from src.utils.logger import logger

# Right Option key hardware keycode
_RIGHT_OPTION_KEYCODE = 61

# NSEventModifierFlagOption (same value as old NSAlternateKeyMask)
_NS_OPTION_FLAG = 1 << 19

# macOS sends these synthetic event types to a CGEventTap callback when the tap
# is auto-disabled.
try:
    from Quartz import kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput
except ImportError:
    kCGEventTapDisabledByTimeout   = 0xFFFFFFFE
    kCGEventTapDisabledByUserInput = 0xFFFFFFFF

_TAP_DISABLED_EVENTS = {kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput}


class HotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self._ns_monitor = None
        self.tap = None
        self._loop = None
        self.last_trigger_time = 0.0
        self._should_run = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        self._should_run = True

        # Primary: NSEvent global monitor.
        # Unlike CGEventTap, it has no "disabled-by-user-input" mechanism —
        # it simply delivers events to the main run loop as long as Input
        # Monitoring is granted.  Tkinter's mainloop() drives the Cocoa main
        # run loop on macOS, so no extra thread is needed.
        if self._start_ns_monitor():
            logger.info("Hotkey listener active (NSEvent global monitor).")
            return

        # Fallback: CGEventTap in a background thread.
        logger.warning("NSEvent monitor unavailable — falling back to CGEventTap.")
        threading.Thread(target=self._run_tap, daemon=True).start()

    def stop(self):
        self._should_run = False

        if self._ns_monitor is not None:
            try:
                import AppKit
                AppKit.NSEvent.removeMonitor_(self._ns_monitor)
                logger.info("NSEvent global monitor removed.")
            except Exception as e:
                logger.error(f"Error removing NSEvent monitor: {e}")
            finally:
                self._ns_monitor = None

        loop = self._loop
        if loop is not None:
            try:
                from Quartz import CFRunLoopStop
                CFRunLoopStop(loop)
            except Exception as e:
                logger.error(f"Error stopping CGEventTap run loop: {e}")

    # ------------------------------------------------------------------
    # NSEvent implementation (primary)
    # ------------------------------------------------------------------

    def _start_ns_monitor(self):
        """Install an NSEvent global monitor. Returns True on success."""
        try:
            import AppKit
        except ImportError:
            logger.warning("AppKit not available — cannot use NSEvent monitor.")
            return False

        # NSEventMaskFlagsChanged = 1 << 12
        mask = getattr(AppKit, 'NSEventMaskFlagsChanged', 1 << 12)

        _self = self

        def _handler(event):
            try:
                if event.keyCode() == _RIGHT_OPTION_KEYCODE:
                    flags = int(event.modifierFlags())
                    # Trigger on press (flag set), ignore release (flag cleared)
                    if flags & _NS_OPTION_FLAG:
                        now = time.time()
                        if now - _self.last_trigger_time > 0.3:
                            _self.last_trigger_time = now
                            logger.info("Hotkey Toggle Triggered (Right Option)!")
                            if _self.callback:
                                _self.callback()
            except Exception as e:
                logger.error(f"NSEvent handler error: {e}")

        monitor = AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            mask, _handler
        )

        if monitor is None:
            logger.warning(
                "NSEvent.addGlobalMonitorForEventsMatchingMask returned None. "
                "Grant Input Monitoring in System Settings > Privacy & Security."
            )
            return False

        self._ns_monitor = monitor
        return True

    # ------------------------------------------------------------------
    # CGEventTap fallback
    # ------------------------------------------------------------------

    def _run_tap(self):
        try:
            from Quartz import (
                CGEventTapCreate,
                CGEventTapEnable,
                CFMachPortCreateRunLoopSource,
                CFRunLoopAddSource,
                CFRunLoopGetCurrent,
                CFRunLoopRunInMode,
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
            logger.error(f"Quartz not available for CGEventTap fallback: {e}")
            return

        def _callback(_proxy, event_type, event, _refcon):
            try:
                if event_type in _TAP_DISABLED_EVENTS:
                    reason = "timeout" if event_type == kCGEventTapDisabledByTimeout else "user-input"
                    logger.warning(f"CGEventTap auto-disabled ({reason}) — re-enabling...")
                    if self.tap is not None:
                        CGEventTapEnable(self.tap, True)
                    return event

                if event_type == kCGEventFlagsChanged:
                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    if keycode == _RIGHT_OPTION_KEYCODE:
                        flags = CGEventGetFlags(event)
                        if flags & kCGEventFlagMaskAlternate:
                            now = time.time()
                            if now - self.last_trigger_time > 0.3:
                                self.last_trigger_time = now
                                logger.info("Hotkey Toggle Triggered (Right Option) [CGEventTap]!")
                                if self.callback:
                                    self.callback()
            except Exception as e:
                logger.error(f"CGEventTap callback error: {e}")
            return event

        self._callback_fn = _callback
        mask = 1 << kCGEventFlagsChanged

        # Try taps from most-global to least, stopping at first success.
        # kCGSessionEventTap + listen-only is intentionally skipped: macOS
        # lets creation succeed without Input Monitoring but silently
        # restricts delivery to the focused process (in-focus-only bug).
        tap = None
        tap_description = None

        tap = CGEventTapCreate(kCGHIDEventTap, kCGHeadInsertEventTap,
                               kCGEventTapOptionDefault, mask, _callback, None)
        if tap is not None:
            tap_description = "HID active (Accessibility granted)"

        if tap is None:
            tap = CGEventTapCreate(kCGSessionEventTap, kCGHeadInsertEventTap,
                                   kCGEventTapOptionDefault, mask, _callback, None)
            if tap is not None:
                tap_description = "session active (Accessibility granted)"

        if tap is None:
            tap = CGEventTapCreate(kCGHIDEventTap, kCGHeadInsertEventTap,
                                   kCGEventTapOptionListenOnly, mask, _callback, None)
            if tap is not None:
                tap_description = "HID listen-only (Input Monitoring granted)"

        if tap is None:
            logger.warning(
                "CGEventTap creation failed. Grant Input Monitoring or Accessibility "
                "in System Settings > Privacy & Security, then restart."
            )
            return

        logger.info(f"CGEventTap created: {tap_description}.")
        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        self._loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._loop, source, kCFRunLoopDefaultMode)
        self.tap = tap
        CGEventTapEnable(tap, True)
        logger.info("CGEventTap listener running.")

        try:
            while True:
                result = CFRunLoopRunInMode(kCFRunLoopDefaultMode, 1.0, False)
                if result == kCFRunLoopRunStopped:
                    break
                if result != kCFRunLoopRunTimedOut:
                    logger.warning(f"CFRunLoop exited unexpectedly (result={result}), restarting.")
                    break
        except Exception as e:
            logger.error(f"CFRunLoop error: {e}")
        finally:
            self._loop = None
            self.tap = None
            self._callback_fn = None

        if self._should_run:
            logger.warning("CGEventTap listener exited — restarting in 3 s...")
            time.sleep(3)
            if self._should_run:
                threading.Thread(target=self._run_tap, daemon=True).start()
