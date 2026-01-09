
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def test_call():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    system_prompt = "You are a helpful assistant."
    user_prompt = "Hello, tell me a joke."
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=100,
                temperature=0.1,
            ),
        )
        print(f"Success: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_call()
