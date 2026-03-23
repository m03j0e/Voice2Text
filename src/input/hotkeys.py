import time
import threading
from src.utils.logger import logger

# Right Option key hardware keycode
_RIGHT_OPTION_KEYCODE = 61

# Seconds to wait before restarting the tap after an unexpected exit
_RESTART_DELAY = 3.0

# Fallback values for tap-disabled constants in case PyObjC doesn't export them
try:
    from Quartz import kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput
except ImportError:
    kCGEventTapDisabledByTimeout   = 0xFFFFFFFE
    kCGEventTapDisabledByUserInput = 0xFFFFFFFF

_TAP_DISABLED_EVENTS = {kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput}


class HotkeyListener:
    """
    Detects the Right Option key via CGEventTap (kCGEventTapOptionDefault at
    kCGHIDEventTap).  Requires Accessibility permission granted in
    System Settings → Privacy & Security → Accessibility.

    Runs in a dedicated background thread — no conflict with Tkinter's mainloop.
    Auto-restarts if the tap dies unexpectedly (e.g. after sleep/wake).
    """

    def __init__(self, callback):
        self.callback = callback
        self.tap = None
        self._loop = None
        self.last_trigger_time = 0.0
        self._should_run = False

    def start(self):
        try:
            from HIServices import AXIsProcessTrusted
            if not AXIsProcessTrusted():
                logger.warning(
                    "[hotkey] Accessibility permission NOT granted. "
                    "Grant it in System Settings → Privacy & Security → Accessibility "
                    "then restart the app."
                )
        except Exception as e:
            logger.warning(f"[hotkey] Could not check Accessibility permission: {e}")

        self._should_run = True
        threading.Thread(target=self._run_tap, daemon=True).start()

    def stop(self):
        self._should_run = False
        loop = self._loop
        if loop is not None:
            try:
                from Quartz import CFRunLoopStop
                CFRunLoopStop(loop)
            except Exception as e:
                logger.error(f"[hotkey] Error stopping run loop: {e}")

    def _trigger(self):
        now = time.time()
        if now - self.last_trigger_time > 0.3:
            self.last_trigger_time = now
            logger.info("Hotkey Toggle Triggered (Right Option)!")
            if self.callback:
                self.callback()
        else:
            logger.debug(f"[hotkey] rising edge debounced (gap={now - self.last_trigger_time:.3f}s)")

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
            logger.error(f"[hotkey] Quartz not available: {e}")
            return

        def _callback(_proxy, event_type, event, _refcon):
            try:
                if event_type in _TAP_DISABLED_EVENTS:
                    reason = "timeout" if event_type == kCGEventTapDisabledByTimeout else "user-input"
                    logger.warning(f"[hotkey] CGEventTap disabled ({reason}) — re-enabling")
                    if self.tap is not None:
                        CGEventTapEnable(self.tap, True)
                    return event

                if event_type == kCGEventFlagsChanged:
                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    if keycode == _RIGHT_OPTION_KEYCODE:
                        flags = CGEventGetFlags(event)
                        if flags & kCGEventFlagMaskAlternate:
                            logger.debug("[hotkey] kCGEventFlagsChanged → Right Option DOWN")
                            self._trigger()
                        else:
                            logger.debug("[hotkey] kCGEventFlagsChanged → Right Option UP")
            except Exception as e:
                logger.error(f"[hotkey] callback error: {e}")
            return event

        # Hold a reference so the callback is not garbage collected
        self._callback_fn = _callback
        mask = 1 << kCGEventFlagsChanged

        while self._should_run:
            logger.info("[hotkey] Creating CGEventTap (kCGHIDEventTap / kCGEventTapOptionDefault)...")

            tap = CGEventTapCreate(
                kCGHIDEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionDefault,
                mask,
                _callback,
                None,
            )

            if tap is None:
                logger.error(
                    "[hotkey] CGEventTapCreate returned None — Accessibility permission required. "
                    "Grant it in System Settings → Privacy & Security → Accessibility."
                )
                time.sleep(_RESTART_DELAY)
                continue

            # Assign to self.tap BEFORE enabling so the callback's re-enable call
            # has a valid reference if a disable event arrives immediately.
            self.tap = tap

            source = CFMachPortCreateRunLoopSource(None, tap, 0)
            loop = CFRunLoopGetCurrent()
            self._loop = loop
            CFRunLoopAddSource(loop, source, kCFRunLoopDefaultMode)
            CGEventTapEnable(tap, True)

            logger.info("[hotkey] CGEventTap active — listening for Right Option globally.")

            # Run the loop in 5-second ticks so we can check _should_run and log heartbeats.
            tick = 0
            result = kCFRunLoopRunTimedOut
            while self._should_run:
                result = CFRunLoopRunInMode(kCFRunLoopDefaultMode, 5.0, False)
                tick += 1
                logger.debug(f"[hotkey] run loop tick #{tick}, result={result}")
                if result == kCFRunLoopRunStopped:
                    break
                # kCFRunLoopRunTimedOut (3) is normal — keep running

            self.tap = None
            self._loop = None

            if self._should_run and result != kCFRunLoopRunStopped:
                logger.warning(
                    f"[hotkey] tap exited unexpectedly (result={result}) — "
                    f"restarting in {_RESTART_DELAY}s"
                )
                time.sleep(_RESTART_DELAY)

        logger.info("[hotkey] CGEventTap listener stopped.")
