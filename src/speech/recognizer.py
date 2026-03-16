Cocoa = None
try:
    import Cocoa
except ImportError:
    pass

from src.utils.logger import logger

class Recognizer:
    def __init__(self, samplerate=16000, result_callback=None):
        try:
            import Cocoa
            import AVFoundation
            from AVFoundation import AVAudioFormat, AVAudioPCMBuffer
            import Speech
            from Speech import SFSpeechRecognizer, SFSpeechAudioBufferRecognitionRequest, SFSpeechRecognitionTask
            self.SFSpeechRecognizer = SFSpeechRecognizer
            self.AVAudioFormat = AVAudioFormat
            self.AVAudioPCMBuffer = AVAudioPCMBuffer
            self.SFSpeechAudioBufferRecognitionRequest = SFSpeechAudioBufferRecognitionRequest
            self.SFSpeechRecognitionTask = SFSpeechRecognitionTask
            self.has_speech = True
        except ImportError:
            self.has_speech = False

        if not self.has_speech:
            self.recognizer = None
            self.samplerate = samplerate
            self.result_callback = result_callback
            self.request = None
            self.recognition_task = None
            self.audio_format = None
            return

        self.recognizer = self.SFSpeechRecognizer.new()
        self.samplerate = samplerate
        self.result_callback = result_callback
        self.request = None
        self.recognition_task = None

        self.audio_format = self.AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(
            self.samplerate, 1
        )

    def start(self):
        if not hasattr(self, 'has_speech') or not self.has_speech:
            return
        logger.info("Initializing SFSpeechRecognizer...")
        self.request = self.SFSpeechAudioBufferRecognitionRequest.new()
        
        # Enable Apple's on-device ML/Apple Intelligence punctuation
        if hasattr(self.request, "setAddsPunctuation_"):
            self.request.setAddsPunctuation_(True)
            
        logger.debug("Creating recognition task...")
        self.recognition_task = self.recognizer.recognitionTaskWithRequest_resultHandler_(
            self.request,
            self.recognition_result_handler
        )
        logger.info("Recognition task started.")

    def stop(self):
        if self.request:
            self.request.endAudio()
            self.request = None
        # Do not immediately cancel the task, allow the final result handler to finish
        # The task will eventually complete on its own after endAudio()
        self.recognition_task = None

    def process_audio(self, numpy_data):
        if not self.request or not hasattr(self, 'AVAudioPCMBuffer'):
            return

        frame_count = len(numpy_data)
        buffer = self.AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(self.audio_format, frame_count)
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
