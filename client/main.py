from tkinter.constants import ON
import asyncio
import websockets
import json
import time
import requests
from smbus2 import SMBus
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

# MPU-6050 Registers
PWR_MGMT_1   = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H  = 0x43

# WebSocket Server details for each MacBook
MACBOOK_SERVERS = [
    {
        "ip": "192.168.0.110",  # Replace with MacBook1's IP
        "port": 6789
    },
    {
        "ip": "192.168.0.172",  # Replace with MacBook1's IP
        "port": 6789
    },
]

# Initialize I2C bus
bus = SMBus(1)  # 1 indicates /dev/i2c-1
LED_PINS = [18, 13]
for pin in LED_PINS:
    GPIO.setup(pin, GPIO.OUT)

def MPU_Init():
    """
    Initialize the MPU6050 sensor.
    """
    bus.write_byte_data(0x68, PWR_MGMT_1, 0)
    print("MPU6050 initialized.")

def read_raw_data(addr):
    """
    Read raw 16-bit value from the MPU6050 sensor.
    """
    high = bus.read_byte_data(0x68, addr)
    low = bus.read_byte_data(0x68, addr + 1)
    value = (high << 8) | low
    # Convert to signed integer
    if value > 32767:
        value -= 65536
    return value

def calibrate_sensors(num_samples=2000):
    """
    Calibrate the MPU6050 sensor by averaging multiple readings.
    """
    print("Calibrating sensors... Please keep the sensor stationary.")
    accel_bias = {'x': 0, 'y': 0, 'z': 0}
    gyro_bias = {'x': 0, 'y': 0, 'z': 0}

    for _ in range(num_samples):
        acc_x = read_raw_data(ACCEL_XOUT_H)
        acc_y = read_raw_data(ACCEL_XOUT_H + 2)
        acc_z = read_raw_data(ACCEL_XOUT_H + 4)
        gyro_x = read_raw_data(GYRO_XOUT_H)
        gyro_y = read_raw_data(GYRO_XOUT_H + 2)
        gyro_z = read_raw_data(GYRO_XOUT_H + 4)

        accel_bias['x'] += acc_x
        accel_bias['y'] += acc_y
        accel_bias['z'] += acc_z
        gyro_bias['x'] += gyro_x
        gyro_bias['y'] += gyro_y
        gyro_bias['z'] += gyro_z

        time.sleep(0.001)  # 1ms delay

    # Average the biases
    accel_bias = {k: v / num_samples for k, v in accel_bias.items()}
    gyro_bias = {k: v / num_samples for k, v in gyro_bias.items()}

    # Adjust Z-axis accelerometer bias for gravity (+1g)
    accel_bias['z'] -= 16384  # For ±2g scale

    print("Calibration complete.")
    return accel_bias, gyro_bias

async def send_gesture(websocket, gesture):
    """
    Send a gesture command to the connected WebSocket server.
    """
    message = json.dumps({"gesture": gesture})
    try:
        await websocket.send(message)
        print(f"Sent gesture '{gesture}' to {websocket.remote_address}")
    except Exception as e:
        print(f"Failed to send gesture '{gesture}': {e}")

async def connect_to_device(uri):
    """
    Establish a WebSocket connection to the given URI.
    Returns the websocket object if successful, else None.
    """
    try:
        websocket = await websockets.connect(uri)
        print(f"Connected to {uri}")
        return websocket
    except Exception as e:
        print(f"Failed to connect to {uri}: {e}")
        return None

# Global variable to track the last request time
last_request_time = 0
RATE_LIMIT_INTERVAL = 1  # Minimum time interval (in seconds) between requests

def send_sensor_readings(ax, ay, az, gesture):
    global last_request_time
    SERVER_URL = 'http://localhost:6969/sensor'
    current_time = time.time()

    # Check if the interval since the last request is less than the rate limit
    if current_time - last_request_time < RATE_LIMIT_INTERVAL:
        print("Rate limit exceeded. Skipping this request.")
        return

    try:
        response = requests.post(SERVER_URL, json={
            'ax': ax,
            'ay': ay,
            'az': az,
            'label': gesture
        })
        last_request_time = current_time  # Update the last request time
        print(response)
    except Exception as e:
        print('Error:', e)

async def main():
    # Initialize and calibrate the MPU6050 sensor
    MPU_Init()
    accel_bias, gyro_bias = calibrate_sensors()

    # List of MacBooks
    macbook_list = MACBOOK_SERVERS
    current_macbook_index = 0
    total_macbooks = len(macbook_list)

    if not macbook_list:
        print("No MacBooks configured in the MACBOOK_SERVERS list.")
        return
    

    # Define thresholds for gesture detection (adjust as needed)
    threshold = 1  # Threshold in g units
    last_gesture_time = 0
    gesture_cooldown = 1.5  # seconds

    # Establish initial connection
    current_macbook = macbook_list[current_macbook_index]
    uri = f"ws://{current_macbook['ip']}:{current_macbook['port']}"
    websocket = await connect_to_device(uri)
    if websocket:
        GPIO.output(LED_PINS[current_macbook_index], GPIO.HIGH)
        print('LED1 on')

    # Initialize previous acceleration values
    prev_acc_x = 0
    prev_acc_z = 1  # Initialized to 1 to avoid division by zero

    try:
        while True:
            # Read sensor data
            acc_x = read_raw_data(ACCEL_XOUT_H) - accel_bias['x']
            acc_y = read_raw_data(ACCEL_XOUT_H + 2) - accel_bias['y']
            acc_z = read_raw_data(ACCEL_XOUT_H + 4) - accel_bias['z']
            gyro_x = read_raw_data(GYRO_XOUT_H) - gyro_bias['x']
            gyro_y = read_raw_data(GYRO_XOUT_H + 2) - gyro_bias['y']
            gyro_z = read_raw_data(GYRO_XOUT_H + 4) - gyro_bias['z']

            # Convert raw data to 'g' and 'deg/s'
            acc_x_g = acc_x / 16384.0  # For ±2g
            acc_y_g = acc_y / 16384.0
            acc_z_g = acc_z / 16384.0
            print('AX = ', acc_x_g, 'AY = ', acc_y_g, 'AZ = ', acc_z_g) 

            gyro_x_dps = gyro_x / 131.0  # For ±250°/s
            gyro_y_dps = gyro_y / 131.0
            gyro_z_dps = gyro_z / 131.0

            current_time = time.time()

            # Calculate differences
            delta_acc_x = prev_acc_x - acc_x_g
            delta_acc_z = prev_acc_z - acc_z_g

            # Initialize gesture magnitudes
            gesture_magnitudes = {}

            # Detect Left Swipe
            if delta_acc_x > 2 * threshold:
                gesture_magnitudes['left'] = delta_acc_x

            # Detect Right Swipe
            if delta_acc_x < -2 * threshold:
                gesture_magnitudes['right'] = -delta_acc_x

            # Detect Up Swipe
            if delta_acc_z > 2 * threshold:
                gesture_magnitudes['up'] = delta_acc_z

            # Detect Down Swipe
            if delta_acc_z < -2 * threshold:
                gesture_magnitudes['down'] = -delta_acc_z

            # Detect and handle gestures
            if gesture_magnitudes and (current_time - last_gesture_time) > gesture_cooldown:
                gesture = max(gesture_magnitudes, key=gesture_magnitudes.get)
                print(f"Detected gesture: {gesture}")
                send_sensor_readings(acc_x_g, acc_y_g, acc_z_g, gesture)

                if gesture == "down":
                    # Switch to the next MacBook
                    if websocket:
                        await websocket.close()
                        GPIO.output(LED_PINS[current_macbook_index], GPIO.LOW)
                        print(f"Disconnected from {current_macbook['ip']}:{current_macbook['port']}")

                    # Update to next MacBook
                    current_macbook_index = (current_macbook_index + 1) % total_macbooks
                    current_macbook = macbook_list[current_macbook_index]
                    uri = f"ws://{current_macbook['ip']}:{current_macbook['port']}"
                    print(f"Switching to MacBook{current_macbook_index +1}: {current_macbook['ip']}:{current_macbook['port']}")

                    # Connect to the next MacBook
                    websocket = await connect_to_device(uri)
                    if websocket:
                        GPIO.output(LED_PINS[current_macbook_index], GPIO.HIGH)
                else:
                    # Send the gesture to the current MacBook
                    if websocket:
                        await send_gesture(websocket, gesture)
                    else:
                        print("No active WebSocket connection. Attempting to reconnect...")
                        websocket = await connect_to_device(uri)
                        if websocket:
                            await send_gesture(websocket, gesture)

                # Update last gesture time
                last_gesture_time = current_time
            else:
                send_sensor_readings(acc_x_g, acc_y_g, acc_z_g, '')

            # Update previous acceleration values
            prev_acc_x = acc_x_g
            prev_acc_z = acc_z_g

            # Sleep before next iteration
            await asyncio.sleep(0.1)  # Adjust the sleep time as needed

    except KeyboardInterrupt:
        print("\nExiting...")
        if websocket:
            await websocket.close()
    except Exception as e:
        print(f"An error occurred: {e}")
        for pin in LED_PINS:
            GPIO.output(pin, GPIO.LOW)
        if websocket:
            await websocket.close()

if __name__ == "__main__":
    asyncio.run(main())


