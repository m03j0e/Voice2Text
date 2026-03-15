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

    # MUST instantiate Tkinter BEFORE calling macOS native APIs to prevent NSApplication crash
    print("DEBUG: About to init tk.Tk()")
    root = tk.Tk()
    print("DEBUG: tk.Tk() initialized")

    outputs = [
        KeyboardInjector(),
        ObsidianExporter()
    ]

    print("DEBUG: About to init AppWindow()")
    app = AppWindow(root, outputs=outputs)
    print("DEBUG: AppWindow() initialized")
    
    # Request microphone/speech auth AFTER all other native/framework initializations
    # This prevents conflicts between Speech framework, Tkinter, and Keyring (Security framework)
    request_authorization()
    
    root.mainloop()

if __name__ == "__main__":
    main()
