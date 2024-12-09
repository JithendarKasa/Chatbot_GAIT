from google.cloud import texttospeech
import os
import base64

class TTSService:
    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()
        
    def generate_audio(self, text):
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Convert audio content to base64 for sending to frontend
            audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
            return audio_base64
            
        except Exception as e:
            print(f"Error generating audio: {str(e)}")
            return None