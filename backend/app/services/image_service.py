import os
import requests
from dotenv import load_dotenv
import base64
import json

load_dotenv()

class ImageService:
    def __init__(self):
        self.api_key = os.getenv('STABILITY_API_KEY')
        if not self.api_key:
            print("Warning: STABILITY_API_KEY not found in environment variables")
        self.api_host = 'https://api.stability.ai'

    def generate_image(self, prompt):
        try:
            print(f"Attempting to generate image with prompt: {prompt}")
            print(f"Using API key: {self.api_key[:6]}...")  # Print first 6 chars for verification

            response = requests.post(
                f"{self.api_host}/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "text_prompts": [
                        {
                            "text": prompt,
                            "weight": 1
                        }
                    ],
                    "cfg_scale": 7,
                    "steps": 30,
                    "width": 1024,
                    "height": 1024,
                }
            )

            print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                raise Exception(f"API returned status code {response.status_code}: {response.text}")

            data = response.json()
            print("Successfully received response from Stability API")
            
            if "artifacts" in data and len(data["artifacts"]) > 0:
                print("Image generated successfully")
                return data["artifacts"][0]["base64"]
            else:
                print("No artifacts found in response")
                print(f"Response data: {json.dumps(data, indent=2)}")
                return None

        except Exception as e:
            print(f"Detailed error in generate_image: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None