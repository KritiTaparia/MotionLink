import RPi.GPIO as GPIO
import time

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)  # Use Broadcom SOC channel numbers

# Define the GPIO pin for the LED (pin 11)
LED_PIN = 18

# Set up the pin as an output
GPIO.setup(LED_PIN, GPIO.OUT)

def turn_on_led():
    """Turn the LED on"""
    GPIO.output(LED_PIN, GPIO.HIGH)

def turn_off_led():
    """Turn the LED off"""
    GPIO.output(LED_PIN, GPIO.LOW)

def blink_led(times=5, delay=0.5):
    """Blink the LED a specified number of times"""
    for _ in range(times):
        turn_on_led()
        time.sleep(delay)
        turn_off_led()
        time.sleep(delay)

try:
    # Example usage
    print("Turning LED on")
    turn_on_led()
    time.sleep(2)  # Keep LED on for 2 seconds
    
    print("Blinking LED")
    blink_led()
    
    print("Turning LED off")
    turn_off_led()

except KeyboardInterrupt:
    # Handle Ctrl+C exit
    print("LED control stopped by user")

finally:
    # Clean up GPIO on exit
    GPIO.cleanup()

