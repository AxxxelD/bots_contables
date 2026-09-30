import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

prompt = "Transcribe el texto que ves en la imagen, sobre todo la parte del mensaje del bot de telegram."
img_path = r'C:\Users\Axel Dávila\.gemini\antigravity-ide\brain\99abf365-70c3-4fce-a029-20e9a23141fb\.user_uploaded\media_1790714296139.png'
with open(img_path, 'rb') as f:
    img_bytes = f.read()

contents = [
    prompt,
    types.Part.from_bytes(data=img_bytes, mime_type='image/png')
]

response = client.models.generate_content(
    model='gemini-3.5-flash',
    contents=contents
)
print('Gemini Extracted:', response.text)
