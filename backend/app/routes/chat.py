from flask import Blueprint, request, jsonify
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
        
    try:
        data = request.get_json()
        user_message = data.get('message')
        
        # Simple test response for now
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful teaching assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        
        return jsonify({
            "message": response.choices[0].message.content,
            "sources": {}
        })
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500