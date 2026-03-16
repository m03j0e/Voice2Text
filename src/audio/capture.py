import numpy as np
from src.utils.logger import logger

def get_audio_devices():
    import sounddevice as sd
    devices = sd.query_devices()
    device_map = {}
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            name = device['name']
            if name in device_map:
                name = f"{name} ({i})"
            device_map[name] = i
    return device_map

class AudioCapture:
    def __init__(self, samplerate=16000, device_id=None, callback=None):
        self.samplerate = samplerate
        self.device_id = device_id
        self.callback = callback
        self.stream = None

    def start(self):
        import sounddevice as sd
        logger.info(f"Starting AudioCapture on device {self.device_id}...")
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            device=self.device_id,
            channels=1,
            callback=self.audio_callback,
            dtype='int16'
        )
        self.stream.start()
        logger.info("AudioCapture stream started.")

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def audio_callback(self, indata, frames, time, status):
        if self.callback:
            # Convert int16 to float32
            data_float = indata.astype(np.float32) / 32768.0
            self.callback(data_float, status)
