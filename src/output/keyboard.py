from pynput import keyboard
from src.output.base import OutputDestination

class KeyboardInjector(OutputDestination):
    def __init__(self):
        self.last_typed_text = ""

    def reset(self):
        self.last_typed_text = ""

    def _get_controller(self):
        if not hasattr(self, 'keyboard_controller'):
            from pynput import keyboard
            self.keyboard_controller = keyboard.Controller()
        return self.keyboard_controller

    def output(self, text: str, is_final: bool = False):
        if not text:
            return

        controller = self._get_controller()

        current_len = len(self.last_typed_text)
        common_len = 0
        min_len = min(current_len, len(text))

        # Simple optimization: if new text is just an extension of last_typed_text
        if text.startswith(self.last_typed_text):
             to_type = text[current_len:]
             if to_type:
                 controller.type(to_type)
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
                 controller.tap(keyboard.Key.backspace)

        # Type new characters
        to_type = text[common_len:]
        if to_type:
            controller.type(to_type)

        self.last_typed_text = text
