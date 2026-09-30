import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

prompt = "Transcribe todo el texto de esta imagen. Si hay un chat, escribe lo que dice el bot."
img_path = r'C:\Users\Axel Dávila\.gemini\antigravity-ide\brain\99abf365-70c3-4fce-a029-20e9a23141fb\.user_uploaded\media_1790713524082.png'
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
with open('gemini_output.txt', 'w', encoding='utf-8') as f:
    f.write(response.text)
print('Done!')
