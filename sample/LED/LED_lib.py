import RPi.GPIO as GPIO
import sys
import time
sys.path.insert(0, '../../')
import config

GPIO.setmode(GPIO.BOARD)
GPIO.setup(config.GPIO_PIN_ADDRESS, GPIO.OUT)
GPIO.output(config.GPIO_PIN_ADDRESS, GPIO.HIGH)

def led_blink():
    for index in range(1,20):
        GPIO.output(config.GPIO_PIN_ADDRESS, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(config.GPIO_PIN_ADDRESS, GPIO.LOW)
        time.sleep(0.5)