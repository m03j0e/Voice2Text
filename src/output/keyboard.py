from src.output.base import OutputDestination
import Quartz
import time

class KeyboardInjector(OutputDestination):
    def __init__(self):
        self.last_typed_text = ""

    def reset(self):
        self.last_typed_text = ""

    def _tap_key(self, keycode):
        # Create key down event
        event_down = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)

        # Create key up event
        event_up = Quartz.CGEventCreateKeyboardEvent(None, keycode, False)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)

        # Slight delay to ensure events are processed
        time.sleep(0.005)

    def _type_string(self, text):
        # We can use CGEventKeyboardSetUnicodeString to type characters
        # without worrying about exact keyboard layouts and shift states.
        for char in text:
            # Create a dummy keyboard event (keycode 0 doesn't matter much here)
            event_down = Quartz.CGEventCreateKeyboardEvent(None, 0, True)
            utf16_len = len(char.encode('utf-16-le')) // 2
            Quartz.CGEventKeyboardSetUnicodeString(event_down, utf16_len, char)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)

            event_up = Quartz.CGEventCreateKeyboardEvent(None, 0, False)
            Quartz.CGEventKeyboardSetUnicodeString(event_up, utf16_len, char)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)

            time.sleep(0.005)

    def output(self, text: str, is_final: bool = False):
        if not text:
            return

        current_len = len(self.last_typed_text)
        common_len = 0
        min_len = min(current_len, len(text))

        # Simple optimization: if new text is just an extension of last_typed_text
        if text.startswith(self.last_typed_text):
             to_type = text[current_len:]
             if to_type:
                 self._type_string(to_type)
             self.last_typed_text = text
             return

        # Mismatch (correction) or completely new text
        for i in range(min_len):
            if self.last_typed_text[i] != text[i]:
                break
            common_len += 1

        if self.last_typed_text[:min_len] == text[:min_len]:
            common_len = min_len

        # Backspace execution
        backspaces_needed = current_len - common_len
        if backspaces_needed > 0:
             for _ in range(backspaces_needed):
                 # Keycode 51 is the Delete (Backspace) key on macOS
                 self._tap_key(51)

        # Type new characters
        to_type = text[common_len:]
        if to_type:
            self._type_string(to_type)

        self.last_typed_text = text
