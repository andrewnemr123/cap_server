import numpy as np
import time
import sys
import sounddevice as sd
import webrtcvad
import queue

RECORD_LENGTH = 3  # Max recording duration in seconds
SILENCE_LENGTH = 3  # Seconds of silence to stop recording
VAD_MODE = 3        # VAD aggressiveness (0-3, 3=most aggressive)
SAMPLE_RATE = 16000 # Audio sample rate

# --- VAD Parameters (for webrtcvad on Windows) ---
VAD_FRAME_MS = 30 # Use 30ms frames for VAD processing (must be 10, 20, or 30)
VAD_FRAME_SAMPLES = int(SAMPLE_RATE * (VAD_FRAME_MS / 1000.0))


# --- Main Recording Function ---
def record_until_thresh():
    audio_queue = queue.Queue()

    def audio_callback(indata, frames, time, status):
        if status: print(f"Sounddevice status: {status}", file=sys.stderr)
        audio_queue.put(indata.copy())

    try:
        vad = webrtcvad.Vad(VAD_MODE)
    except NameError:
         print("Error: webrtcvad library not available.", file=sys.stderr); return np.array([], dtype=np.float32)
    except Exception as e:
         print(f"Error initializing VAD: {e}", file=sys.stderr); return np.array([], dtype=np.float32)

    recorded_blocks = []
    triggered = False
    frames_since_last_speech = 0
    total_recorded_duration_s = 0.0
    silence_frames_needed = SILENCE_LENGTH * SAMPLE_RATE
    block_duration_s = VAD_FRAME_SAMPLES / SAMPLE_RATE
    stream = None
    selected_device_index = -1
    selected_device_name = "Default"

    try:
        try:
            default_input_device_info = sd.query_devices(kind='input')
            if default_input_device_info and isinstance(default_input_device_info, dict):
                 idx = default_input_device_info.get('index')
                 if idx is not None:
                     selected_device_index = idx
                     selected_device_name = default_input_device_info.get('name', f'Device {idx}')
                     
                     #print(f"Using default input device: #{selected_device_index} - {selected_device_name}")
                     print("🎤 Capturing command...")
                 else:
                      print("Warning: Could not get index from default input device info. Using default index -1.", file=sys.stderr)
            else:
                 print("Warning: Could not query default input device info. Using default index -1.", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error querying default input device: {e}. Using default index -1.", file=sys.stderr)

        stream = sd.InputStream(
            device=selected_device_index, samplerate=SAMPLE_RATE, channels=1,
            dtype='float32', blocksize=VAD_FRAME_SAMPLES, callback=audio_callback
        )
        stream.start()

        while total_recorded_duration_s < RECORD_LENGTH:
            try:
                frame_data_float32 = audio_queue.get(timeout=SILENCE_LENGTH + 1)
                frame_count = frame_data_float32.shape[0]
                total_recorded_duration_s += block_duration_s

                if frame_count != VAD_FRAME_SAMPLES:
                     print(f"Warning: Received frame size {frame_count} != expected {VAD_FRAME_SAMPLES}. Skipping VAD.", file=sys.stderr)
                     if triggered: recorded_blocks.append(frame_data_float32)
                     continue

                frame_data_float32 = np.clip(frame_data_float32, -1.0, 1.0)
                frame_data_int16 = (frame_data_float32 * 32767).astype(np.int16)
                frame_bytes = frame_data_int16.tobytes()

                try:
                    is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)
                except Exception as vad_error:
                     print(f"Warning: VAD error: {vad_error}. Treating as silence.", file=sys.stderr); is_speech = False

                if is_speech:
                    if not triggered: 
                        triggered = True
                    recorded_blocks.append(frame_data_float32); frames_since_last_speech = 0
                elif triggered:
                    recorded_blocks.append(frame_data_float32); frames_since_last_speech += frame_count
                    if frames_since_last_speech >= silence_frames_needed:
                        break

            except queue.Empty:
                if triggered: print(f"\nTimeout waiting for audio. Assuming silence, stopping."); break
                if total_recorded_duration_s >= RECORD_LENGTH: print("\nMax duration reached while waiting."); break
                continue

        if total_recorded_duration_s >= RECORD_LENGTH: print("\nMax recording duration reached.")

    except sd.PortAudioError as pa_error:
        print(f"\nError: Sounddevice/PortAudio error: {pa_error}", file=sys.stderr)
        _print_audio_devices()
        print("Troubleshooting Tips:", file=sys.stderr)
        print("1. Check Mic Connection & Windows Sound Settings (Input Device enabled & Default).", file=sys.stderr)
        print("2. Check Windows Microphone Privacy Settings (Allow desktop apps).", file=sys.stderr)
        print("3. Update Audio Drivers.", file=sys.stderr)
        print("4. Close other apps using the mic.", file=sys.stderr)
        print("5. Restart computer.", file=sys.stderr)
        return np.array([], dtype=np.float32)
    except Exception as e:
        print(f"\nAn unexpected error occurred during Windows recording: {e}", file=sys.stderr)
        return np.array([], dtype=np.float32)
    finally:
        if stream is not None:
             try:
                 if stream.active: stream.stop()
                 stream.close(); 
                 #print("Audio stream stopped and closed.")
             except Exception as close_err: print(f"Error stopping/closing stream: {close_err}", file=sys.stderr)

    #print("Processing recorded blocks...")
    if not recorded_blocks:
        #print("Warning: No audio blocks were recorded (or kept).")
        return np.array([], dtype=np.float32)

    try:
        full_audio_2d = np.concatenate(recorded_blocks, axis=0)
        full_audio_1d = np.squeeze(full_audio_2d)
        final_duration = len(full_audio_1d) / SAMPLE_RATE
        #print(f"Successfully recorded {final_duration:.2f} seconds of audio. Final shape: {full_audio_1d.shape}")
        return full_audio_1d
    except ValueError as e:
         print(f"Error: Could not concatenate recorded blocks: {e}", file=sys.stderr)
         return np.array([], dtype=np.float32)
    except Exception as e:
        print(f"Error processing/squeezing audio blocks: {e}", file=sys.stderr)
        return np.array([], dtype=np.float32)