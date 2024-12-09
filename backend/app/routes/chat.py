from flask import Blueprint, request, jsonify
import openai
import os
from dotenv import load_dotenv
from ..services.search_service import SearchService
from google.cloud import texttospeech
import base64

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

chat_bp = Blueprint('chat', __name__)
try:
    search_service = SearchService()
    tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    print(f"Warning: Service initialization failed: {str(e)}")
    search_service = None
    tts_client = None

def generate_audio(text):
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Convert audio content to base64
        audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
        return audio_base64
        
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return None

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message')
        audio_requested = data.get('audio_requested', False)  # New parameter
        print(f"\nReceived question: {user_message}")
        
        context = ""
        sources = []
        if search_service:
            try:
                print("Searching for relevant content...")
                search_result = search_service.get_context(user_message)
                context = search_result['context']
                sources = search_result['sources']
                print(f"Found context: {bool(context)}")
                if sources:
                    print(f"Source: {sources[0]['filename']}")
            except Exception as e:
                print(f"Search service error: {str(e)}")
        else:
            print("Search service not initialized!")
        
        # Create system message
        system_message = (
            "You are a knowledgeable teaching assistant for the PTRS:6224 course. "
        )
        if context:
            system_message += f"\nUse this course material to answer: {context}"
        else:
            system_message += "\nProvide general guidance if no specific course material is available."
        
        # Get response from OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        message_content = response.choices[0].message.content
        
        # Generate audio if requested and TTS client is available
        audio_base64 = None
        if audio_requested and tts_client:
            try:
                print("Generating audio response...")
                audio_base64 = generate_audio(message_content)
                if audio_base64:
                    print("Audio generated successfully")
                else:
                    print("Failed to generate audio")
            except Exception as e:
                print(f"Error generating audio: {str(e)}")
        
        return jsonify({
            "message": message_content,
            "sources": sources[0] if sources else None,
            "used_context": bool(context),
            "context_preview": context[:200] if context else None,
            "audio": audio_base64
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500