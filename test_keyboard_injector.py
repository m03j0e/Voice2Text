import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock pynput.keyboard
mock_pynput = MagicMock()
sys.modules['pynput'] = mock_pynput
sys.modules['pynput.keyboard'] = mock_pynput.keyboard

from src.output.keyboard import KeyboardInjector

class TestKeyboardInjector(unittest.TestCase):
    def setUp(self):
        self.injector = KeyboardInjector()
        # Mock the controller to avoid pynput issues on Linux
        self.injector.keyboard_controller = MagicMock()

    @patch('src.output.keyboard.logger')
    @patch('subprocess.run')
    def test_output_diff(self, mock_run, mock_logger):
        # Initial state
        self.injector.last_typed_text = "Hello"

        # New text "He" - should backspace 3 times
        self.injector.output("He")
        self.assertEqual(self.injector.keyboard_controller.tap.call_count, 3)
        self.injector.keyboard_controller.tap.assert_called_with(mock_pynput.keyboard.Key.backspace)
        self.injector.keyboard_controller.type.assert_not_called()
        self.assertEqual(self.injector.last_typed_text, "He")

        self.injector.keyboard_controller.reset_mock()

        # New text "Healthy" - common is "He", so common_len=2.
        # backspaces_needed = len("He") - 2 = 0.
        # to_type = "althy"
        self.injector.output("Healthy")
        self.injector.keyboard_controller.tap.assert_not_called()
        self.injector.keyboard_controller.type.assert_called_with("althy")
        self.assertEqual(self.injector.last_typed_text, "Healthy")

    @patch('src.output.keyboard.logger')
    def test_output_no_common(self, mock_logger):
        self.injector.last_typed_text = "abc"
        self.injector.output("def")

        # Should backspace 3 times, then type "def"
        self.assertEqual(self.injector.keyboard_controller.tap.call_count, 3)
        self.injector.keyboard_controller.type.assert_called_with("def")
        self.assertEqual(self.injector.last_typed_text, "def")

if __name__ == '__main__':
    unittest.main()
