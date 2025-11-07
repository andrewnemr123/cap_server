import tempfile
import os
import speech_recognition as sr
import openai

openai.api_key = ""

# Function to capture audio and convert to text
def capture_voice():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for your command...")
        try:
            # Listen for audio input
            audio = recognizer.listen(source, timeout=20)
            print("Processing your voice input...")

            # Save the audio to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                temp_audio_file.write(audio.get_wav_data())
                temp_audio_file_name = temp_audio_file.name

            # Use OpenAI Whisper API for speech-to-text
            with open(temp_audio_file_name, "rb") as audio_file:
                response = openai.Audio.transcribe("whisper-1", audio_file)
            
            # Clean up the temporary file
            os.remove(temp_audio_file_name)
            
            return response["text"]

        except sr.WaitTimeoutError:
            print("Listening timeout, please try again.")
        except Exception as e:
            print(f"Error capturing voice: {e}")
        return None



def interpretSeriesOfCommands(order: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """You are an assistant that converts natural
              language instructions into a JSON array of robot commands."""
              "Each command must be in the format: {\"command\": \"move/turn\", \"float_data\": [value]}."},

            {"role": "user", "content": f"""Execute the order: '{order}'.
              Use 'move' or 'turn' to describe actions, or an empty array if the entire prompt is not related to movement or turning.
              Output a JSON array of 'move' and 'turn' commands if multiple actions need to be taken.
              Indicate the angle as float_data for a turn instruction.
              Indicate the distance in meters as float_data for a move instruction"""}
        ],
        max_tokens=100,
        temperature=0
    )
    return response['choices'][0]['message']['content'].strip()

print(interpretSeriesOfCommands("Go to the room directly on the left, grab my thylenol, then come out and go to the third room on the right to give it to me"))
# Expected: "[turn -90, move 1, turn 180, move 1, turn 90, move 3]" 
print(interpretSeriesOfCommands("Turn left now! Then grab the insulin in the room in front of you and come back to me."))
# Expected: "[turn 90]"       
print(interpretSeriesOfCommands("What's your name?"))
# Expected: "null"    

if __name__ == "__main__":
    # Take the message from standard input
    interpreted_message = interpretSeriesOfCommands(capture_voice())
    print(interpreted_message)
