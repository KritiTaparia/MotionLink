from flask import Flask, request, jsonify, render_template, Response
import datetime
import time
import threading

app = Flask(__name__)

# Global variables
sensor_readings = []
gesture_log = set()  # Use a set to store unique gestures
connected_devices = ["Kunal's MacBook", "Kriti's MacBook"]
current_device_index = 0  # By default, connected to Kunal's MacBook
device_update_event = threading.Event()

@app.route('/')
def index():
    return render_template('index.html', devices=connected_devices, current_device=current_device_index)

@app.route('/sensor', methods=['POST'])
def sensor():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    try:
        ax = data['ax']
        ay = data['ay']
        az = data['az']
        label = data.get('label', "")
        timestamp = datetime.datetime.now()

        # Append the reading to the global list
        sensor_readings.append({
            'timestamp': timestamp,
            'ax': ax,
            'ay': ay,
            'az': az,
            'label': label
        })

        # Remove readings older than 2 minutes
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=2)
        sensor_readings[:] = [reading for reading in sensor_readings if reading['timestamp'] > cutoff_time]

        # Add to gesture log if label is present and unique
        if label and label not in gesture_log:
            gesture_log.add(label)

        return jsonify({"message": "Sensor data received"}), 200

    except KeyError as e:
        return jsonify({"error": f"Missing key: {e}"}), 400

@app.route('/data', methods=['GET'])
def data():
    # Remove readings older than 2 minutes before sending data to the client
    cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=2)
    filtered_readings = [
        reading for reading in sensor_readings if reading['timestamp'] > cutoff_time
    ]

    # Format timestamps to strings before sending data to the client
    formatted_readings = [
        {
            'timestamp': reading['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
            'ax': reading['ax'],
            'ay': reading['ay'],
            'az': reading['az'],
            'label': reading['label']
        } for reading in filtered_readings
    ]
    return jsonify({"readings": formatted_readings, "gestures": list(gesture_log), "current_device": current_device_index, "devices": connected_devices})

@app.route('/switch_device', methods=['POST'])
def switch_device():
    global current_device_index
    try:
        # Switch to the next device
        current_device_index = (current_device_index + 1) % len(connected_devices)
        device_update_event.set()  # Notify clients of the change
        device_update_event.clear()
        return jsonify({"message": "Device switched", "current_device": connected_devices[current_device_index]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/device_updates')
def device_updates():
    def stream():
        while True:
            device_update_event.wait()  # Wait for the event
            yield f"data: {current_device_index}\n\n"
    return Response(stream(), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(port=6969, host='0.0.0.0', debug=True)

