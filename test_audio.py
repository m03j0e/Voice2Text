import time
import sys
try:
    import Cocoa
except ImportError:
    import pytest
    pytest.skip('macOS only test', allow_module_level=True)
    Cocoa = type('Dummy', (), {'NSObject': object})
import AVFoundation
from AVFoundation import (
    AVCaptureDevice,
    AVMediaTypeAudio,
    AVAudioSession,
    AVAudioSessionCategoryPlayAndRecord,
    AVAudioSessionCategoryOptionAllowBluetooth,
    AVAudioSessionCategoryOptionDefaultToSpeaker,
    AVAudioSessionModeMeasurement,
    AVAudioEngine,
    AVAudioFormat,
)
from PyObjCTools import AppHelper

class AudioTester(Cocoa.NSObject):
    def start(self):
        print("Initializing Audio Session...")
        session = AVAudioSession.sharedInstance()
        try:
            options = AVAudioSessionCategoryOptionAllowBluetooth | AVAudioSessionCategoryOptionDefaultToSpeaker
            session.setCategory_mode_options_error_(
                AVAudioSessionCategoryPlayAndRecord, 
                AVAudioSessionModeMeasurement, 
                options, 
                None
            )
            session.setActive_withOptions_error_(True, 1, None)
            print("AudioSession active.")
        except Exception as e:
            print(f"Session Error: {e}")

        print("Setting up Engine...")
        self.audio_engine = AVAudioEngine.new()
        input_node = self.audio_engine.inputNode()
        fmt = input_node.outputFormatForBus_(0)
        print(f"Input Format: {fmt}")

        input_node.installTapOnBus_bufferSize_format_block_(
            0, 1024, fmt, self.tap_block
        )

        print("Starting Engine...")
        self.audio_engine.prepare()
        res, err = self.audio_engine.startAndReturnError_(None)
        if res:
            print("Engine started. Speak now! (Ctrl+C to stop)")
        else:
            print(f"Engine failed: {err}")

    def tap_block(self, buffer, time):
        print(f"Buffer received! Length: {buffer.frameLength()}")

if __name__ == "__main__":
    tester = AudioTester.alloc().init()
    tester.start()
    
    print("Running console event loop...")
    try:
        # AppHelper handles the runloop correctly for PyObjC
        AppHelper.runConsoleEventLoop()
    except KeyboardInterrupt:
        print("Stopping...")
