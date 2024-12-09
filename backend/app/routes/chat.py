from flask import Blueprint, request, jsonify
import openai
import os
from dotenv import load_dotenv
from ..services.search_service import SearchService  # Changed from rag_service

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

chat_bp = Blueprint('chat', __name__)
try:
    search_service = SearchService()  # Changed from rag_service
except Exception as e:
    print(f"Warning: Search service initialization failed: {str(e)}")
    search_service = None

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message')
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
        
        return jsonify({
            "message": response.choices[0].message.content,
            "sources": sources[0] if sources else None,
            "used_context": bool(context),
            "context_preview": context[:200] if context else None
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500