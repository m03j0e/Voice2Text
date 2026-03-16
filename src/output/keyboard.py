from pynput import keyboard
from src.output.base import OutputDestination
from src.utils.logger import logger

class KeyboardInjector(OutputDestination):
    def __init__(self):
        self.last_typed_text = ""

    def reset(self):
        self.last_typed_text = ""

    def _type_fallback(self, text):
        import subprocess
        logger.debug(f"Attempting AppleScript fallback for: '{text}'")
        
        # AppleScript 'keystroke' into active application
        # Escaping for AppleScript
        escaped_text = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\r')
        script = f'tell application "System Events" to keystroke "{escaped_text}"'
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"AppleScript injection failed: {result.stderr.strip()}")
                return False
            logger.debug("AppleScript injection successful.")
            return True
        except Exception as e:
            logger.error(f"Subprocess error in AppleScript: {e}")
            return False

    def _get_controller(self):
        if not hasattr(self, 'keyboard_controller'):
            try:
                from pynput import keyboard
                self.keyboard_controller = keyboard.Controller()
                logger.debug("Pynput keyboard controller initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize pynput controller: {e}")
                self.keyboard_controller = None
        return self.keyboard_controller

    def output(self, text: str, is_final: bool = False):
        if not text:
            return
        
        logger.debug(f"KeyboardInjector processing: '{text}' (final={is_final})")
        
        current_len = len(self.last_typed_text)
        common_len = 0
        min_len = min(current_len, len(text))

        # Determine common prefix
        for i in range(min_len):
            if self.last_typed_text[i] == text[i]:
                common_len += 1
            else:
                break

        # Backspace execution
        backspaces_needed = current_len - common_len
        controller = self._get_controller()

        if backspaces_needed > 0:
            logger.info(f"Injection: Sending {backspaces_needed} backspaces")
            success = False
            if controller:
                try:
                    # Clear last_typed_text temporarily so we don't get recursive loops
                    for _ in range(backspaces_needed):
                        controller.tap(keyboard.Key.backspace)
                    success = True
                except Exception as e:
                    logger.warning(f"Pynput backspace failed: {e}")
            
            if not success:
                # AppleScript fallback for backspace (Key code 51 is delete)
                import subprocess
                script = f'tell application "System Events" to repeat {backspaces_needed} times\nkey code 51\nend repeat'
                subprocess.run(["osascript", "-e", script])

        # Type new characters
        to_type = text[common_len:]
        if to_type:
            logger.info(f"Injection: Typing '{to_type}'")
            success = False
            if controller:
                try:
                    controller.type(to_type)
                    success = True
                    logger.debug("Pynput typing successful.")
                except Exception as e:
                    logger.warning(f"Pynput typing failed: {e}")
            
            if not success:
               self._type_fallback(to_type)

        # Update tracking
        self.last_typed_text = text
        
        # At the end of a session, we reset the baseline for the next recording
        if is_final:
            self.last_typed_text = ""
