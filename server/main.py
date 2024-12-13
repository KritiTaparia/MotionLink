import asyncio
import websockets
from pynput.keyboard import Controller, Key
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

keyboard = Controller()

SERVER_HOST = '0.0.0.0'  
SERVER_PORT = 6789       

GESTURE_KEY_MAPPING = {
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "idle": None  
}

async def handle_connection(websocket):
    logger.info(f"New connection from {websocket.remote_address}")
    try:
        async for message in websocket:
            logger.info(f"Received message: {message}")
            try:
                data = json.loads(message)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decoding failed: {e}")
                continue  

            gesture = data.get("gesture")
            if gesture in GESTURE_KEY_MAPPING:
                key = GESTURE_KEY_MAPPING[gesture]
                if key:
                    logger.info(f"Simulating key press: {key}")
                    simulate_key_press(key)
            else:
                logger.warning(f"Unknown gesture: {gesture}")
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Connection closed: {e}")
    except Exception as e:
        logger.error(f"Error in connection handler: {e}")

def simulate_key_press(key):
    """
    Simulate a keyboard key press using pynput.
    """
    try:
        if key in ['up', 'down', 'left', 'right']:
            if key == 'up':
                key = 'space'
            key_to_press = getattr(Key, key)
            keyboard.press(key_to_press)
            keyboard.release(key_to_press)
        else:
            keyboard.press(key)
            keyboard.release(key)
        logger.info(f"Key '{key}' simulated successfully.")
    except Exception as e:
        logger.error(f"Error simulating key press '{key}': {e}")

async def main():
    try:
        async with websockets.serve(handle_connection, SERVER_HOST, SERVER_PORT):
            logger.info(f"WebSocket Server started on {SERVER_HOST}:{SERVER_PORT}")
            await asyncio.Future()  
    except Exception as e:
        logger.critical(f"Server encountered a critical error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
