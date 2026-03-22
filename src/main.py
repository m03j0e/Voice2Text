import tkinter as tk
from src.utils.logger import logger

def request_authorization():
    try:
        import Speech
        def auth_callback(status: int) -> None:
            logger.debug(f"Speech Authorization Status: {status}")
        Speech.SFSpeechRecognizer.requestAuthorization_(auth_callback)
    except ImportError:
        logger.warning("Speech framework not available. Skipping authorization.")

def main():
    logger.info("--- Starting Voice2Text ---")

    root = tk.Tk()

    from src.ui.app_window import AppWindow
    from src.output.keyboard import KeyboardInjector

    app = AppWindow(root, outputs=[KeyboardInjector()])

    root.after(2000, request_authorization)
    root.mainloop()

if __name__ == "__main__":
    main()
