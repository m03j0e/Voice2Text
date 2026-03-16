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

    # Initialize Tkinter first. On macOS, this initializes the NSApplication.
    root = tk.Tk()
    
    # Initialize destinations. 
    # KeyboardInjector is lazy-initialized to avoid native API conflicts at startup.
    outputs = [
        KeyboardInjector(),
        ObsidianExporter()
    ]

    # Create the application window.
    # Most heavy/native initializations are deferred within AppWindow using root.after().
    app = AppWindow(root, outputs=outputs)
    
    # Request microphone/speech authorization after a short delay to ensure stability.
    root.after(2000, request_authorization)
    
    root.mainloop()

if __name__ == "__main__":
    main()
