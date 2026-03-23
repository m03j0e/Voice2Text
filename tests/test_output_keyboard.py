import sys
import unittest
from unittest.mock import MagicMock

# Mock pynput before importing KeyboardInjector
mock_pynput = MagicMock()
mock_keyboard = MagicMock()
mock_pynput.keyboard = mock_keyboard
sys.modules['pynput'] = mock_pynput
sys.modules['pynput.keyboard'] = mock_keyboard

from src.output.keyboard import KeyboardInjector

class TestKeyboardInjector(unittest.TestCase):
    def setUp(self):
        self.injector = KeyboardInjector()
        # Mocking controller to avoid native API calls and dependencies
        self.injector.keyboard_controller = MagicMock()

    def test_output_logic(self):
        test_cases = [
            # (initial_text, new_text, expected_backspaces, expected_typed)
            ("", "Hello", 0, "Hello"),
            ("Hello", "Hello world", 0, " world"),
            ("Hello world", "Hello word", 2, "d"),
            ("Hello word", "Hi", 9, "i"),
            ("Hi", "Hi", 0, ""), # Should be skipped by the "identical text" check
            ("Hi", "", 0, ""), # Should be skipped by the "empty text" check
            ("Hello", "Helper", 2, "per"),
        ]

        # In our mock environment, we can set up the expected Key values
        mock_keyboard.Key.backspace = 'backspace_key'

        for initial, new, expected_bs, expected_typed in test_cases:
            self.injector.last_typed_text = initial
            self.injector.keyboard_controller.reset_mock()

            self.injector.output(new)

            # Cases that should be short-circuited
            if not new or not new.strip() or new == initial:
                continue

            # Check backspaces: it should call tap(Key.backspace) expected_bs times
            actual_bs = 0
            for call in self.injector.keyboard_controller.tap.call_args_list:
                if call[0][0] == 'backspace_key':
                    actual_bs += 1
            self.assertEqual(actual_bs, expected_bs, f"Backspace count mismatch for '{initial}' -> '{new}'")

            # Check typed text
            if expected_typed:
                self.injector.keyboard_controller.type.assert_called_with(expected_typed)
            else:
                self.injector.keyboard_controller.type.assert_not_called()

            # Verify internal state updated correctly
            self.assertEqual(self.injector.last_typed_text, new)

if __name__ == '__main__':
    unittest.main()
