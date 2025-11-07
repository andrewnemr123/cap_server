import os
import time
from scipy.io.wavfile import write
import numpy as np

from src.llm.stt.record import record_until_thresh
from faster_whisper import WhisperModel

CACHE_RECORDINGS = False
RECORDINGS_DIR = "data/recordings"
SAMPLE_RATE = '16000'
DEVICE = 'cpu'
WHISPER_SIZE = 'tiny'

class FasterWhisper:
    """Faster version of the whisper class below, also uses int8
    precision. Takes raw audio data at a sampling rate of
    16000.
    """
    def __init__(self):
        device_type = "cuda" if "cuda" in DEVICE else "cpu"
        self.whisper = WhisperModel(WHISPER_SIZE, device=device_type, compute_type="int8") # Use device_type

    def transcribe(self, data: np.ndarray):
        # Ensure data is float32, as expected by many Whisper implementations
        if data.dtype != np.float32:
            data = data.astype(np.float32) / 32768.0 # Normalize if needed (check recorder output)

        segments,_ = self.whisper.transcribe(data, beam_size=5, language="en")
        return ''.join([segment.text for segment in segments]).strip()

    def listen_transcribe(self):
        """This listens to audio until silence, then transcribes audio to text
        using FasterWhisper.
        """

        if CACHE_RECORDINGS:
            # Ensure the recordings directory exists
            _create_subfolders_for_file(RECORDINGS_DIR + "/") # Ensure base dir exists
            filename = os.path.join(RECORDINGS_DIR, f"morbius_recording_{int(time.time())}.wav")
            #print(f"Recording will be cached to: {filename}")

        
        try:
            # Record audio until silence is detected
            data = record_until_thresh()
            #print(f"Recording complete. Audio data shape: {data.shape}, dtype: {data.dtype}")
        except Exception as e:
            # Provide more specific error feedback if possible
            print(f"Failed to record audio: {e}")
            print("Check audio input device and recording library setup.")
            return "" # Return empty string on recording failure

        print("Starting transcription...")
        try:
            # Pass the recorded data to the transcribe method of the provided instance
            results = self.transcribe(data)
            print(f"Transcription complete. Result: '{results}'")
        except Exception as e:
            print(f"Failed to transcribe audio: {e}")
            results = "" # Return empty string on transcription failure

        # Save the recording if caching is enabled and data exists
        if CACHE_RECORDINGS and data.size > 0:
            try:
                # Ensure data is int16 for WAV writing
                if data.dtype == np.float32:
                    # Scale float32 data in range [-1, 1] to int16
                    scaled = np.int16(data * 32767)
                elif data.dtype == np.int16:
                    scaled = data # Already int16
                else:
                    print(f"Warning: Unsupported dtype for saving WAV: {data.dtype}. Skipping save.")
                    scaled = None

                if scaled is not None:
                    # Check directory again just before writing
                    _create_subfolders_for_file(filename)
                    write(filename, SAMPLE_RATE, scaled)
                    print(f"Recording saved to {filename}")

            except Exception as e:
                print(f"Failed to save recording to {filename}: {e}")
        return results

def _create_subfolders_for_file(file_path):
    directory = os.path.dirname(file_path)

    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directories created for {directory}")
    else:
        print(f"Directory {directory} already exists")