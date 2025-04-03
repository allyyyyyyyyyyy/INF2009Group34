import cv2
import dlib
import time
import threading
import queue
import paho.mqtt.client as mqtt
import json
from imutils import face_utils
from scipy.spatial import distance

# Initialize face detector and shape predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("models/shape_predictor_68_face_landmarks.dat")

# Get facial landmark indices for eyes
lStart, lEnd = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
rStart, rEnd = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

# Create queues for data
frame_queue = queue.Queue()
metrics_queue = queue.Queue()

# Driver state variables
is_driver_fatigue = False
long_eye_close = False
blinking = False
consecutive_frames = 0
blink_count = 0
blink_start_time = time.time()


#---------------- Customizable Values ---------------------------
threshold = 0.25
frame_check = 40
blink_threshold = 0.2
blink_time_window = 10.0
blink_count_threshold = 5
reset_delay = 2.0
reset_timer_value = 120
timer = reset_timer_value
#---------------- Customizable Values ---------------------------

def startMQTT():
  client = mqtt.Client()
  client.connect("localhost", 1883)
  return client

def sendMQTT(message):
  global client
  client.publish("Drowsiness", message)
  

def calculate_ear(eye):
  A = distance.euclidean(eye[1], eye[5])
  B = distance.euclidean(eye[2], eye[4])
  C = distance.euclidean(eye[0], eye[3])
  ear = (A + B) / (2.0 * C)
  return ear

def process_frame():
  global consecutive_frames, blink_count, is_driver_fatigue, blink_start_time, long_eye_close, blinking
  while True:
    if not frame_queue.empty():
      frame = frame_queue.get()
      gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      subjects = detector(gray, 0)
      
      for subject in subjects:
        shape = predictor(gray, subject)
        shape = face_utils.shape_to_np(shape)
        
        # Extract eye regions
        left_eye = shape[lStart:lEnd]
        right_eye = shape[rStart:rEnd]
        
        # Calculate eye aspect ratios
        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)
        ear = (left_ear + right_ear) / 2.0
        
        # Draw eye contours
        left_eye_hull = cv2.convexHull(left_eye)
        right_eye_hull = cv2.convexHull(right_eye)
        cv2.drawContours(frame, [left_eye_hull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [right_eye_hull], -1, (0, 255, 0), 1)
        
        # Check for drowsiness
        if ear < threshold:
          consecutive_frames += 1
          if consecutive_frames >= frame_check:
            long_eye_close = True
            #sendMQTT("Fatigue")
            cv2.putText(frame, "****************ALERT!****************", (10, 30),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
          if consecutive_frames > 0 and ear > blink_threshold:
            blink_count += 1
          consecutive_frames = 0
        
        # Check for rapid blinking
        current_time = time.time()
        elapsed_time = current_time - blink_start_time
        
        if elapsed_time >= blink_time_window:
          if blink_count > blink_count_threshold:
            blinking = True
            cv2.putText(frame, "****RAPID BLINKING ALERT!****", (10, 60),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
          if elapsed_time >= blink_time_window + reset_delay:
            blink_count = 0
            blink_start_time = current_time
        
        metrics_queue.put({
          "ear": ear,
          "consecutive_frames": consecutive_frames,
          "blink_count": blink_count,
          "is_fatigue": is_driver_fatigue
        })
      
      cv2.imshow("Frame", frame)
      if cv2.waitKey(1) & 0xFF == ord("q"):
        return
      
def check_fatigue():
  global is_driver_fatigue, timer, long_eye_close, reset_timer_value
  warned_blinking = False
  while True:
    timer -= 1
    if long_eye_close and not is_driver_fatigue:
      is_driver_fatigue = True
      long_eye_close = False
      sendMQTT("Fatigue")
      print("Fatigue detected")
      timer = reset_timer_value
    if blinking and not warned_blinking:
      sendMQTT("Blinking")
      warned_blinking = True
    if timer < 0:
      is_driver_fatigue = False
      warned_blinking = False
    time.sleep(1)


def read_camera():
  cap = cv2.VideoCapture(0)
  while True:
    ret, frame = cap.read()
    if ret:
      frame_queue.put(frame)
    time.sleep(0.1)
  cap.release()
  
client = startMQTT()

def read_config(client, userdata, message):
    config = json.loads(message.payload.decode())
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

client = startMQTT()
client.subscribe("Config")
client.on_message = read_config
client.loop_start()
print("Checking config")
time.sleep(2)
client.unsubscribe("Config")
client.loop_stop()

# Load config
with open('config.json', 'r') as file:
  data = json.load(file)
  threshold = float(data.get("threshold", threshold))
  frame_check = int(data.get("frame_check", frame_check))
  blink_threshold = float(data.get("blink_threshold", blink_threshold))
  blink_time_window = float(data.get("blink_time_window", blink_time_window))
  blink_count_threshold = int(data.get("blink_count_threshold", blink_count_threshold))
  reset_delay = float(data.get("reset_delay", reset_delay))

# Start the threads

threading.Thread(target=read_camera, daemon=True).start()
threading.Thread(target=process_frame, daemon=True).start()
threading.Thread(target=check_fatigue, daemon=True).start()

try:
  while True:
    time.sleep(1)
except KeyboardInterrupt:
  cv2.destroyAllWindows()
