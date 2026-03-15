import google.generativeai as genai
import keyring
from src.utils.logger import logger

class GeminiClient:
    def __init__(self, service_name="voice2text_mac"):
        self.service_name = service_name
        self._setup_client()

    def _setup_client(self):
        api_key = keyring.get_password(self.service_name, "gemini_api_key")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-3.0-flash')
            self.has_key = True
        else:
            self.model = None
            self.has_key = False
            logger.warning("Gemini API key not found in keyring.")

    def set_api_key(self, api_key: str):
        if not api_key:
            return False
        try:
            keyring.set_password(self.service_name, "gemini_api_key", api_key)
            self._setup_client()
            return True
        except Exception as e:
            logger.error(f"Failed to set API key: {e}")
            return False

    def polish_text(self, text: str, prompt: str) -> str:
        if not self.has_key or not self.model:
            logger.error("Attempted to polish text without an API key configured.")
            return text

        if not text.strip():
            return text

        full_prompt = f"{prompt}\n\nText to polish:\n{text}"
        try:
            logger.debug("Sending text to Gemini for polishing...")
            response = self.model.generate_content(full_prompt)
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
