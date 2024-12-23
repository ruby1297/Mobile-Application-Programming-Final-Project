import os
import whisper
UPLOAD_FOLDER = "static"
whisper_model = whisper.load_model("base")
# 將音訊檔(static/audio.wav)轉換成文字(static/transcribed_text.txt)
def transcribe_audio(audio_file_path):
    try:
        # Check if the audio file exists
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Load the audio file
        audio = whisper.load_audio(audio_file_path)
        
        # Transcribe the audio file
        result = whisper_model.transcribe(audio, fp16=False)  # Use whisper_model here
    except Exception as e:
        print(f"Error transcribing audio file: {e}")
        return "NO TRANSCRIPTION"
    return result['text']

if __name__ == "__main__":
    # Test the audio transcription
    audio_file_path = 'static/audio.wav'
    transcribed_text = transcribe_audio(audio_file_path)
    print(f"Transcribed Text: {transcribed_text}")
    # 將轉換後的文本保存到 static 文件夾中
    text_file_path = os.path.join(UPLOAD_FOLDER, "transcribed_text.txt")
    with open(text_file_path, "w", encoding="utf-8") as text_file:
        text_file.write(transcribed_text)
    print("Transcribed text saved to: ", text_file_path)
