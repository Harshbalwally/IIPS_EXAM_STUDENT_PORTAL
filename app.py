from flask import Flask, render_template, Response, jsonify
import cv2
from mtcnn.mtcnn import MTCNN
import pyaudio
import wave
import threading
import speech_recognition as sr
import os
import time

app = Flask(__name__)

# Initialize the webcam
cap = cv2.VideoCapture(0)

# Initialize the MTCNN face detector
detector = MTCNN()

# Initialize the speech recognizer
recognizer = sr.Recognizer()

# Lock for thread-safe webcam access
lock = threading.Lock()

# Directory to store media files
MEDIA_DIR = 'media'
os.makedirs(MEDIA_DIR, exist_ok=True)

# Global flag to track whether tests are completed
test_ready = False

# Function to record video and capture a photo from the webcam
def record_video_and_capture_photo(video_filename, photo_filename):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(video_filename, fourcc, 20.0, (640, 480))

    # Record video for 10 seconds and capture a single photo
    for _ in range(200):  # Capture approximately 10 seconds at 20 FPS
        with lock:
            ret, frame = cap.read()
            if not ret:
                break
            # Write the frame to the video file
            out.write(frame)
        time.sleep(0.05)

    # Capture a photo
    with lock:
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(photo_filename, frame)

    out.release()

# Function to capture audio using pyaudio
def record_audio(filename, duration=10, sample_rate=16000):
    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=1024)

    frames = []

    for _ in range(int(sample_rate / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save the recorded audio to a file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))

# Function to start the webcam and audio test
def run_tests():
    global test_ready
    video_filename = os.path.join(MEDIA_DIR, 'test_video.mp4')
    photo_filename = os.path.join(MEDIA_DIR, 'student_photo.jpg')
    audio_filename = os.path.join(MEDIA_DIR, 'test_audio.wav')

    # Start recording video and capture a photo
    record_video_and_capture_photo(video_filename, photo_filename)

    # Start recording audio
    record_audio(audio_filename, duration=10)

    test_ready = True

# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route to start the webcam and audio tests
@app.route('/start_test')
def start_test():
    global test_ready
    test_ready = False

    # Start the tests in a separate thread
    test_thread = threading.Thread(target=run_tests)
    test_thread.start()

    return jsonify({'message': 'Webcam and audio tests started'})

# Route to check the test status
@app.route('/check_test_status')
def check_test_status():
    return jsonify({'test_ready': test_ready})

# Route to stream the webcam feed
def generate_frames():
    while True:
        with lock:
            success, frame = cap.read()
            if not success:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

