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

    # Run as a background accessory app so the Tkinter event loop never steals
    # keyboard focus from the user's target application when a hotkey fires.
    # With NSApplicationActivationPolicyAccessory the window is visible and
    # interactive (clicking on it still works) but it will not become the key
    # application unless the user explicitly clicks its window.
    try:
        import Cocoa
        Cocoa.NSApplication.sharedApplication().setActivationPolicy_(
            Cocoa.NSApplicationActivationPolicyAccessory
        )
        logger.info("Activation policy set to Accessory (no focus stealing).")
    except Exception as e:
        logger.warning(f"Could not set activation policy: {e}")

    from src.ui.app_window import AppWindow
    from src.output.keyboard import KeyboardInjector

    app = AppWindow(root, outputs=[KeyboardInjector()])

    root.after(2000, request_authorization)
    root.mainloop()

if __name__ == "__main__":
    main()
