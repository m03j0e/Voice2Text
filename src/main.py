import tkinter as tk
from src.ui.app_window import AppWindow
from src.output.keyboard import KeyboardInjector
from src.output.obsidian import ObsidianExporter
from src.utils.logger import logger

def request_authorization():
    import Speech
    def auth_callback(status: int) -> None:
        logger.debug(f"Speech Authorization Status: {status}")
    Speech.SFSpeechRecognizer.requestAuthorization_(auth_callback)

def main():
    logger.info("--- Starting Voice2Text ---")

    logger.info("Instantiating Tk...")
    root = tk.Tk()
    logger.info("Tk instantiated.")
    
    # We will initialize outputs and app window, but we delay the native API calls
    logger.info("Initializing context...")
    outputs = [
        KeyboardInjector(),
        ObsidianExporter()
    ]

    logger.info("Creating AppWindow...")
    app = AppWindow(root, outputs=outputs)
    logger.info("AppWindow created.")
    
    # Request microphone/speech authorization after a short delay to ensure stability.
    root.after(2000, request_authorization)
    
    root.mainloop()

if __name__ == "__main__":
    main()
