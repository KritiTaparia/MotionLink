'''
import time
import numpy as np
import matplotlib.pyplot as plt
from smbus2 import SMBus

# MPU-6050 Registers and addresses
PWR_MGMT_1   = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H  = 0x43

DEVICE_ADDRESS = 0x68  # MPU-6050 I2C address

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

        # Initialize matplotlib
        plt.ion()
        fig, axs = plt.subplots(2, 1, figsize=(10, 8))

        # Initialize data lists
        x_data = []
        acc_x_list = []
        acc_y_list = []
        acc_z_list = []
        gyro_x_list = []
        gyro_y_list = []
        gyro_z_list = []

        max_points = 200  # Maximum number of points to display

        start_time = time.time()

        print("Starting real-time data plotting. Press Ctrl+C to exit.")

        try:
            while True:
                current_time = time.time() - start_time
                x_data.append(current_time)

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

                # Append data to lists
                acc_x_list.append(acc_x_g)
                acc_y_list.append(acc_y_g)
                acc_z_list.append(acc_z_g)
                gyro_x_list.append(gyro_x_dps)
                gyro_y_list.append(gyro_y_dps)
                gyro_z_list.append(gyro_z_dps)

                # Limit the lists to max_points
                x_data = x_data[-max_points:]
                acc_x_list = acc_x_list[-max_points:]
                acc_y_list = acc_y_list[-max_points:]
                acc_z_list = acc_z_list[-max_points:]
                gyro_x_list = gyro_x_list[-max_points:]
                gyro_y_list = gyro_y_list[-max_points:]
                gyro_z_list = gyro_z_list[-max_points:]

                # Clear the plots
                axs[0].cla()
                axs[1].cla()

                # Plot accelerometer data
                axs[0].plot(x_data, acc_x_list, label='Acc X')
                axs[0].plot(x_data, acc_y_list, label='Acc Y')
                axs[0].plot(x_data, acc_z_list, label='Acc Z')
                axs[0].set_ylabel('Acceleration (g)')
                axs[0].legend(loc='upper right')
                axs[0].set_title('Accelerometer Data')

                # Plot gyroscope data
                axs[1].plot(x_data, gyro_x_list, label='Gyro X')
                axs[1].plot(x_data, gyro_y_list, label='Gyro Y')
                axs[1].plot(x_data, gyro_z_list, label='Gyro Z')
                axs[1].set_xlabel('Time (s)')
                axs[1].set_ylabel('Angular Velocity (°/s)')
                axs[1].legend(loc='upper right')
                axs[1].set_title('Gyroscope Data')

                # Adjust layout and pause
                plt.tight_layout()
                plt.pause(0.001)

                time.sleep(0.01)  # Adjust sampling rate as needed

        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            plt.ioff()
            plt.show()

if __name__ == "__main__":
    main()
'''
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt


plt.plot([1, 2, 3], [1, 4, 9])
plt.title('Test Plot')
plt.xlabel('x')
plt.ylabel('y')
plt.show()

