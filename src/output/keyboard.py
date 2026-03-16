from pynput import keyboard
from src.output.base import OutputDestination

class KeyboardInjector(OutputDestination):
    def __init__(self):
        self.last_typed_text = ""

    def reset(self):
        self.last_typed_text = ""

    def _type_fallback(self, text):
        import subprocess
        # AppleScript 'keystroke' into active application
        # Escaping for AppleScript
        escaped_text = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\r')
        script = f'tell application "System Events" to keystroke "{escaped_text}"'
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return True
        except Exception as e:
            return False

    def _get_controller(self):
        if not hasattr(self, 'keyboard_controller'):
            try:
                from pynput import keyboard
                self.keyboard_controller = keyboard.Controller()
            except Exception:
                self.keyboard_controller = None
        return self.keyboard_controller

    def output(self, text: str, is_final: bool = False):
        if not text:
            return

        from src.utils.logger import logger
        logger.debug(f"KeyboardInjector output: '{text}' (final={is_final})")
        
        current_len = len(self.last_typed_text)
        common_len = 0
        min_len = min(current_len, len(text))

        # Determine common prefix
        for i in range(min_len):
            if self.last_typed_text[i] != text[i]:
                break
            common_len += 1

        # Backspace execution
        backspaces_needed = current_len - common_len
        controller = self._get_controller()

        if backspaces_needed > 0:
            logger.debug(f"Pressing backspace {backspaces_needed} times")
            if controller:
                for _ in range(backspaces_needed):
                    controller.tap(keyboard.Key.backspace)
            else:
                # AppleScript fallback for backspace
                import subprocess
                script = f'tell application "System Events" to repeat {backspaces_needed} times\nkey code 51\nend repeat'
                subprocess.run(["osascript", "-e", script])

        # Type new characters
        to_type = text[common_len:]
        if to_type:
            logger.debug(f"Typing: '{to_type}'")
            if controller:
                try:
                    controller.type(to_type)
                except Exception:
                    self._type_fallback(to_type)
            else:
                self._type_fallback(to_type)

        self.last_typed_text = text
