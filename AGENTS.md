# Voice2Text AI Agent Guidelines

Welcome, Agent. You are working on the Voice2Text macOS application. This document contains crucial environmental constraints, architectural rules, and troubleshooting context derived from the codebase and development history.

**Read and adhere to these guidelines before making changes or attempting to fix bugs.**

## Core Directive: Continuous Troubleshooting Improvement
*   **Mandatory Update Rule**: Whenever you (the AI agent) troubleshoot and successfully resolve a new issue, bug, or environmental constraint within this project, you **MUST** update this `AGENTS.md` file (and the Troubleshooting section in `README.md` if applicable) to document the solution.
*   **Goal**: Ensure future AI workflows and human developers do not have to rediscover the same solutions.

## Architecture and UI Initialization Constraints (macOS)
The application heavily relies on native macOS APIs (`PyObjC`, `Speech`, `Cocoa`, `Security`) alongside `Tkinter`. Initializing these in the wrong order will cause fatal crashes (e.g., `Trace/BPT trap: 5`).

1.  **Tkinter First:** `tk.Tk()` and its `mainloop()` must be fully initialized *before* importing or calling any macOS native APIs or libraries that trigger security checks (e.g., `SFSpeechRecognizer`, `Security` framework via AI clients/keyring).
2.  **Staggered Initialization:** The application uses `root.after()` (e.g., `root.after(800, self._initialize_recognizer)`) to defer native setups. Do not move native initialization back into synchronous paths before `mainloop()`.
3.  **Main Thread Imports:** Any native macOS library (like `pynput` or modules from `PyObjC`) that relies on system frameworks MUST be *imported* on the main thread first (e.g., in the `start()` method) before their objects or classes are used in background threads. Importing them for the first time inside a background thread (e.g., `threading.Thread`) will cause a fatal `Trace/BPT trap: 5` error.
4.  **No Native UI in Threads:** Do not attempt to update `Tkinter` widgets or spawn native dialogs (e.g., `NSPanel`) directly from background threads (like the AI processing thread or audio callback). Always use a `queue.Queue()` and `root.after` polling to pass data back to the main thread.


5.  **Module-Level Imports of Native Libraries:** Do NOT import native macOS libraries (`sounddevice`, `Speech`, `Cocoa`, `AVFoundation`, `pynput`) at the top level of any Python module. If a module containing such an import is imported before `Tkinter.mainloop()` starts (even just to access a utility function), it will trigger native API initialization and cause a `Trace/BPT trap: 5` crash. Always place these imports *inside* the functions or classes that use them.

## Background Threads and Daemons
1.  **Pynput Hotkeys:** The hotkey listener now uses `pynput.keyboard.Listener` on a dedicated background thread. This simplifies hotkey polling, removing complex logic and reliance on manually re-enabling Quartz manual event taps. Ensure `pynput` is installed and imported safely (e.g. inside thread to avoid `Trace/BPT trap: 5`). Accessibility permissions are still required on macOS.
2.  **AI Polishing:** AI calls (e.g., Google Gemini) are synchronous network operations. They must be dispatched to a background thread (`threading.Thread`) to prevent freezing the UI.

## Testing and CI Constraints
1.  **Linux Headless Testing:** The project utilizes macOS-specific frameworks (`pyobjc-framework-Speech`, `Cocoa`, `afplay`) which *cannot* be installed or executed on Linux environments. Testing these macOS-native modules on Linux CI/test environments will fail without proper mocking.
2.  **X11 Display Requirement:** When verifying `pynput` or other X11-dependent UI libraries on headless Linux environments, you must start a virtual framebuffer: `Xvfb :0 -screen 0 1024x768x24 &` and set `DISPLAY=:0` to prevent `DisplayNameError`.
3.  **PortAudio Requirement:** `sounddevice` depends on system-level PortAudio. When setting up or testing the environment on Linux/Ubuntu, execute `sudo apt-get install -y portaudio19-dev` *prior* to installing Python dependencies.

## Known Errors and Expected Behaviors
1.  **kAFAssistantErrorDomain 1110:** In `speech/recognizer.py`, this error code is safe to ignore (`pass`). It usually occurs when the audio stream ends or is momentarily interrupted.
2.  **kLSRErrorDomain 301 ("Recognition request was canceled"):** In `speech/recognizer.py`, this error fires after `endAudio()` on every normal recording stop. It is expected and silently ignored. Treating it as a real error will cause confusing log noise.
3.  **AppleScript Fallback:** In `output/keyboard.py`, `pynput` is the primary injection method, but AppleScript (`osascript`) is used as a fallback if `pynput` fails due to permissions or environment issues.

## Post-Stop Race Conditions (Resolved)
After `stop_recording()`, Apple's `SFSpeechRecognizer` continues to fire result callbacks with stale or empty transcription text. These late arrivals can corrupt the injected text. The fix is a **three-layer guard**:

1.  **Recognizer (`_stopped` flag):** `Recognizer.stop()` sets `self._stopped = True`. The `recognition_result_handler` checks this flag and silently discards any callbacks that arrive after stop. `start()` resets it to `False`.
2.  **AppWindow (`is_recording` guard):** `on_recognition_result()` returns immediately if `self.is_recording` is `False`. Additionally, `process_queue()` discards `"text"` queue messages when not recording.
3.  **KeyboardInjector (no is_final reset):** `output()` does **not** reset `last_typed_text` on `is_final=True`. The reset only happens in `reset()` at the start of the next recording. This prevents duplicate dispatches from retyping text. Empty and identical-text dispatches are also short-circuited.

**Never remove any of these guards** — they work together to prevent the race condition.

## Performance Optimizations
1.  **Common Prefix Search**: In `src/output/keyboard.py`, the manual character-by-character loop for finding the common prefix between the previously typed text and the new transcription has been replaced with `os.path.commonprefix`. While `os.path.commonprefix` is primarily for file paths, it is implemented efficiently in Python and provides a measurably faster result (up to 30% improvement) for longer strings (1000+ characters) compared to a basic Python loop.

## State Feedback
*   The application uses the native macOS `afplay` command (e.g., `afplay /System/Library/Sounds/Ping.aiff`) for audio feedback on state changes. Do not replace this with cross-platform libraries unless explicitly requested.
