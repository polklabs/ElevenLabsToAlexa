from flask import Flask, request, jsonify
import requests
import os
import subprocess
import json

app = Flask(__name__)

# Dictionary to store mapping from input text to audio file path
text_to_audio_map = {}

# File path for storing the mapping
mapping_file_path = 'cache.json'

# Load the mapping from the JSON file on server startup
if os.path.exists(mapping_file_path):
    with open(mapping_file_path, 'r') as f:
        text_to_audio_map = json.load(f)

# Endpoint to retrieve the audio file path for a given text or synthesize it if not found
@app.route('/synthesize', methods=['POST'])
def synthesize_or_get_audio():
    # Get the text from the request
    text = request.json.get('text')
    if not text:
        return jsonify({'error': 'Text not provided'}), 400

    # Look for the audio file path in the mapping
    audio_file_path = text_to_audio_map.get(text)
    if audio_file_path:
        return jsonify({'audio_file': audio_file_path}), 200

    # If audio file not found, synthesize it
    response = requests.post('https://api.eleven-labs.com/api/speech/v1/generate', json={'text': text})
    if response.status_code != 200:
        return jsonify({'error': 'Failed to synthesize audio'}), 500

    # Save the audio file
    file_path = 'audio_files/{}.wav'.format(text_to_filename(text))
    with open(file_path, 'wb') as file:
        file.write(response.content)

    # Convert the audio file using ffmpeg
    output_file_path = 'converted_audio/{}.mp3'.format(text_to_filename(text))
    subprocess.run(['ffmpeg', '-i', file_path, output_file_path])

    # Clean up: delete the original audio file
    os.remove(file_path)

    # Update mapping
    text_to_audio_map[text] = output_file_path

    # Save the updated mapping to the JSON file
    save_mapping_to_file()

    return jsonify({'audio_file': output_file_path}), 200

# Utility function to convert text to a valid filename
def text_to_filename(text):
    return text.replace(' ', '_').lower()

# Save the mapping to the JSON file
def save_mapping_to_file():
    with open(mapping_file_path, 'w') as f:
        json.dump(text_to_audio_map, f)

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs('audio_files', exist_ok=True)
    os.makedirs('converted_audio', exist_ok=True)
    app.run(debug=True)
