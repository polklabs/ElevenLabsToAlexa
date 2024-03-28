from flask import Flask, request, jsonify
import requests
import os
import subprocess
import json
import uuid
import re
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

ELEVENLABS_API_KEY = os.environ.get('ELEVENLABSAPI')
assert ELEVENLABS_API_KEY is not None and ELEVENLABS_API_KEY != '', 'ELEVENLABSAPI is empty or not set'

ALEXA_FOLDER = os.environ.get('ALEXAFOLDER')
assert ALEXA_FOLDER is not None and ALEXA_FOLDER != '', 'ALEXAFOLDER is empty or not set'

assert os.path.exists('./data/ffmpeg'), 'ffmpeg does not exist in data directory'

CHUNK_SIZE = 1024

# Dictionary to store mapping from input text to audio file path
text_to_audio_map = {}

# File path for storing the mapping
mapping_file_path = './data/cache.json'
file_path = './data/audio_files/output.mp3'

# Dictionary to store mapping for voices
voice_map = {}

voice_file_path = './data/voices.json'

# Load the mapping from the JSON file on server startup
if os.path.exists(mapping_file_path):
    with open(mapping_file_path, 'r') as f:
        text_to_audio_map = json.load(f)

if os.path.exists(voice_file_path):
    with open(voice_file_path, 'r') as f:
        voice_map = json.load(f)
else:
    with open('voices.json', 'r') as f:
        voice_map = json.load(f)
    with open(voice_file_path, 'w') as f:
        f.write(json.dumps(voice_map))

# Endpoint to retrieve the audio file path for a given text or synthesize it if not found
@app.route('/synthesize/<voice>', methods=['POST'])
def synthesize_or_get_audio(voice):
    # Get the text from the request
    text = request.json.get('text')
    print(request.json)
    if not text:
        return jsonify({'error': 'Text not provided'}), 400
    
    voice = voice_map[voice]

    # Look for the audio file path in the mapping
    voiceObj = text_to_audio_map.get(voice['id'])
    if voiceObj:
        audio_file_path = voiceObj.get(text)
        if audio_file_path:
            if os.path.exists(audio_file_path):
                return jsonify({'audio_file': os.path.split(audio_file_path)[-1]}), 200
            else:
                del voiceObj[text]

    # If audio file not found, synthesize it
    url = "https://api.elevenlabs.io/v1/text-to-speech/" + voice['id']
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": cleanText(text),
        "model_id": voice['model_id'],
        "voice_settings": {
            "stability": voice['stability'],
            "similarity_boost": voice['similarity_boost']
        }
    }

    print('Fetching audio from ElevenLabs')
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to synthesize audio'}), 500

    # Save the audio file
    with open(file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)

    # Convert the audio file using ffmpeg
    output_file_path =  os.path.join(ALEXA_FOLDER, '{}.mp3'.format(str(uuid.uuid4())))
    try:
        subprocess.run(['chmod', '+x', '/data/ffmpeg'], check=True)
        subprocess.run(['./data/ffmpeg', '-y', '-i', file_path, '-ac', '2', '-codec:a', 'libmp3lame', '-b:a', '48k', '-ar', '24000', '-write_xing', '0', '-filter:a', 'volume=15dB', output_file_path], check=True)
        # subprocess.run(['ffmpeg', '-y', '-i', file_path, '-ac', '2', '-codec:a', 'libmp3lame', '-b:a', '48k', '-ar', '24000', '-write_xing', '0', '-filter:a', 'volume=10dB', output_file_path], check=True)
    except subprocess.CalledProcessError:
        os.remove(file_path)
        return jsonify({'error': 'Failed to convert audio file'}), 500

    # Clean up: delete the original audio file
    os.remove(file_path)

    # Update mapping
    if voice['id'] not in text_to_audio_map:
        text_to_audio_map[voice['id']] = {}
    text_to_audio_map[voice['id']][text] = output_file_path

    # Save the updated mapping to the JSON file
    save_mapping_to_file()

    return jsonify({'audio_file': os.path.split(output_file_path)[-1]}), 200

# Save the mapping to the JSON file
def save_mapping_to_file():
    with open(mapping_file_path, 'w') as f:
        json.dump(text_to_audio_map, f)

def cleanText(text):
    pattern = r'[^a-zA-Z0-9.,!?\'% ]'
    return re.sub(pattern, ' ', text)

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs('./data/audio_files', exist_ok=True)
    app.run(host="0.0.0.0", port=5325)
