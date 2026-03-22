# Voice2Text for macOS

A native macOS Voice-to-Text application built with Python. It uses Apple's on-device `SFSpeechRecognizer` for high-quality, privacy-focused transcription and can inject text directly into any active application.

## Features

- **High Quality Transcription**: Uses macOS native Speech API (SFSpeechRecognizer) for accuracy and language support.
- **Global Hotkey**: Toggle recording from anywhere using the **Right Option** key.
- **Text Injection**: Automatically types transcribed text into your active window (TextEdit, Word, Browser, etc.).
- **Smart Formatting & Punctuation**: Automatically removes common filler words ("um", "uh", "like") and leverages macOS Apple Intelligence/ML to automatically add proper punctuation.
- **AI Polishing**: Optional integration with Google Gemini API to polish text, fix grammar, or apply custom prompts (e.g., "Make this more professional").
- **Visual Feedback**: Always-on-top floating indicator shows when you are actively recording.
- **Obsidian Integration**: Export your transcriptions directly to Obsidian as daily notes.
- **Corrections**: Intelligently handles backspacing and correction if the transcriber updates its prediction in real-time.

## Requirements

- **macOS** (10.15+ recommended)
- **Python 3.10+**
- **PortAudio** (for microphone access via `sounddevice`)

## Installation

1.  **Install PortAudio** (using Homebrew):
    ```bash
    brew install portaudio
    ```

2.  **Clone the repository**:
    ```bash
    git clone https://github.com/m03j0e/Voice2Text.git
    cd Voice2Text
    ```

3.  **Create a Virtual Environment & Install Dependencies**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the application**:
    ```bash
    ./venv/bin/python -m src.main
    ```

2.  **Grant Permissions**:
    - **Microphone**: You will be prompted to allow access.
    - **Accessibility**: Required for the Global Hotkey and Text Injection to work globally. Go to `System Settings` -> `Privacy & Security` -> `Accessibility` and enable your Terminal (or Python/App).

3.  **Start Dictating**:
    - Select your microphone from the dropdown.
    - Check "Inject Text into Active App" if you want it to type for you.
    - Check "Export to Obsidian" to save logs to your Obsidian vault.
    - Enable "AI Polish" and enter your Gemini API key for advanced text processing.
    - Click inside any other application (e.g., Notes).
    - Press **Right Option** to start recording.
    - Speak!
    - Press **Right Option** again to stop.

## How it Works (`src/main.py`)

The application combines several libraries to bridge Python with macOS native APIs, organized into modular components:

### 1. Audio Capture (`sounddevice`)
Instead of using PyObjC's complex audio engine, we use `sounddevice` (based on PortAudio) to capture raw audio samples from the microphone. This ensures broad compatibility with Bluetooth headsets and external mics.

### 2. Native Speech Recognition (`pyobjc-framework-Speech`)
We instantiate Apple's `SFSpeechRecognizer`. The raw audio from `sounddevice` (captured as numpy arrays) is manually copied into `AVAudioPCMBuffer` objects in memory using a fast loop. These buffers are then fed into the `SFSpeechAudioBufferRecognitionRequest` object, which processes them in real-time.

### 3. Global Hotkey (`Quartz CGEventTap`)
- **Keyboard Listener**: A `CGEventTap` (active tap) is created via the macOS Quartz event framework and runs on a dedicated background `CFRunLoop` thread. It detects the `Right Option` key (hardware keycode 61) globally, even when the app is minimized, by inspecting `kCGEventFlagsChanged` events without invoking any TSM (Carbon) APIs.
- **Tap Resilience**: macOS can automatically disable a `CGEventTap` on sleep/wake, user-input interruption, or a callback timeout. The listener handles `kCGEventTapDisabledByTimeout` and `kCGEventTapDisabledByUserInput` events and immediately re-enables the tap. If the run loop exits unexpectedly (e.g., the tap source is invalidated), the listener thread automatically restarts after a 3-second delay.
- **Keyboard Controller** (`pynput`): Text injection uses `pynput.keyboard.Controller`. It applies a "diffing" algorithm to compare new transcription text with what was previously typed. If the recognizer changes its prediction (e.g., correcting "weather" to "whether"), the app calculates the diff, sends the required **Backspace** taps, and types the new characters. AppleScript (`osascript`) is used as a fallback if `pynput` fails.

### 4. Text Processing
The `remove_filler_words` function uses Regular Expressions (`re`) to strip out hesitation markers like "um", "uh", "so", and "like" before the text is displayed or typed.

## Troubleshooting & Common Issues

The Voice2Text application relies on several system-level integrations (macOS accessibility, native frameworks, audio capture). If you encounter issues, review the solutions below.

### 1. Crashing on Startup (`Trace/BPT trap: 5`)
*   **Cause**: This usually happens if macOS security or native APIs (like `PyObjC` Speech, `sounddevice`, `pynput` or Security frameworks) are initialized before the Tkinter main thread is fully running. Importing these libraries at the module level (top-level) will trigger this crash when the module is loaded.
*   **Fix**: Ensure no native macOS UI elements or framework initializations are moved out of the `root.after()` staggered loading sequences in `src/ui/app_window.py`. Additionally, ensure that imports for `sounddevice`, `pynput`, `Speech`, `Cocoa`, and `AVFoundation` are strictly contained *inside* the functions or classes that use them, not at the top-level of the file.

### 2. Hotkeys Not Working or Only Working When App is in Focus
*   **Cause**: The `CGEventTap` listener requires the correct permission to receive global events. A common trap: `kCGSessionEventTap + listen-only` appears to succeed (macOS returns a non-None tap port) without Input Monitoring permission, but macOS silently restricts delivery to events targeting the focused process. The app avoids this by using `kCGHIDEventTap` (lowest level, fails fast with `None` when permission is denied) for the listen-only fallback.
*   **Fix**:
    1. Grant **Accessibility** to the exact binary shown in the startup dialog (`venv/bin/python` resolved to its real path) in `System Settings -> Privacy & Security -> Accessibility`. This is the preferred path — it enables an active tap that works globally.
    2. If Accessibility cannot be granted, grant **Input Monitoring** instead (`System Settings -> Privacy & Security -> Input Monitoring`). The app will fall back to a HID-level listen-only tap which is also global.
    3. After granting either permission, **restart the app** — permissions are checked at tap creation time.
    4. The app auto-detects tap-disable events (sleep/wake) and re-enables immediately; if the run loop exits unexpectedly it restarts within 3 seconds.

### 3. Text Injection Failing (AppleScript Fallback Error)
*   **Cause**: If `pynput` fails to inject text, the app attempts to use `osascript` (AppleScript) as a fallback. If both fail, it's a permissions issue.
*   **Fix**: Similar to hotkeys, ensure the app has **Accessibility** permissions. Check the console logs for "AppleScript injection failed" to confirm if the fallback is being triggered.

### 4. Linux Development & CI Errors
*   **Cause**: This is a macOS-first application. Running tests or the app on Linux will encounter missing libraries.
*   **Fix**:
    1. **PortAudio**: You must install the system library before `pip install`. Run: `sudo apt-get install -y portaudio19-dev`.
    2. **Headless X11**: When running tests involving `pynput` on Linux CI, you must start a virtual display: `Xvfb :0 -screen 0 1024x768x24 &` and `export DISPLAY=:0`.
    3. **macOS Frameworks**: Modules like `pyobjc-framework-Speech` and native commands like `afplay` will not work on Linux and must be mocked during testing.

### 5. AI Polishing Freezes the UI
*   **Cause**: Network calls to Google Gemini blocking the main thread.
*   **Fix**: Ensure AI processing remains dispatched to a background `threading.Thread` (e.g., `polish_and_dispatch`). Do not attempt to update Tkinter UI directly from this thread; use the `queue.Queue()`.

---

**⚠️ Developer / AI Agent Notice**
When troubleshooting or resolving new issues, environmental constraints, or bugs, you **must** ensure the `AGENTS.md` file is updated. This continuous documentation is required to support improved troubleshooting for future AI workflows and human developers.
