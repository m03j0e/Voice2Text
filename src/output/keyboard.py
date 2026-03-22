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
        
        # Use parameterized AppleScript to prevent code injection
        script = 'on run argv\ntell application "System Events" to keystroke (item 1 of argv)\nend run'
        normalized_text = text.replace('\n', '\r')
        try:
            result = subprocess.run(["osascript", "-e", script, normalized_text], capture_output=True, text=True)
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
        if not text or not text.strip():
            logger.debug("KeyboardInjector: empty text, skipping.")
            return
        
        logger.debug(f"KeyboardInjector processing: '{text}' (final={is_final})")

        # If text is identical to what we already typed, skip (prevents duplicate dispatch)
        if text == self.last_typed_text:
            logger.debug("KeyboardInjector: text identical to last typed, skipping.")
            return
        
        current_len = len(self.last_typed_text)
        common_len = 0
        min_len = min(current_len, len(text))

        for i in range(min_len):
            if self.last_typed_text[i] == text[i]:
                common_len += 1
            else:
                break

        backspaces_needed = current_len - common_len
        controller = self._get_controller()

        if backspaces_needed > 0:
            logger.info(f"Injection: Sending {backspaces_needed} backspaces")
            success = False
            if controller:
                try:
                    from pynput import keyboard
                    for _ in range(backspaces_needed):
                        controller.tap(keyboard.Key.backspace)
                    success = True
                except Exception as e:
                    logger.warning(f"Pynput backspace failed: {e}")
            
            if not success:
                import subprocess
                # Use parameterized AppleScript for better security posture
                script = 'on run argv\ntell application "System Events" to repeat (item 1 of argv as integer) times\nkey code 51\nend repeat\nend run'
                subprocess.run(["osascript", "-e", script, str(backspaces_needed)])

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

        self.last_typed_text = text
        # Do NOT reset last_typed_text on is_final — reset() handles that
        # at the start of the next recording session. This prevents late
        # duplicate dispatches from retyping the entire text.
