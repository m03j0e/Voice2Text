with open("README.md", "r") as f:
    content = f.read()

new_content = content.replace(
    "1.  **Crashing on Startup (`Trace/BPT trap: 5`)**\n*   **Cause**: This usually happens if macOS security or native APIs (like `PyObjC` Speech or Security frameworks) are initialized before the Tkinter main thread is fully running.\n*   **Fix**: Ensure no native macOS UI elements or framework initializations are moved out of the `root.after()` staggered loading sequences in `src/ui/app_window.py`.",
    "1.  **Crashing on Startup (`Trace/BPT trap: 5`)**\n*   **Cause**: This usually happens if macOS security or native APIs (like `PyObjC` Speech or Security frameworks) are initialized before the Tkinter main thread is fully running, OR if native macOS libraries (like `pynput`) are imported for the first time on a background thread.\n*   **Fix**: Ensure no native macOS UI elements or framework initializations are moved out of the `root.after()` staggered loading sequences in `src/ui/app_window.py`. Also verify that any `import pynput` statements occur on the main thread (e.g., in a `start()` method) before spinning up a background thread to use them."
)

with open("README.md", "w") as f:
    f.write(new_content)
