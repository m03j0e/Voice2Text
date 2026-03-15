import AppKit

class HotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.monitor = None
        self.local_monitor = None
        self.right_option_was_down = False

    def start(self):
        # The Right Option key is a modifier, so it generates FlagsChanged events, not KeyDown.
        # Key code for Right Option is 61.
        # modifierFlags mask for Right Option (NSEventModifierFlagOption) is 1 << 19 or 524288
        def handler(event):
            if event.keyCode() == 61:
                # Check if the Right Option flag is currently set in the modifierFlags
                # This distinguishes a "key down" from a "key up" for modifier keys
                is_down = (event.modifierFlags() & AppKit.NSEventModifierFlagOption) != 0

                # Only trigger the callback on the key down transition
                if is_down and not self.right_option_was_down:
                    if self.callback:
                        self.callback()

                self.right_option_was_down = is_down

        # Listen globally (when app is in background)
        self.monitor = AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            AppKit.NSEventMaskFlagsChanged,
            handler
        )

        # Listen locally (when app is in foreground)
        self.local_monitor = AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            AppKit.NSEventMaskFlagsChanged,
            lambda event: (handler(event), event)[1]
        )

    def stop(self):
        if self.monitor:
            AppKit.NSEvent.removeMonitor_(self.monitor)
            self.monitor = None
        if self.local_monitor:
            AppKit.NSEvent.removeMonitor_(self.local_monitor)
            self.local_monitor = None
