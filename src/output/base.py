from abc import ABC, abstractmethod

class OutputDestination(ABC):
    @abstractmethod
    def output(self, text: str, is_final: bool = False):
        """
        Send text to the destination.
        :param text: The text to send.
        :param is_final: Whether this is the final finalized text for the session.
        """
        pass

    def reset(self):
        """Reset any state before a new recording starts."""
        pass
