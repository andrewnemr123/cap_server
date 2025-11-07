import pyaudio
import numpy as np
import sounddevice # Use sounddevice for querying AND potentially playback
import subprocess
import platform
import sys # For error messages

ACTIVE_TTS = 'nix_tts'  # any of TTS_MODELS
TTS_MODELS = ['styleTTS2','fast_speech','espeak','nix_tts']

class TextToSpeech:
    """
    Handles Text-to-Speech generation and playback.

    Uses PyAudio for playback on non-Pi systems, aplay on Pi.
    Includes fixes for channel, device selection, and sample rate issues.
    """
    def __init__(self, active_tts=ACTIVE_TTS, tts_models=TTS_MODELS):

        if active_tts not in tts_models:
            raise ValueError(f"TTS model '{active_tts}' not found in available models: {', '.join(tts_models)}")

        #print(f"Initializing TTS with model: {active_tts}")
        # Lazy load the tts model
        if active_tts=='nix_tts':
            # Ensure this path is correct relative to where controller.py runs
            from src.llm.tts.nix_tts import NixTTS
            self.model = NixTTS()
        else:
             # Should be caught by the check above, but safeguard
             raise ValueError(f"TTS model '{active_tts}' loading not implemented.")

        # --- Device Handling ---
        self.pyaudio_instance = None # Initialize pyaudio instance variable

        try:
            # Initialize PyAudio only if not on Pi
            self.pyaudio_instance = pyaudio.PyAudio()
            #print("PyAudio initialized for audio output.")
        except Exception as e:
            print(f"Warning: Failed to initialize PyAudio: {e}", file=sys.stderr)
            print("Playback using PyAudio might fail.", file=sys.stderr)
            # Consider falling back to sounddevice playback or raising error

        # --- Store Model Sample Rate ---
        # Ensure the loaded model has a 'sampling_rate' attribute
        if not hasattr(self.model, 'sampling_rate'):
             raise AttributeError(f"Loaded TTS model '{active_tts}' does not have a 'sampling_rate' attribute.")
        self._model_sampling_rate = self.model.sampling_rate
        #print(f"TTS model sample rate: {self._model_sampling_rate} Hz")


    def speak(self, message):
        """Generates speech audio from text and plays it."""
        if not message:
             print("TTS: Received empty message, nothing to speak.")
             return

        #print(f"TTS generating audio for: '{message[:50]}...'")
        try:
            # Generate audio waveform (expecting numpy array)
            wav_predictions = self.model(message)

            if not isinstance(wav_predictions, np.ndarray) or wav_predictions.size == 0:
                 print("TTS Warning: Model did not return valid audio data.", file=sys.stderr)
                 return

            # Ensure data is float32 for PyAudio/sounddevice float format
            if wav_predictions.dtype != np.float32:
                 wav_predictions = wav_predictions.astype(np.float32)

            # Ensure data is within [-1.0, 1.0] for float format
            # Some models might output outside this range
            max_val = np.max(np.abs(wav_predictions))
            if max_val > 1.0:
                print(f"TTS Warning: Audio data amplitude ({max_val:.2f}) exceeds 1.0. Clipping.", file=sys.stderr)
                wav_predictions = np.clip(wav_predictions, -1.0, 1.0)
            elif max_val == 0.0:
                 print("TTS Warning: Generated audio data is all zeros.", file=sys.stderr)
                 return # Don't try to play silence


            #print(f"TTS generated audio: Duration={len(wav_predictions)/self._model_sampling_rate:.2f}s, Shape={wav_predictions.shape}, dtype={wav_predictions.dtype}")

            # --- Play Audio ---
            if self.pyaudio_instance: # Check if PyAudio was initialized
                self.__stream_pyaudio(wav_predictions)
            else:
                 print("Error: PyAudio not available for playback on this system.", file=sys.stderr)

        except Exception as e:
            print(f"Error during TTS generation or playback: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc() # Print full traceback for debugging


    def __stream_pyaudio(self, wav_predictions):
        """Plays audio using PyAudio (for non-Pi systems)."""
        stream = None # Initialize stream variable
        try:
            # --- FIX: Determine Channels (Assume Mono) ---
            # Most TTS generates mono. If stereo is possible, check wav_predictions.ndim
            num_channels = 1
            if wav_predictions.ndim > 1:
                 # If data somehow has more dimensions, check shape
                 # This is unlikely for standard TTS
                 num_channels = wav_predictions.shape[1] if wav_predictions.shape[1] in [1, 2] else 1
                 print(f"TTS Warning: Audio data appears to have {wav_predictions.ndim} dimensions. Assuming {num_channels} channels.", file=sys.stderr)
                 if num_channels > 1:
                      # Need to ensure data is interleaved correctly for PyAudio if stereo
                      # wav_predictions = wav_predictions.flatten().astype(np.float32) # Example, might need adjustment
                      pass # Add handling if stereo TTS is actually used

            output_device_index = None # Use default if None
            try:
                 # PyAudio's way to get default output device info
                 default_device_info = self.pyaudio_instance.get_default_output_device_info()
                 output_device_index = default_device_info['index']
                 #print(f"Using default PyAudio output device: #{output_device_index} - {default_device_info['name']}")
            except Exception as e:
                 print(f"Warning: Could not get default PyAudio output device: {e}. Using system default.", file=sys.stderr)
                 # output_device_index remains None, PyAudio will use default

            output_rate = self._model_sampling_rate

            #print(f"Opening PyAudio stream: Rate={output_rate}, Channels={num_channels}, Device={output_device_index or 'Default'}")

            stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32, # Data is already float32
                channels=num_channels,    # Use determined number of channels (usually 1)
                rate=output_rate,         # Use the model's actual sample rate
                output=True,
                output_device_index=output_device_index # Use default or specific index
            )

            audio_bytes = wav_predictions.tobytes()
            #print(f"Writing {len(audio_bytes)} bytes to audio stream...")
            stream.write(audio_bytes)
            #print("Finished writing to stream.")

        except OSError as e:
             # Catch OS errors like "Invalid number of channels" specifically
             print(f"\nError: PyAudio OSError during stream open/write: {e}", file=sys.stderr)
             if "Invalid number of channels" in str(e):
                  print("This often means the requested number of channels ({num_channels}) is not supported by the output device.", file=sys.stderr)
                  print("Most TTS is mono (1 channel). Check if the device supports mono.", file=sys.stderr)
             elif "Invalid sample rate" in str(e):
                   print(f"The requested sample rate ({output_rate}Hz) may not be supported by the output device.", file=sys.stderr)
             print("Troubleshooting: Check default audio output device in system settings.", file=sys.stderr)

        except Exception as e:
            print(f"Error during PyAudio playback: {e}", file=sys.stderr)
        finally:
            # Ensure stream is closed
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                    #print("PyAudio stream stopped and closed.")
                except Exception as close_err:
                     print(f"Error closing PyAudio stream: {close_err}", file=sys.stderr)

    def __del__(self):
        # Ensure PyAudio is terminated when the object is deleted
        if  hasattr(self, 'pyaudio_instance') and self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
                print("PyAudio terminated.")
            except Exception as e:
                 print(f"Error terminating PyAudio: {e}", file=sys.stderr)

