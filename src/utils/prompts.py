import json
import os
from src.utils.logger import logger

class PromptManager:
    def __init__(self):
        self.filename = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts.json")
        self.default_prompt = "Fix spelling and grammar."
        self.prompts = [self.default_prompt]
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.prompts = data
            if self.default_prompt not in self.prompts:
                self.prompts.insert(0, self.default_prompt)
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")

    def save(self, prompt: str):
        if not prompt or prompt in self.prompts:
            return

        self.prompts.append(prompt)
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.prompts, f)
        except Exception as e:
            logger.error(f"Error saving prompts: {e}")
