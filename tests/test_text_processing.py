import unittest
from src.utils.text_processing import remove_filler_words

class TestTextProcessing(unittest.TestCase):
    def test_remove_filler_words_basic(self):
        self.assertEqual(remove_filler_words("um hello"), "Hello")
        self.assertEqual(remove_filler_words("uh testing"), "Testing")
        self.assertEqual(remove_filler_words("like really"), "Really")
        self.assertEqual(remove_filler_words("so anyway"), "Anyway")
        self.assertEqual(remove_filler_words("you know what I mean"), "What I mean")

    def test_remove_filler_words_case_insensitive(self):
        self.assertEqual(remove_filler_words("UM hello"), "Hello")
        self.assertEqual(remove_filler_words("Uh testing"), "Testing")
        self.assertEqual(remove_filler_words("LIKE really"), "Really")

    def test_remove_filler_words_punctuation(self):
        self.assertEqual(remove_filler_words("thinking, uh, about"), "Thinking about")
        self.assertEqual(remove_filler_words("well, um, let's see"), "Well let's see")
        self.assertEqual(remove_filler_words("so, anyway"), "Anyway")

    def test_remove_filler_words_positions(self):
        # Start
        self.assertEqual(remove_filler_words("um I was saying"), "I was saying")
        # Middle
        self.assertEqual(remove_filler_words("I am uh happy"), "I am happy")
        # End
        self.assertEqual(remove_filler_words("I am happy so"), "I am happy")

    def test_remove_filler_words_multi(self):
        self.assertEqual(remove_filler_words("um, so, like, anyway"), "Anyway")
        self.assertEqual(remove_filler_words("uh, you know, it is like fine"), "It is fine")

    def test_remove_filler_words_word_boundaries(self):
        # Should not remove words that contain fillers as substrings
        self.assertEqual(remove_filler_words("summary"), "Summary")
        self.assertEqual(remove_filler_words("sofa"), "Sofa")
        self.assertEqual(remove_filler_words("alike"), "Alike")
        self.assertEqual(remove_filler_words("sound"), "Sound")

    def test_remove_filler_words_empty_null(self):
        self.assertEqual(remove_filler_words(""), "")
        self.assertEqual(remove_filler_words(None), None)

    def test_remove_filler_words_capitalization(self):
        self.assertEqual(remove_filler_words("um, hello world"), "Hello world")
        self.assertEqual(remove_filler_words("hello world"), "Hello world")

    def test_remove_filler_words_hanging_punctuation(self):
        self.assertEqual(remove_filler_words(", , so anyway"), "Anyway")
        self.assertEqual(remove_filler_words("  , um hello"), "Hello")

if __name__ == "__main__":
    unittest.main()
