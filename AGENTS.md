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
1.  **CGEventTap Hotkeys:** The hotkey listener uses `Quartz.CGEventTapCreate` (NOT pynput) running its own `CFRunLoop` on a dedicated `daemon=True` background thread (`HotkeyListener._run_tap`). All Quartz imports happen inside `_run_tap`, never at module level. Key stability behaviours:
    - macOS auto-disables a tap on sleep/wake or callback timeout. The callback handles `kCGEventTapDisabledByTimeout` and `kCGEventTapDisabledByUserInput` by immediately calling `CGEventTapEnable(self.tap, True)`.
    - `self.tap` is assigned **before** `CGEventTapEnable` is called so the re-enable path in the callback always has a valid reference.
    - If the run loop exits with any result other than `kCFRunLoopRunTimedOut` (normal heartbeat) or `kCFRunLoopRunStopped` (intentional stop via `stop()`), the thread restarts itself after a 3-second delay as long as `_should_run` is `True`.
    - `stop()` sets `_should_run = False` before calling `CFRunLoopStop` so the restart logic knows not to restart.
    - **CRITICAL — tap location / option fallback order**: `kCGSessionEventTap + kCGEventTapOptionListenOnly` is **intentionally skipped**. Without Input Monitoring permission, macOS lets that creation return non-None but silently restricts event delivery to the focused process only (in-focus-only bug). The correct order is:
      1. `kCGHIDEventTap` active (Accessibility) → truly global
      2. `kCGSessionEventTap` active (Accessibility) → truly global
      3. `kCGHIDEventTap` listen-only (Input Monitoring) → returns `None` if denied (safe fail)
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

## State Feedback
*   The application uses the native macOS `afplay` command (e.g., `afplay /System/Library/Sounds/Ping.aiff`) for audio feedback on state changes. Do not replace this with cross-platform libraries unless explicitly requested.
