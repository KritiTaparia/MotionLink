import time
import numpy as np
from smbus2 import SMBus
import subprocess
from evdev import UInput, ecodes as e

# MPU-6050 Registers and addresses
PWR_MGMT_1   = 0x6B
ACCEL_XOUT_H = 0x3B
DEVICE_ADDRESS = 0x68  # MPU-6050 I2C address

paired_devices = ['80:A9:97:36:8B:94']
current_device_index = 0
# Initialize UInput device for keyboard events
ui = UInput()

def MPU_Init(bus):
        # Initialize MPU6050
        bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0)
        # Additional configuration can be added here if needed

def switch_device():
        global current_device_index
        current_mac = paired_devices[current_device_index]
        # Disconnect from current device
        subprocess.run(['bluetoothctl', 'disconnect', current_mac])

        # Move to next device
        current_device_index = (current_device_index + 1) % len(paired_devices)
        next_mac = paired_devices[current_device_index]

        # Connect to next device
        subprocess.run(['bluetoothctl', 'connect', next_mac])
        print(f"Switched to device: {next_mac}")

def read_raw_data(bus, addr):
        # Read raw 16-bit value
        high = bus.read_byte_data(DEVICE_ADDRESS, addr)
        low = bus.read_byte_data(DEVICE_ADDRESS, addr+1)
        value = (high << 8) | low
        # Convert to signed integer
        if value > 32767:
                value -= 65536
        return value

def calibrate_sensors(bus, num_samples=2000):
        print("Calibrating sensors... Please keep the sensor stationary.")
        accel_bias = {'x': 0, 'y': 0, 'z': 0}

        for _ in range(num_samples):
                acc_x = read_raw_data(bus, ACCEL_XOUT_H)
                acc_y = read_raw_data(bus, ACCEL_XOUT_H + 2)
                acc_z = read_raw_data(bus, ACCEL_XOUT_H + 4)

                accel_bias['x'] += acc_x
                accel_bias['y'] += acc_y
                accel_bias['z'] += acc_z

                time.sleep(0.001)

        # Average the biases
        accel_bias = {k: v / num_samples for k, v in accel_bias.items()}

        # Adjust Z-axis accelerometer bias for gravity (+1g)
        accel_bias['z'] -= 16384  # For ±2g scale

        print("Calibration complete.")
        return accel_bias

def send_key(key_code):
    ui.write(e.EV_KEY, key_code, 1)  # Key press
    ui.write(e.EV_KEY, key_code, 0)  # Key release
    ui.syn()
    print('Sent keycode:', key_code)

def main():
        with SMBus(1) as bus:
                MPU_Init(bus)
                accel_bias = calibrate_sensors(bus)

                print("Starting gesture detection. Press Ctrl+C to exit.")
                switch_device()
                send_key(e.KEY_A)
                send_key(e.KEY_S)
                send_key(e.KEY_S)

                prev_acc_x = 0
                prev_acc_z = 1  # Initialized to 1 to avoid division by zero

                threshold = 1 # Threshold in g units

                # Cooldown to prevent multiple detections
                cooldown_time = 1.5 # in seconds
                last_detection_time = 0  # Time of the last detected gesture

                try:
                        while True:
                                # Read accelerometer data
                                acc_x = read_raw_data(bus, ACCEL_XOUT_H)
                                acc_y = read_raw_data(bus, ACCEL_XOUT_H + 2)
                                acc_z = read_raw_data(bus, ACCEL_XOUT_H + 4)

                                # Apply calibration
                                acc_x_cal = acc_x - accel_bias['x']
                                acc_y_cal = acc_y - accel_bias['y']
                                acc_z_cal = acc_z - accel_bias['z']

                                # Convert to physical units
                                acc_x_g = acc_x_cal / 16384.0
                                acc_y_g = acc_y_cal / 16384.0
                                acc_z_g = acc_z_cal / 16384.0

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

                                # Determine the gesture with the maximum magnitude
                                if gesture_magnitudes:
                                        # Check cooldown
                                        if (current_time - last_detection_time) > cooldown_time:
                                                # Get the gesture with the highest magnitude difference
                                                detected_gesture = max(gesture_magnitudes, key=gesture_magnitudes.get)
                                                print(f"{detected_gesture.capitalize()} Swipe Detected")
                                                if detected_gesture == 'up':
                                                        send_key(e.KEY_UP)
                                                elif detected_gesture == 'left':
                                                        send_key(e.KEY_LEFT)
                                                elif detected_gesture == 'down':
                                                        send_key(e.KEY_DOWN)
                                                elif detected_gesture == 'right':
                                                        send_key(e.KEY_RIGHT)
                                                last_detection_time = current_time

                                # Update previous values
                                prev_acc_x = acc_x_g
                                prev_acc_z = acc_z_g

                                time.sleep(0.01)  # Adjust sampling rate as needed

                except KeyboardInterrupt:
                        print("\nExiting...")

if __name__ == "__main__":
        main()
