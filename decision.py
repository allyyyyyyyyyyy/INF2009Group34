import random
import time
import json
import pyttsx3
import pygame
from vosk import Model, KaldiRecognizer
import pyaudio
import paho.mqtt.client as mqtt
import threading

# Variables
accel_fatigue = False
cam_fatigue = False

# === INIT TEXT-TO-SPEECH ===
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

# === INIT ALARM ===
pygame.mixer.init()
pygame.mixer.music.load("test.wav")  # Ensure you have alarm.wav in the same folder

# === INIT VOSK MODEL & AUDIO STREAM ===
model = Model("model")  # Folder with vosk model files
recognizer = KaldiRecognizer(model, 16000)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8000)
stream.start_stream()

# === LISTEN FOR A SPECIFIC WORD OFFLINE ===
def listen_for_word(expected_word, timeout=10):
    print(f"?? Say the word '{expected_word}' within {timeout} seconds...")
    end_time = time.time() + timeout
    while time.time() < end_time:
        data = stream.read(4000, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            heard = result.get("text", "").lower()
            print("?? Heard:", heard)

            if expected_word.lower() in heard:
                return True
    return False

# === ALARM UNTIL USER RESPONDS ===
def play_alarm_until_awake():
    print("?? Alarm playing...")
    pygame.mixer.music.play(-1)  # Loop the alarm
    while True:
        if listen_for_word("i am awake now", timeout=5):
            print("? Driver confirmed they're awake.")
            pygame.mixer.music.stop()
            break
        else:
            print("? No valid response yet.")

# === MAIN TEST LOOP ===
def test_fatigue_detection_loop():
    #while True:
        print("\n[TEST MODE] Fatigue detected...")

        # Random challenge word
        random_word = random.choice(["hello"])
        speak(f"Hi, you seem to be sleepy. If you are awake and aware, please say the word {random_word}")

        if not listen_for_word(random_word, timeout=10):
            speak("You did not respond correctly.")
            play_alarm_until_awake()
        else:
            print("? Driver responded correctly. No fatigue detected.")

        #time.sleep(10)  # Wait before next simulated fatigue check

def on_message(client, userdata, message):
    print(f"Received message '{message.payload.decode()}' on topic '{message.topic}'")
    if message.topic == "Accelerometer":
        if message.payload.decode() == "Fatigue":
            accel_fatigue = True
        elif message.payload.decode() == "Reset":
            accel_fatigue = False
    
    if accel_fatigue == True or cam_fatigue == True:
        #test_fatigue_detection_loop()
        threading.Thread(target=test_fatigue_detection_loop, daemon=True).start()

def main():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("localhost", 1883)
    client.subscribe("test/topic")
    client.loop_forever()

# === RUN MAIN LOOP ===
if __name__ == "__main__":
    main()


