import time
import numpy as np
import tensorflow as tf
from smbus2 import SMBus
from collections import deque
import pickle

# MPU-6050 Registers
PWR_MGMT_1   = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H  = 0x43

# MPU-6050 I2C address
DEVICE_ADDRESS = 0x68

def MPU_Init(bus):
    # Initialize MPU6050
    bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0)
    # Additional configuration can be added here if needed

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
    gyro_bias = {'x': 0, 'y': 0, 'z': 0}

    for _ in range(num_samples):
        acc_x = read_raw_data(bus, ACCEL_XOUT_H)
        acc_y = read_raw_data(bus, ACCEL_XOUT_H + 2)
        acc_z = read_raw_data(bus, ACCEL_XOUT_H + 4)
        gyro_x = read_raw_data(bus, GYRO_XOUT_H)
        gyro_y = read_raw_data(bus, GYRO_XOUT_H + 2)
        gyro_z = read_raw_data(bus, GYRO_XOUT_H + 4)

        accel_bias['x'] += acc_x
        accel_bias['y'] += acc_y
        accel_bias['z'] += acc_z
        gyro_bias['x'] += gyro_x
        gyro_bias['y'] += gyro_y
        gyro_bias['z'] += gyro_z

        time.sleep(0.001)

    # Average the biases
    accel_bias = {k: v / num_samples for k, v in accel_bias.items()}
    gyro_bias = {k: v / num_samples for k, v in gyro_bias.items()}

    # Adjust Z-axis accelerometer bias for gravity (+1g)
    accel_bias['z'] -= 16384  # For ±2g scale

    print("Calibration complete.")
    return accel_bias, gyro_bias

def main():
    with SMBus(1) as bus:
        MPU_Init(bus)
        accel_bias, gyro_bias = calibrate_sensors(bus)

        # Load the TensorFlow Lite model
        interpreter = tf.lite.Interpreter(model_path="gesture_recognition_model.tflite")
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        # Load the scaler
        with open('scaler.pkl', 'rb') as f:
            scaler = pickle.load(f)

        # Load the label encoder
        with open('label_encoder.pkl', 'rb') as f:
            label_encoder = pickle.load(f)
        gestures = label_encoder.classes_

        window_size = 20  # Must match the window size used during training
        data_window = deque(maxlen=window_size)
        num_features = 6  # Number of features

        # Parameters for cooldown and confidence threshold
        cooldown_time = 1.0  # Time in seconds to wait after detecting a gesture
        last_detection_time = time.time() - cooldown_time  # Initialize to allow immediate detection
        confidence_threshold = 0.7  # Minimum confidence to consider a detection valid

        try:
            print("Starting real-time gesture detection. Press Ctrl+C to exit.")
            while True:
                # Read sensor data
                acc_x = read_raw_data(bus, ACCEL_XOUT_H)
                acc_y = read_raw_data(bus, ACCEL_XOUT_H + 2)
                acc_z = read_raw_data(bus, ACCEL_XOUT_H + 4)
                gyro_x = read_raw_data(bus, GYRO_XOUT_H)
                gyro_y = read_raw_data(bus, GYRO_XOUT_H + 2)
                gyro_z = read_raw_data(bus, GYRO_XOUT_H + 4)

                # Apply calibration
                acc_x_cal = acc_x - accel_bias['x']
                acc_y_cal = acc_y - accel_bias['y']
                acc_z_cal = acc_z - accel_bias['z']
                gyro_x_cal = gyro_x - gyro_bias['x']
                gyro_y_cal = gyro_y - gyro_bias['y']
                gyro_z_cal = gyro_z - gyro_bias['z']

                # Convert to physical units
                acc_x_g = acc_x_cal / 16384.0
                acc_y_g = acc_y_cal / 16384.0
                acc_z_g = acc_z_cal / 16384.0
                gyro_x_dps = gyro_x_cal / 131.0
                gyro_y_dps = gyro_y_cal / 131.0
                gyro_z_dps = gyro_z_cal / 131.0

                # Create data array
                data = [acc_x_g, acc_y_g, acc_z_g, gyro_x_dps, gyro_y_dps, gyro_z_dps]
                data = np.array(data).reshape(1, -1)

                # Standardize data using the scaler
                data_scaled = scaler.transform(data)

                # Append data to window
                data_window.append(data_scaled.flatten())

                current_time = time.time()
                # Check if cooldown period has passed
                if len(data_window) == window_size and (current_time - last_detection_time) >= cooldown_time:
                    # Prepare input tensor
                    input_data = np.array(data_window)
                    input_data = input_data.reshape(1, window_size, num_features).astype(np.float32)

                    interpreter.set_tensor(input_details[0]['index'], input_data)
                    interpreter.invoke()
                    output_data = interpreter.get_tensor(output_details[0]['index'])
                    predicted_label = np.argmax(output_data)
                    confidence = output_data[0][predicted_label]

                    if confidence > confidence_threshold:
                        gesture_name = gestures[predicted_label]
                        print(f"Gesture Detected: {gesture_name} (Confidence: {confidence:.2f})")
                        last_detection_time = current_time  # Update the last detection time
                        # Clear the window to avoid overlapping predictions
                        data_window.clear()
                    else:
                        # Optionally, do not print anything if confidence is low
                        pass
                time.sleep(0.02)
        except KeyboardInterrupt:
            print("\nExiting...")

if __name__ == "__main__":
    main()

