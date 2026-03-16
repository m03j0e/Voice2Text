try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    import pytest
    pytest.skip('macOS only test', allow_module_level=True)

print("Listing Sound Devices:")
print(sd.query_devices())

print("\nDefault Input Device:")
try:
    default_device = sd.query_devices(kind='input')
    print(default_device)
except Exception as e:
    print(f"Error getting default device: {e}")

print("\nTesting 2 seconds of recording...")
try:
    fs = 44100  # Sample rate
    seconds = 2  # Duration of recording
    
    myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait until recording is finished
    print("Recording finished.")
    print(f"Max Amplitude: {np.max(np.abs(myrecording))}")
    if np.max(np.abs(myrecording)) > 0.01:
        print("Success: Audio signal detected!")
    else:
        print("Warning: Audio signal is silence (or near silence). Check microphone gain/mute.")
    
except Exception as e:
    print(f"Recording Error: {e}")
