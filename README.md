# Voice2Text for macOS

A native macOS Voice-to-Text application built with Python. It uses Apple's on-device `SFSpeechRecognizer` for high-quality, privacy-focused transcription and can inject text directly into any active application.

## Features

- **High Quality Transcription**: Uses macOS native Speech API (SFSpeechRecognizer) for accuracy and language support.
- **Global Hotkey**: Toggle recording from anywhere using the **Right Option** key.
- **Text Injection**: Automatically types transcribed text into your active window (TextEdit, Word, Browser, etc.).
- **Smart Formatting**: Automatically removes common filler words ("um", "uh", "like") and handles capitalization.
- **Corrections**: intelligently handles backspacing and correction if the transcriber updates its prediction.

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

### 3. Global Inputs (`pynput`)
- **Keyboard Listener**: Runs in a background thread to detect the `Right Option` key press globally, even when the app is minimized.
- **Keyboard Controller**: Simulates keystrokes. It uses a "diffing" algorithm (`handle_typing`) to compare the new transcription with what was previously typed. If the recognizer changes its mind (e.g., correcting "weather" to "whether"), the app calculates the difference, sends valid **Backspace** taps, and types the new characters.

### 4. Text Processing
The `remove_filler_words` function uses Regular Expressions (`re`) to strip out hesitation markers like "um", "uh", "so", and "like" before the text is displayed or typed.
