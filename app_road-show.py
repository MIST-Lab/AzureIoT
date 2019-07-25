import sys
import time
import config
# LCD
sys.path.insert(0, 'sample/LCD')
import LCD_lib
# mpu6050
from mpu6050 import mpu6050
# LED
sys.path.insert(1, 'sample/LED')
import LED_lib
# music
import pygame

def lcd_init():
    LCD_lib.init_lcd()

def lcd_warning():
    LCD_lib.warning_lcd()

def three_axis():
    sensor = mpu6050(address = config.I2C_ADDRESS)
    try:
        while True:
            accel_data = sensor.get_accel_data(g=True)
            all_data = sensor.get_all_data()
            print(accel_data)
            limitTagX = accel_data['x']
            limitTagY = accel_data['y']
            limitTagZ = accel_data['z']
            limitTag = config.LIMIT_TAG
            time.sleep(1)
            if (limitTagY*limitTagY + limitTagZ*limitTagZ > limitTag):
                print ("ERROR")
                lcd_warning()
                sound_play()
    except KeyboardInterrupt:
        print ("Software Closed")

def led_blink():
    LED_lib.led_blink()

def sound_play():
    pygame.init()
    pygame.mixer.init(44100)
    pygame.mixer.music.load('./assets/youDare.mp3')
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        led_blink()
        pygame.event.wait()

if __name__ == '__main__' :
    lcd_init()
    # lcd_warning()
    three_axis()