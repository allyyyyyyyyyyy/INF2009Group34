import time
import threading
import queue
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import board
import busio
import adafruit_lis3dh
import math
import sys
import paho.mqtt.client as mqtt
import json

# Initialize I2C bus and accelerometer
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)

# Default x and z values
default_x = 0
default_z = 0

# Create a FIFO queue
x_data_queue = queue.Queue()
y_data_queue = queue.Queue()

# Variable to hold count of sudden movement
steering_sudden_movement = 0
sudden_brake_movement = 0

# Declare timer variables for value resets
fatigue_time = None
reset_time = None

# Driver state
is_driver_fatigue = False

#---------------- Customizable Values ---------------------------

# Define the steering_threshold for detecting sharp changes (in m/s²)
steering_threshold = 7.0

# Timer to reset sudden movement count
timer_value = 120
timer = timer_value

# Percentage to reduce sudden movements by each time
percentage_reduce = 0.5
percentage_reduce_fatigue = 0.25

# Sudden steering threshold. Exceeding theshold suggest driver is tired
steering_movement_threshold = 20

# Time between steering_threshold exceeding and reseting the driver state
steering_cooldown = 300

# Acceleration threshold
accel_threshold = 3

# Sudden Braking threshold.
sudden_brake_threshold = 5

#---------------- Customizable Values ---------------------------

def startMQTT():
    client = mqtt.Client()
    client.connect("localhost", 1883)
    return client

# Function to perform action on driver fatigue
def sendMQTT(message):
    global client
    client.publish("Accelerometer", message)
    print("Fatigue detected")

# Calibrate system
def calibrate_default():
    global default_x, default_z
    default_x_array = []
    default_y_array = []
    print("Calibrating... do not move the device")
    for i in range(0, 50):
        x, y, _ = accel.acceleration
        default_x_array.append(x)
        default_y_array.append(y)
        sys.stdout.write('\r' + str(i) + '/50 recorded')
        time.sleep(0.1)
    default_x = sum(default_x_array)/len(default_x_array)
    default_y = sum(default_y_array)/len(default_y_array)

# Function to sudden movement checks
def check_fatigue():
    global steering_sudden_movement, sudden_brake_movement, is_driver_fatigue, fatigue_time, timer
    while True:
        # Check current state
        if (steering_sudden_movement > steering_movement_threshold or sudden_brake_movement > 5) and is_driver_fatigue == False:
            is_driver_fatigue = True
            fatigue_time = time.time()
            sendMQTT("Fatigue") # Update system
        # Reeset state if driver is normal for some time   
        if is_driver_fatigue == True and steering_sudden_movement < steering_movement_threshold and sudden_brake_movement < sudden_brake_threshold and fatigue_time < time.time() - steering_cooldown:
            is_driver_fatigue = False
            sendMQTT("Reset")
        if timer <= 0:
            if is_driver_fatigue == False: # Preodically reduce the sudden movement count
                steering_sudden_movement = math.ceil(steering_sudden_movement * (1-percentage_reduce))
                sudden_brake_movement = math.ceil(sudden_brake_movement * (1-percentage_reduce))
            else:
                steering_sudden_movement = math.ceil(steering_sudden_movement * (1-percentage_reduce_fatigue))
                sudden_brake_movement = math.ceil(sudden_brake_movement * (1-percentage_reduce_fatigue))

            timer = timer_value
        time.sleep(1)


# Function to read y accelerometer data and put it into the queue (steering)
def read_accel_data_y():
    global steering_sudden_movement, timer
    previous_y = None
    while True:
        _, y, _ = accel.acceleration  # Read X-axis acceleration
        if previous_y is not None:
            delta_y = abs(y - previous_y)
            
            if delta_y > steering_threshold and delta_y < 10:
                print(f"Sharp change detected: Δx = {delta_y:.2f} m/s²")
                steering_sudden_movement += 1
        timer-=1
        previous_y = y
        y_data_queue.put(y)
        time.sleep(0.1)  # Adjust the sampling rate as needed

# Function to read accelerometer data and put it into the queue (sudden brake)
def read_accel_data_x():
    global steering_sudden_movement, timer, default_z, sudden_brake_movement
    previous_x = None
    while True:
        x, _, _ = accel.acceleration  # Read X-axis acceleration
            
        if x > default_x + accel_threshold or x < default_x - accel_threshold:
            print(f"Jam brake detected: Δx = {x:.2f} m/s²")
            sudden_brake_movement += 1
        timer-=1
        x_data_queue.put(x)
        time.sleep(0.1)  # Adjust the sampling rate as needed

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
    steering_threshold = int(data.get("steering_threshold")) if data.get("steering_threshold") != None else steering_threshold
    timer_value = int(data.get("timer_value")) if data.get("timer_value") != None else timer_value
    percentage_reduce = float(data.get("percentage_reduce")) if data.get("percentage_reduce") != None else percentage_reduce
    percentage_reduce_fatigue = float(data.get("percentage_reduce_fatigue")) if data.get("percentage_reduce_fatigue") != None else percentage_reduce_fatigue
    steering_movement_threshold = float(data.get("steering_movement_threshold")) if data.get("steering_movement_threshold") != None else steering_movement_threshold
    steering_cooldown = int(data.get("steering_cooldown")) if data.get("steering_cooldown") != None else steering_cooldown
    accel_threshold = int(data.get("accel_threshold")) if data.get("accel_threshold") != None else accel_threshold
    sudden_brake_threshold = int(data.get("sudden_brake_threshold")) if data.get("sudden_brake_threshold") != None else sudden_brake_threshold
    
# Start the data reading thread
calibrate_default()

threading.Thread(target=read_accel_data_x, daemon=True).start()
threading.Thread(target=read_accel_data_y, daemon=True).start()
threading.Thread(target=check_fatigue, daemon=True).start()

#------------------- Visulization, can be moved to cloud or removed --------------
# Set up the plot
fig, ax = plt.subplots()
x_values, x_accel_values, y_accel_values = [], [], []
x_line, = ax.plot(x_values, x_accel_values, label='X-axis Acceleration')
y_line, = ax.plot(x_values, y_accel_values, label='Y-axis Acceleration', color='orange')
ax.set_ylim(-10, 10)  # Adjust based on expected g-force range
ax.set_xlim(0, 100)
ax.set_xlabel('Samples')
ax.set_ylabel('Acceleration (m/s²)')
ax.set_title('Real-Time Accelerometer Data')
ax.legend()

# Function to update the plot
def update_plot(frame):
    while not x_data_queue.empty() and not y_data_queue.empty():
        x_accel_values.append(x_data_queue.get())
        y_accel_values.append(y_data_queue.get())
        x_values.append(len(x_accel_values))
    x_line.set_data(x_values, x_accel_values)
    y_line.set_data(x_values, y_accel_values)
    if len(x_values) > 100:
        ax.set_xlim(len(x_values) - 100, len(x_values))
    return x_line, y_line

# Animate the plot
ani = animation.FuncAnimation(fig, update_plot, blit=True, interval=100)
plt.show()
