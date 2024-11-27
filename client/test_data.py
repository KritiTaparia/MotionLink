import time
import pandas as pd
import numpy as np
from smbus2 import SMBus

# MPU-6050 Registers
PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
CONFIG       = 0x1A
GYRO_CONFIG  = 0x1B
ACCEL_CONFIG = 0x1C
INT_ENABLE   = 0x38

ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H  = 0x43

# MPU-6050 I2C address
DEVICE_ADDRESS = 0x68

def MPU_Init(bus):
    # Initialize MPU6050
    bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0)
    bus.write_byte_data(DEVICE_ADDRESS, SMPLRT_DIV, 7)
    bus.write_byte_data(DEVICE_ADDRESS, CONFIG, 0)
    bus.write_byte_data(DEVICE_ADDRESS, GYRO_CONFIG, 0)
    bus.write_byte_data(DEVICE_ADDRESS, ACCEL_CONFIG, 0)
    bus.write_byte_data(DEVICE_ADDRESS, INT_ENABLE, 1)

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

def collect_gesture_data(bus, accel_bias, gyro_bias, gesture_name, num_attempts=10, num_readings=100, sample_rate=0.1):

	acc_x = read_raw_data(bus, ACCEL_XOUT_H)
	acc_y = read_raw_data(bus, ACCEL_XOUT_H + 2)
	acc_z = read_raw_data(bus, ACCEL_XOUT_H + 4)
	# Read gyroscope data
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

	acc_x_cal = acc_x_cal / 16384.0
	acc_y_cal = acc_y_cal / 16384.0
	acc_z_cal = acc_z_cal / 16384.0
	gyro_x_cal = gyro_x_cal / 131.0
	gyro_y_cal = gyro_y_cal / 131.0
	gyro_z_cal = gyro_z_cal / 131.0


	print('ax: {:.2f} ay: {:.2f} az: {:.2f} | gx: {:.2f} gy: {:.2f} gz: {:.2f}'.format(acc_x_cal, acc_y_cal, acc_z_cal, gyro_x_cal, gyro_y_cal, gyro_z_cal))
	time.sleep(sample_rate)
	return []

def main():
	with SMBus(1) as bus:
		MPU_Init(bus)
		accel_bias, gyro_bias = calibrate_sensors(bus)
		while True:
			gestures_data = collect_gesture_data(bus, accel_bias, gyro_bias, 'test')

if __name__ == "__main__":
    main()

