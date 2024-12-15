from flask import Blueprint, request, jsonify
import openai
import os
from dotenv import load_dotenv
from ..services.search_service import SearchService
from ..services.image_service import ImageService
from google.cloud import texttospeech
import base64

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

chat_bp = Blueprint('chat', __name__)
try:
    search_service = SearchService()
    image_service = ImageService()
    tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    print(f"Warning: Service initialization failed: {str(e)}")
    search_service = None
    image_service = None
    tts_client = None

def is_course_related(question, context):
    """
    Determine if a question is course-related based on context and keywords.
    """
    # List of non-course keywords
    general_keywords = [
        'weather', 'time', 'hello', 'hi', 'hey', 
        'how are you', 'what\'s up', 'good morning',
        'good afternoon', 'good evening', 'thanks',
        'thank you', 'bye', 'goodbye', 'who are you'
    ]
    
    question_lower = question.lower()
    
    # If question contains general keywords, it's not course-related
    if any(keyword in question_lower for keyword in general_keywords):
        return False
    
    # If meaningful context was found, it's course-related
    if context and len(context.strip()) > 0:
        meaningful_context = len(context.split()) > 10
        return meaningful_context
    
    # List of course-specific keywords
    course_keywords = [
        'ptrs', 'muscle', 'neural', 'plasticity', 'motor unit', 
        'metabolism', 'epigenetics', 'rehabilitation', 'spinal cord',
        'biomechanics', 'motor control', 'hill equation', 'exercise',
        'physical therapy', 'movement', 'strength training',
        'fitness', 'anatomy', 'physiology', 'health', 'medical',
        'patient', 'treatment', 'therapy', 'clinical', 'research',
        'lecture', 'course', 'exam', 'assignment', 'study'
    ]
    
    return any(keyword in question_lower for keyword in course_keywords)

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
        audio_requested = data.get('audio_requested', False)
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
        
        # Check if question is course-related
        is_course_question = is_course_related(user_message, context)
        print(f"Is course-related question: {is_course_question}")
        
        # Create system message
        system_message = (
            "You are a knowledgeable teaching assistant for the PTRS:6224 course. "
        )
        if context and is_course_question:
            system_message += f"\nUse this course material to answer: {context}"
        elif is_course_question:
            system_message += "\nAnswer based on general knowledge about this topic in physical therapy and rehabilitation science."
        else:
            system_message = "You are a helpful assistant. Provide a general response as this question is not related to the course material."
        
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
        
        # Generate audio if requested
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
        
        # Only include sources and context if it's a course-related question
        return jsonify({
            "message": message_content,
            "sources": sources[0] if (sources and is_course_question) else None,
            "used_context": bool(context) and is_course_question,
            "context_preview": context[:200] if (context and is_course_question) else None,
            "is_course_related": is_course_question,
            "audio": audio_base64
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        image_base64 = image_service.generate_image(prompt)
        
        # Add descriptive information
        description = f"Generated anatomical illustration showing {prompt}. "
        description += "This medical-style diagram includes detailed labeling and precise anatomical structures. "
        description += "You can use this illustration for studying or reference purposes."
        
        if image_base64:
            return jsonify({
                "image": image_base64,
                "description": description,
                "success": True
            })
        else:
            return jsonify({
                "error": "Failed to generate image",
                "success": False
            }), 500
            
    except Exception as e:
        print(f"Error in generate_image endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500