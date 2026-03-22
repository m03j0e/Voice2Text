
import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock dependencies before importing the module under test
sys.modules['pynput'] = MagicMock()
sys.modules['pynput.keyboard'] = MagicMock()

from src.output.keyboard import KeyboardInjector

class TestKeyboardInjection(unittest.TestCase):
    @patch('subprocess.run')
    def test_type_fallback_secure(self, mock_run):
        injector = KeyboardInjector()

        # We need to mock return value so the code continues
        mock_run.return_value = MagicMock(returncode=0)

        # A payload that would have been an injection breakout
        breakout_payload = '\nend tell\ndo shell script "whoami"\n--'
        injector._type_fallback(breakout_payload)

        # Check the call to subprocess.run
        mock_run.assert_called()
        args, kwargs = mock_run.call_args
        command = args[0]

        # command is expected to be ["osascript", "-e", script, normalized_text]
        script = command[2]
        text_arg = command[3]

        # Verify it's using the parameterized pattern
        self.assertIn('on run argv', script)
        self.assertIn('item 1 of argv', script)

        # Verify the text is passed as a separate argument and normalized (\n to \r)
        self.assertEqual(text_arg, breakout_payload.replace('\n', '\r'))

    @patch('subprocess.run')
    def test_backspace_fallback_secure(self, mock_run):
        injector = KeyboardInjector()
        injector.last_typed_text = "Hello"

        # To trigger backspaces, we need to provide text that has different start or shorter
        # and we need to make sure pynput fails
        injector.keyboard_controller = None # This will trigger fallback

        # We need to mock return value
        mock_run.return_value = MagicMock(returncode=0)

        # Change text to something shorter to trigger backspaces
        injector.output("He")

        # Check all calls to mock_run
        backspace_call = None
        for call in mock_run.call_args_list:
            command = call[0][0] # call[0] is the tuple of positional args, [0] is the first arg (the command list)
            if len(command) > 2 and 'repeat' in command[2]:
                backspace_call = call
                break

        self.assertIsNotNone(backspace_call, "Backspace fallback was not called")
        command = backspace_call[0][0]
        script = command[2]
        count_arg = command[3]

        self.assertIn('on run argv', script)
        self.assertIn('item 1 of argv as integer', script)
        self.assertEqual(count_arg, "3") # "Hello" -> "He" needs 3 backspaces

    @patch('subprocess.run')
    def test_type_fallback_tricky_text(self, mock_run):
        injector = KeyboardInjector()
        mock_run.return_value = MagicMock(returncode=0)

        tricky_text = 'Backslash \\ and Quote " and Newline \n'
        injector._type_fallback(tricky_text)

        args, kwargs = mock_run.call_args
        text_arg = args[0][3]

        # Verify normalization and no double-escaping
        expected_text = 'Backslash \\ and Quote " and Newline \r'
        self.assertEqual(text_arg, expected_text)

if __name__ == '__main__':
    unittest.main()
