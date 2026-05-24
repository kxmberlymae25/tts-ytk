import pyttsx3
from flask import Flask, request, jsonify, send_file, render_template_string
import gtts
import os
from datetime import datetime, timedelta
import librosa
import soundfile as sf
import traceback
import threading
import time

app = Flask(__name__)

# Directory to store the generated audio files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to change male or female voice and vice versa
def gender_change(text, gender='male', filename='output.mp3'):
    try:
        # Initialize the pyttsx3 engine
        engine = pyttsx3.init()

        # Retrieve available voices
        voices = engine.getProperty('voices')

        # Choose the voice based on gender
        if gender == 'female':
            # Select a female voice (usually the second voice in the list)
            engine.setProperty('voice', voices[1].id)
        else:
            # Select a male voice (usually the first voice in the list)
            engine.setProperty('voice', voices[0].id)

        # Set speech rate (optional)
        engine.setProperty('rate', 150)  # Adjust the rate as needed

        # Save the generated speech to an MP3 file
        engine.save_to_file(text, filename)

        # Run the engine to process the speech
        engine.runAndWait()

        print(f"Generated {gender} voice and saved as {filename}")
    except Exception as e:
        print(f"Error generating voice: {e}")
        traceback.print_exc()
        raise


# Helper function to pitch shift audio
def pitch_shift(input_path, output_path, n_steps):
    try:
        print(f"Loading audio file from: {input_path}")
        # Load the audio file (Librosa handles WAV perfectly out-of-the-box)
        y, sr = librosa.load(input_path, sr=None)
        print(f"Audio loaded. Sample rate: {sr}, Length: {len(y)}")

        # Apply pitch shifting
        y_shifted = librosa.effects.pitch_shift(y=y, sr=sr, n_steps=n_steps)
        print(f"Pitch shifting applied with {n_steps} semitones.")

        # Save the pitch-shifted audio to a standard WAV file format
        sf.write(output_path, y_shifted, sr)
        print(f"Pitch-shifted audio saved to: {output_path}")
    except Exception as e:
        print(f"Error during pitch shifting: {e}")
        traceback.print_exc()
        raise

# Route to generate audio from text
@app.route('/generate', methods=['POST'])
def generate():
    # Get text, language, and pitch from the request
    data = request.json
    text = data.get('text')
    lang = data.get('lang', 'en')  # Default to 'en' if no language is provided
    pitch = data.get('pitch', 0)  # Pitch shift in semitones
    gender = data.get('gender', 0)  # gender

    # Validate text length
    if not text:
        return jsonify({'error': 'No text provided, Please Enter Some Text to Generate Audio'}), 400
    if len(text) > 5000:
        return jsonify({'error': 'Text exceeds 5000 character limit'}), 400

    # Validate language code
    if lang not in gtts.lang.tts_langs():
        return jsonify({'error': 'Unsupported language'}), 400

    # Generate filename based on the current timestamp
    currentDateAndTime = datetime.now()
    formattedDateTime = currentDateAndTime.strftime("%Y%m%d_%H%M%S")
    
    # CRITICAL FIX: If shifting pitch, use .wav so librosa can process it without ffmpeg dependencies
    if pitch != 0:
        filename = f'tts_{formattedDateTime}_temp.wav'
    else:
        filename = f'tts_{formattedDateTime}.mp3'
        
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Generate and save the audio file
    try:
        sound = gtts.gTTS(text, lang=lang)
        sound.save(filepath)
        print(f"Audio file generated and saved to: {filepath}")
    except Exception as e:
        print(f"Error during TTS generation: {e}")
        return jsonify({'error': 'Error generating audio'}), 500

    if gender != 0:
        try:
            gender_change(text, gender)
        except Exception as e:
            print(f"Error during gender change : {e}")
            return jsonify({'error': 'Error gender change '}), 500

    # Apply pitch shift if necessary
    if pitch != 0:
        # Save output final file as a standard WAV file so it plays cleanly in the browser
        shifted_filename = f'tts_{formattedDateTime}.wav'
        shifted_filepath = os.path.join(UPLOAD_FOLDER, shifted_filename)
        try:
            pitch_shift(filepath, shifted_filepath, pitch)
            # Remove the temporary un-shifted WAV file
            if os.path.exists(filepath):
                os.remove(filepath)
            filepath = shifted_filepath
            filename = shifted_filename
        except Exception as e:
            print(f"Error during pitch adjustment: {e}")
            return jsonify({'error': 'Error adjusting pitch'}), 500

    # Return the URL for the generated audio file
    audio_url = f"/download/{filename}"
    return jsonify({'audio_url': audio_url})

# Route to serve the generated audio file
@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/')
def index():
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Text-to-Speech API</title>
        <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            body {
                padding: 40px;
                background-color: #f0f2f5;
                font-family: 'Roboto', sans-serif;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: #ffffff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
            h1 {
                margin-bottom: 20px;
                color: #333;
                text-align: center;
                font-weight: 700;
            }
            h2 {
                margin-bottom: 20px;
                color: #333;
                text-align: center;
                font-weight: 700;
            }
            h3 {
                margin-bottom: 20px;
                color: #333;
                text-align: center;
                font-weight: 700;
            }
            textarea {
                width: 100%;
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ddd;
            }
            .btn-primary, .btn-success {
                width: 48%;
                background-color: #007bff;
                border: none;
                padding: 10px;
                font-size: 18px;
                font-weight: 500;
                transition: background-color 0.3s ease;
                margin-top: 5px;
            }
            .btn-primary:hover {
                background-color: #0056b3;
            }
            .btn-success {
                background-color: #28a745;
                border: none;
                transition: background-color 0.3s ease;
            }
            .btn-success:hover {
                background-color: #218838;
            }
            #audio-player {
                margin-top: 30px;
                text-align: center;
            }
            .alert {
                margin-top: 20px;
                text-align: center;
            }
            .spinner-border {
                display: none;
                width: 3rem;
                height: 3rem;
                border-width: 0.3em;
            }
            #spinner-container {
                display: none;
                text-align: center;
                margin-top: 20px;
            }
            #spinner-container .message {
                font-size: 1.2rem;
                color: #007bff;
                margin-bottom: 10px;
                display: inline-block;
            }
            #char-count {
                margin-top: 10px;
                font-size: 1rem;
                color: #666;
            }
            .form-group label {
                font-weight: 500;
                color: #555;
            }
            .flex-container {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .flex-container .form-group {
                flex: 1;
                margin-right: 10px;
            }
            .form-group:last-child {
                margin-right: 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Text-to-Speech Converter</h2>
            <h3>Free and Unlimited FOREVER</h3>
            <form id="text-form">
                <div class="form-group">
                    <textarea id="text-input" class="form-control" rows="5" placeholder="Enter text here..." required oninput="updateCharCount()"></textarea>
                    <div id="char-count">0/5000 characters</div>
                </div>
                <div class="flex-container">
                    <div class="form-group">
                        <label for="language-select">Select Language:</label>
                        <select id="language-select" class="form-control">
                            <option value="en">English</option>
                            <option value="hi">हिन्दी</option>
                            <option value="es">Español</option>
                            <option value="fr">Français</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="pitch-select">Select Speaker:</label>
                        <select id="pitch-select" class="form-control">
                            <option value="0">Anshika</option>
                            <option value="-4">Abhishek</option>
                            <option value="-3">Kundan</option>
                            <option value="-2">Nayan Raj</option>
                            <option value="-1">Divya</option>
                            <option value="1">Pooja</option>
                            <option value="2">Mansi</option>
                            <option value="3">Shivangi</option>
                        </select>
                    </div>
                </div>
                <div class="button-container">
                    <button type="button" class="btn btn-primary" onclick="generateAudio()">Generate</button>
                    <button type="button" class="btn btn-success" onclick="generateAndDownload()">Download</button>
                </div>
                <div id="spinner-container">
                    <div class="spinner-border text-primary" role="status">
                        <span class="sr-only">Generating...</span>
                    </div>
                    <div class="message" id="spinner-message">Generating, Please wait</div>
                </div>
                <div id="audio-player"></div>
            </form>
        </div>

        <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.3/dist/umd/popper.min.js"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
        <script>
            let dotCount = 1;
            let intervalId;

            function updateCharCount() {
                const textarea = document.getElementById('text-input');
                const charCount = document.getElementById('char-count');
                const textLength = textarea.value.length;
                if (textLength > 5000) {
                    textarea.value = textarea.value.substring(0, 5000);
                    charCount.textContent = '5000/5000 characters';
                } else {
                    charCount.textContent = `${textLength}/5000 characters`;
                }
            }

            function updateSpinnerMessage() {
                const message = document.getElementById('spinner-message');
                const dots = '.'.repeat(dotCount);
                message.textContent = `Generating, Please wait${dots}`;
                dotCount = (dotCount % 3) + 1;
            }

            async function generateAudio() {
                document.getElementById('spinner-container').style.display = 'block';
                intervalId = setInterval(updateSpinnerMessage, 500);

                const text = document.getElementById('text-input').value;
                const lang = document.getElementById('language-select').value;
                const pitch = parseFloat(document.getElementById('pitch-select').value);
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ text, lang, pitch }),
                });
                const data = await response.json();

                clearInterval(intervalId);
                document.getElementById('spinner-container').style.display = 'none';

                if (data.audio_url) {
                    const audioPlayer = document.getElementById('audio-player');
                    // Changed standard audio source layout to support both .mp3 and .wav natively in HTML5
                    audioPlayer.innerHTML = `
                        <div class="alert alert-success">
                            <h2>Generated Audio</h2>
                            <audio id="audio" controls autoplay>
                                <source src="${data.audio_url}">
                                Your browser does not support the audio element.
                            </audio>
                            <br>
                            <a href="${data.audio_url}" class="btn btn-success mt-3" download>Download Audio</a>
                        </div>
                    `;
                    document.getElementById('audio').play();
                } else {
                    alert('Error generating audio: ' + (data.error || 'Unknown error'));
                }
            }

            async function generateAndDownload() {
                document.getElementById('spinner-container').style.display = 'block';
                intervalId = setInterval(updateSpinnerMessage, 500);

                const text = document.getElementById('text-input').value;
                const lang = document.getElementById('language-select').value;
                const pitch = parseFloat(document.getElementById('pitch-select').value);

                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ text, lang, pitch }),
                });
                const data = await response.json();

                clearInterval(intervalId);
                document.getElementById('spinner-container').style.display = 'none';

                if (data.audio_url) {
                    const link = document.createElement('a');
                    link.href = data.audio_url;
                    link.download = data.audio_url.split('/').pop();
                    link.click();
                } else {
                    alert('Error generating audio: ' + (data.error || 'Unknown error'));
                }
            }
        </script>
    </body>
    </html>
    """)

# Function to clean up old files
def cleanup_files():
    while True:
        current_time = datetime.now()
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if current_time - file_mod_time > timedelta(minutes=15):
                    os.remove(file_path)
                    print(f"Deleted old file: {file_path}")
        time.sleep(10)

# Start the cleanup thread
cleanup_thread = threading.Thread(target=cleanup_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(debug=True)
