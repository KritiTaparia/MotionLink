import asyncio
import websockets
import json
import time
from smbus2 import SMBus

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
        # {
        #         "ip": "192.168.1.101",  # Replace with MacBook2's IP
        #         "port": 6789
        # },
        # Add more MacBooks as needed
]

# Initialize I2C bus
bus = SMBus(1)  # 1 indicates /dev/i2c-1

def MPU_Init():
        # Initialize MPU6050
        bus.write_byte_data(0x68, PWR_MGMT_1, 0)

def read_raw_data(addr):
        # Read raw 16-bit value
        high = bus.read_byte_data(0x68, addr)
        low = bus.read_byte_data(0x68, addr + 1)
        value = (high << 8) | low
        # Convert to signed integer
        if value > 32767:
                value -= 65536
        return value

def calibrate_sensors(num_samples=2000):
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


async def send_gesture_to_server(websocket, gesture):
        """
        Send a gesture command to the connected WebSocket server.
        """
        message = json.dumps({"gesture": gesture})
        await websocket.send(message)
        print(f"Sent gesture '{gesture}' to {websocket.remote_address}")

async def connect_to_macbook(server_info, gesture_queue):
        """
        Connect to a single MacBook WebSocket server and send gestures from the queue.
        """
        uri = f"ws://{server_info['ip']}:{server_info['port']}"
        try:
                async with websockets.connect(uri) as websocket:
                        print(f"Connected to {server_info['ip']}:{server_info['port']}")
                        while True:
                                gesture = await gesture_queue.get()
                                if gesture is None:
                                        # None is the signal to disconnect
                                        print(f"Disconnecting from {server_info['ip']}:{server_info['port']}")
                                        break
                                await send_gesture_to_server(websocket, gesture)
        except Exception as e:
                print(f"Connection to {server_info['ip']}:{server_info['port']} failed: {e}")

async def main():
        MPU_Init()
        accel_bias, gyro_bias = calibrate_sensors()

        # List of MacBooks
        macbook_list = MACBOOK_SERVERS
        current_macbook_index = 0
        total_macbooks = len(macbook_list)

        # Initialize gesture queue
        gesture_queue = asyncio.Queue()

        # Function to handle gesture sending
        async def gesture_sender():
                nonlocal current_macbook_index
                while True:
                        gesture = await gesture_queue.get()
                        if gesture == "switch":
                                # Signal to disconnect current connection
                                await gesture_queue.put(None)
                                # Update to next MacBook
                                current_macbook_index = (current_macbook_index + 1) % total_macbooks
                                next_macbook = macbook_list[current_macbook_index]
                                print(f"Switching to MacBook{current_macbook_index +1}: {next_macbook['ip']}:{next_macbook['port']}")
                                # Start connection to next MacBook
                                asyncio.create_task(connect_to_macbook(next_macbook, gesture_queue))
                        else:
                                # Send gesture to the current MacBook
                                await gesture_queue.put(gesture)

        # Start by connecting to the first MacBook
        if macbook_list:
                asyncio.create_task(connect_to_macbook(macbook_list[current_macbook_index], gesture_queue))
                print(f"Initial connection to MacBook1: {macbook_list[current_macbook_index]['ip']}:{macbook_list[current_macbook_index]['port']}")
        else:
                print("No MacBooks configured in the MACBOOK_SERVERS list.")
                return

        # Start the gesture sender
        asyncio.create_task(gesture_sender())
        
        prev_acc_x = 0
        prev_acc_z = 1  # Initialized to 1 to avoid division by zero

        threshold = 1 # Threshold in g units

        last_gesture_time = 0
        gesture_cooldown = 1.5  # seconds

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

                        if gesture_magnitudes and gesture and (current_time - last_gesture_time) > gesture_cooldown:
                                gesture = max(gesture_magnitudes, key=gesture_magnitudes.get)
                                print(f"Detected gesture: {gesture}")
                                await gesture_queue.put(gesture)
                                last_gesture_time = current_time

                        await asyncio.sleep(0.1)  # Adjust the sleep time as needed
        except KeyboardInterrupt:
                print("\nExiting...")

if __name__ == "__main__":
        asyncio.run(main())

