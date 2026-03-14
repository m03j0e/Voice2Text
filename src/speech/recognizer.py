import Cocoa
import AVFoundation
from AVFoundation import (
    AVAudioFormat,
    AVAudioPCMBuffer,
)
import Speech
from Speech import (
    SFSpeechRecognizer,
    SFSpeechAudioBufferRecognitionRequest,
    SFSpeechRecognitionTask,
)
from src.utils.logger import logger

class Recognizer:
    def __init__(self, samplerate=16000, result_callback=None):
        self.recognizer = SFSpeechRecognizer.new()
        self.samplerate = samplerate
        self.result_callback = result_callback
        self.request = None
        self.recognition_task = None

        self.audio_format = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(
            self.samplerate, 1
        )

    def start(self):
        logger.debug("Initializing SFSpeechRecognizer...")
        self.request = SFSpeechAudioBufferRecognitionRequest.new()
        
        # Enable Apple's on-device ML/Apple Intelligence punctuation
        if hasattr(self.request, "setAddsPunctuation_"):
            self.request.setAddsPunctuation_(True)
            
        self.recognition_task = self.recognizer.recognitionTaskWithRequest_resultHandler_(
            self.request,
            self.recognition_result_handler
        )
        logger.debug("Recognition task started")

    def stop(self):
        if self.request:
            self.request.endAudio()
            self.request = None
        if self.recognition_task:
            self.recognition_task.cancel()
            self.recognition_task = None

    def process_audio(self, numpy_data):
        if not self.request:
            return

        frame_count = len(numpy_data)
        buffer = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(self.audio_format, frame_count)
        buffer.setFrameLength_(frame_count)

        channels = buffer.floatChannelData()
        ptr = channels[0]

        flat_data = numpy_data.flatten()

        for i in range(frame_count):
            ptr[i] = flat_data[i]

        self.request.appendAudioPCMBuffer_(buffer)

    def recognition_result_handler(self, result, error):
        if error:
            if error.domain() == "kAFAssistantErrorDomain" and error.code() == 1110:
                pass
            else:
                logger.error(f"Recognition error: {error}")

        if result:
            transcription = result.bestTranscription().formattedString()
            is_final = result.isFinal()
            if self.result_callback:
                self.result_callback(transcription, is_final)
