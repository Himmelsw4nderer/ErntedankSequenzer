import RPi.GPIO as GPIO
import serial
import time
import pygame

sound_file = 'sound.flac'
control_pin = 17
dmx_address = 1
serial_port = '/dev/ttyS0'
baud_rate = 250000

pygame.mixer.init()
pygame.mixer.music.load(sound_file)

GPIO.setmode(GPIO.BCM)
GPIO.setup(control_pin, GPIO.OUT)

ser = serial.Serial(serial_port, baud_rate)

def send_dmx(address, value):
    ser.write(b'\x00' * (address - 1))
    ser.write(bytes([value]))
    ser.write(b'\x00' * (512 - address))
    
def main_loop():
    try:
        while True:
            pygame.mixer.music.play()
            GPIO.output(control_pin, True)
            send_dmx(dmx_address, 255)
            
            time.sleep(1)

            send_dmx(dmx_address, 0)
            GPIO.output(control_pin, False)

            while pygame.mixer.music.get_busy():
                time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
        ser.close()
        pygame.quit()

if __name__ == '__main__':
    main_loop()
