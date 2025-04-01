# INF 2009 Group 34

## Project Description
Talk about the project

## Block Diagram

<img src="assets/system-design.png" alt="drawing" width="500"/>

## Setup
If needed..

- How to setup the hardware and front end, prerequisites 

## Accelerometer

### Description

The accelerometer used is a LIS3DH which is mounted to the Raspberry Pi which is mounted to the vehicles steering wheel. Its goal is to detect the steering wheel movements as well as the acceleration of the car. These measurements will be used to detect potential fatigue in the driver or signs of dangerous driving.

### Libraries
1. busio: Used for I2C protocol to communicate with the accelerometer
2. adafruit_lis3dh: Used to make interfacing with the accelerometer easier
3. matplotlib: used for visualizing the changes in car movement and steering movement

### How its done

The Raspberry Pi communicates with the Accelerometer using I2C protocol and we made use of the Adafruit CircuitPython library in Python to record accelerometer data. The readings from the accelerometer are then put into a FIFO queue for the purposes for decision making and visualisation.

The accelerometer decision system keep tracks of sudden changes of steering movements 'steering_threshold' or sudden acceleration or deceleration (example jam braking) 'accel_threshold' and keep a tally.  These values are reset by a percentage 'percentage_reduce' every time period 'timer_value'

If the number of occurrences exceed a specified threshold 'steering_movement_threshold' and 'sudden_brake_threshold' it will deem that the driver is fatigued/driving dangerously and send a message through MQTT to the central decision system. After a set time 'steering_cooldown' the driver state in the system will reset. 

<img src="assets/Graph_visuals.jpg" alt="graph" width="200"/>

The visualisation are created using Matplotlib primarily used for testing and configuration of thresholds. It can be omitted during runtime to free up computing resources.

### Results

Detecting driver fatigue

<img src="assets/accelrometer_detection.jpg" alt="graph" width="200"/>


## Eye tracking using webcam

This feature is inspired by [Akshay Bahadur](https://github.com/akshaybahadur21/Drowsiness_Detection.git). Credits goes to repo owner.

### Description

The algorithm and [model](models/shape_predictor_68_face_landmarks.dat) of the original code was taken to aid in better detection and measurement of Eye Aspect Ratio (EAR). How it is different is [Webcam](webcam.py) applies MQTT format for easier integration with the other parts of the system, added blinking detection for detection of rapid blinking which is one of the sign of fatigue, as well as customisable thresholds in [Conguration File](config.json) where system user change the values base on different eye behaviours and features.

### Libraries

1) cv2 : A open-source real-time computer vision used for capturing video, process frames and drawing contours around the eyes
2) imutils : convert facial landmarks into a NumPy array format for easier manipualtion
3) dlib : an ML and CV toolkit used for specific facial landmarks, such as the eyes.
4) scipy : to calculate the Euclidean distance between points for Eye Aspect Ratio (EAR)

### How its done 

Each eye is represented by 6 (x, y)-coordinates, starting at the left-corner of the eye (as if you were looking at the person), and then working clockwise around the eye.

It checks value of `threshold` consecutive frames and if the Eye Aspect ratio is less than value of `frame_check`, necessary executions to the system is triggered for long eye closure. Whereas for blinking, it checks `blink_threshold` for EAR specifically for this feature. If it exceeded `blink_count_threshold` within time period of `blink_time_window`, it will trigger rapid blinking. `reset_delay` before it resets and counts again.

<img src="assets/eye1.jpg" alt="drawing" width="200"/>

#### Base formuale used:

<img src="assets/eye2.png" alt="drawing" width="350"/>

#### Summing up:

<img src="assets/eye3.jpg" alt="drawing" width="300"/>

#### Results:

Will send alerts through the system by MQTT

<img src="assets/blinking.jpg" alt="drawing" width="500"/>

<img src="assets/alarm.jpg" alt="drawing" width="500"/>

For more information, [see](https://www.pyimagesearch.com/2017/05/08/drowsiness-detection-opencv/)


## Fatigue Decision system
What its used for, how its done, results etc
