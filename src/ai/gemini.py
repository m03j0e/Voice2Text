from google import genai
import keyring
from src.utils.logger import logger

class GeminiClient:
    def __init__(self, service_name="voice2text_mac", defer_init=False):
        self.service_name = service_name
        self.api_key = None
        self.client = None
        self.model_name = 'gemini-3.0-flash'
        self.has_key = False

        if not defer_init:
            self._setup_client()

    def initialize(self):
        """Manually trigger the keychain fetch and client setup if it was deferred."""
        if not self.has_key:
            self._setup_client()
        return self.has_key

    def _setup_client(self):
        try:
            self.api_key = keyring.get_password(self.service_name, "gemini_api_key")
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
                self.has_key = True
                logger.debug("Successfully retrieved Gemini API key from keychain.")
            else:
                self.client = None
                self.has_key = False
                logger.warning("Gemini API key not found in keychain.")
        except Exception as e:
            self.client = None
            self.has_key = False
            logger.error(f"Error accessing keychain for Gemini API key: {e}")

    def set_api_key(self, api_key: str):
        if not api_key:
            return False
        try:
            keyring.set_password(self.service_name, "gemini_api_key", api_key)
            self._setup_client()
            return True
        except Exception as e:
            logger.error(f"Failed to save API key to keychain: {e}")
            return False

    def polish_text(self, text: str, prompt: str) -> str:
        if not self.has_key or not self.client:
            logger.error("Attempted to polish text without an API key configured.")
            return text

        if not text.strip():
            return text

        full_prompt = f"{prompt}\n\nText to polish:\n{text}"
        try:
            logger.debug("Sending text to Gemini for polishing...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            if response.text:
                polished = response.text.strip()
                logger.debug("Successfully received polished text.")
                return polished
            else:
                logger.warning("Received empty response from Gemini.")
                return text
        except Exception as e:
            logger.error(f"Error during Gemini generation: {e}")
            return text
