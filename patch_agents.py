with open("AGENTS.md", "r") as f:
    content = f.read()

new_content = content.replace(
    "2.  **Staggered Initialization:** The application uses `root.after()` (e.g., `root.after(800, self._initialize_recognizer)`) to defer native setups. Do not move native initialization back into synchronous paths before `mainloop()`.",
    "2.  **Staggered Initialization:** The application uses `root.after()` (e.g., `root.after(800, self._initialize_recognizer)`) to defer native setups. Do not move native initialization back into synchronous paths before `mainloop()`.\n3.  **Main Thread Imports:** Any native macOS library (like `pynput` or modules from `PyObjC`) that relies on system frameworks MUST be *imported* on the main thread first (e.g., in the `start()` method) before their objects or classes are used in background threads. Importing them for the first time inside a background thread (e.g., `threading.Thread`) will cause a fatal `Trace/BPT trap: 5` error."
)

new_content = new_content.replace(
    "3.  **No Native UI in Threads:**",
    "4.  **No Native UI in Threads:**"
)

new_content = new_content.replace(
    "1.  **Pynput Hotkeys:** The `pynput.keyboard.Listener` MUST be started in a separate `daemon=True` thread (`threading.Thread(target=self._run_listener, daemon=True).start()`). Initializing it from the main Tkinter thread loop on macOS will block the UI or cause `BPT traps`.",
    "1.  **Pynput Hotkeys:** The `pynput.keyboard.Listener` MUST be started in a separate `daemon=True` thread (`threading.Thread(target=self._run_listener, daemon=True).start()`). Initializing the listener loop from the main Tkinter thread on macOS will block the UI. However, the `import pynput` statement MUST happen on the main thread before starting the background thread to prevent `BPT traps`."
)

with open("AGENTS.md", "w") as f:
    f.write(new_content)
