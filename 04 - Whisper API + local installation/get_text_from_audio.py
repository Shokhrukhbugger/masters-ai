from pydub import AudioSegment

# Load the MP3 file (replace 'your_audio.mp3' with the actual file name)
audio = AudioSegment.from_file("recording.mp3")


# Define the start and end time for the segment (in milliseconds)
# For example, cut a 2-minute segment starting at the 5-minute mark

def minutes_to_milliseconds(minutes: int):
    return minutes * 60 * 1000


start_time = minutes_to_milliseconds(5)  # 5 minutes in milliseconds
end_time = start_time + minutes_to_milliseconds(2)  # Add 2 minutes in milliseconds

# Extract the segment
segment = audio[start_time:end_time]

audio_save_path = "output_segment.mp3"

# Save the extracted segment to a new file
segment.export(audio_save_path, format="mp3")

print("2-minute segment saved as 'output_segment.mp3'")

import whisper

# Load the Whisper model
model = whisper.load_model("base")  # Use "base", "small", "medium", or "large" for different accuracies

# Transcribe the audio file
transcript = model.transcribe(audio_save_path)

# Save the transcribed text to a new file
with open("transcript.txt", "w") as file:
    file.write(transcript["text"])