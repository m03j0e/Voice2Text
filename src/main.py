import tkinter as tk
from src.ui.app_window import AppWindow
from src.output.keyboard import KeyboardInjector
from src.output.obsidian import ObsidianExporter
from src.utils.logger import logger
import Speech

def request_authorization():
    def auth_callback(status):
        logger.debug(f"Speech Authorization Status: {status}")
    Speech.SFSpeechRecognizer.requestAuthorization_(auth_callback)

def main():
    logger.info("--- Starting Voice2Text ---")
    request_authorization()

    root = tk.Tk()

    outputs = [
        KeyboardInjector(),
        ObsidianExporter()
    ]

    app = AppWindow(root, outputs=outputs)
    root.mainloop()

if __name__ == "__main__":
    main()
