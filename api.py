from flask import Flask, request, jsonify
import requests
import os
import subprocess
import json
import uuid
from dotenv import load_dotenv
import shutil

app = Flask(__name__)

load_dotenv()

ELEVENLABS_API_KEY = os.environ.get('ELEVENLABSAPI')
assert ELEVENLABS_API_KEY is not None and ELEVENLABS_API_KEY != '', 'ELEVENLABSAPI is empty or not set'

ALEXA_FOLDER = os.environ.get('ALEXAFOLDER')
assert ALEXA_FOLDER is not None and ALEXA_FOLDER != '', 'ALEXAFOLDER is empty or not set'

CHUNK_SIZE = 1024

# Dictionary to store mapping from input text to audio file path
text_to_audio_map = {}

# File path for storing the mapping
mapping_file_path = 'cache.json'
file_path = 'audio_files/output.mp3'

# Load the mapping from the JSON file on server startup
if os.path.exists(mapping_file_path):
    with open(mapping_file_path, 'r') as f:
        text_to_audio_map = json.load(f)

# Endpoint to retrieve the audio file path for a given text or synthesize it if not found
@app.route('/synthesize', methods=['POST'])
def synthesize_or_get_audio():
    # Get the text from the request
    text = request.json.get('text')
    print(request.json)
    if not text:
        return jsonify({'error': 'Text not provided'}), 400

    # Look for the audio file path in the mapping
    audio_file_path = text_to_audio_map.get(text)
    if audio_file_path:
        if os.path.exists(audio_file_path):
            return jsonify({'audio_file': os.path.split(audio_file_path)[-1]}), 200

    # If audio file not found, synthesize it
    # Charlotte XB0fDUnXU5powFXDhCwa
    # Rachael 21m00Tcm4TlvDq8ikWAM
    url = "https://api.elevenlabs.io/v1/text-to-speech/XB0fDUnXU5powFXDhCwa"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
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
        subprocess.run(['ffmpeg', '-y', '-i', file_path, '-ac', '2', '-codec:a', 'libmp3lame', '-b:a', '48k', '-ar', '24000', '-write_xing', '0', '-filter:a', 'volume=10dB', output_file_path], check=True)
    except subprocess.CalledProcessError:
        os.remove(file_path)
        return jsonify({'error': 'Failed to convert audio file'}), 500

    # Clean up: delete the original audio file
    os.remove(file_path)

    # Update mapping
    text_to_audio_map[text] = output_file_path

    # Save the updated mapping to the JSON file
    save_mapping_to_file()

    return jsonify({'audio_file': os.path.split(output_file_path)[-1]}), 200

# Save the mapping to the JSON file
def save_mapping_to_file():
    with open(mapping_file_path, 'w') as f:
        json.dump(text_to_audio_map, f)

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs('audio_files', exist_ok=True)
    os.makedirs('converted_audio', exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=6969)
