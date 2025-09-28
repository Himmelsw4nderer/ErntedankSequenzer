import RPi.GPIO as GPIO
import serial
import time
import pygame
import threading
import os
import json
from pathlib import Path

class SequenceExecutor:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.running = False
        self.current_thread = None
        self.loop_mode = False

        # Initialize hardware
        self.init_gpio()
        self.init_serial()
        self.init_pygame()

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        default_config = {
            'control_pin': 17,
            'serial_port': '/dev/ttyS0',
            'baud_rate': 250000,
            'sounds_directory': 'sounds'
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    return {**default_config, **config}
        except Exception as e:
            print(f"Error loading config: {e}")

        return default_config

    def init_gpio(self):
        """Initialize GPIO"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.config['control_pin'], GPIO.OUT)
        GPIO.output(self.config['control_pin'], False)

    def init_serial(self):
        """Initialize DMX serial connection"""
        try:
            self.ser = serial.Serial(
                self.config['serial_port'],
                self.config['baud_rate']
            )
        except Exception as e:
            print(f"Error initializing serial: {e}")
            self.ser = None

    def init_pygame(self):
        """Initialize pygame mixer for sound"""
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Error initializing pygame: {e}")

    def write_dmx(self, address, value):
        """Send DMX value to specified address"""
        if not self.ser:
            print(f"DMX not available - would send address {address}, value {value}")
            return

        try:
            # Create DMX packet
            packet = bytearray(513)  # Start code + 512 channels
            packet[0] = 0  # Start code
            packet[address] = min(255, max(0, int(value)))  # Clamp value to 0-255

            self.ser.write(packet)
            print(f"DMX: Address {address} = {value}")
        except Exception as e:
            print(f"Error sending DMX: {e}")

    def play_sound(self, sound_file, volume=1.0):
        """Play sound file with specified volume"""
        try:
            sound_path = os.path.join(self.config['sounds_directory'], sound_file)
            if not os.path.exists(sound_path):
                print(f"Sound file not found: {sound_path}")
                return

            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.set_volume(min(1.0, max(0.0, volume)))
            pygame.mixer.music.play()
            print(f"Playing sound: {sound_file} at volume {volume}")

        except Exception as e:
            print(f"Error playing sound: {e}")

    def sleep(self, seconds):
        """Sleep for specified number of seconds"""
        if seconds > 0:
            print(f"Sleeping for {seconds} seconds")
            time.sleep(float(seconds))

    def wait_for_sound(self):
        """Wait for current sound to finish playing"""
        while pygame.mixer.music.get_busy():
            if not self.running:
                pygame.mixer.music.stop()
                break
            time.sleep(0.1)

    def stop_sound(self):
        """Stop currently playing sound"""
        try:
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"Error stopping sound: {e}")

    def execute_sequence_file(self, sequence_file):
        """Execute a sequence from a Python file"""
        try:
            # Read the sequence file
            with open(sequence_file, 'r') as f:
                sequence_code = f.read()

            # Create execution context with our functions
            exec_globals = {
                'write_dmx': self.write_dmx,
                'play_sound': self.play_sound,
                'sleep': self.sleep,
                'wait_for_sound': self.wait_for_sound,
                'stop_sound': self.stop_sound,
                'time': time,
                'os': os
            }

            # Execute the sequence
            exec(sequence_code, exec_globals)

        except Exception as e:
            print(f"Error executing sequence: {e}")
            raise

    def run_sequence(self, sequence_file, loop=False):
        """Run sequence in a separate thread"""
        if self.running:
            print("Sequence already running")
            return False

        self.running = True
        self.loop_mode = loop

        def sequence_thread():
            try:
                if loop:
                    print(f"Starting sequence loop: {sequence_file}")
                    while self.running:
                        self.execute_sequence_file(sequence_file)
                        if not self.running:
                            break
                else:
                    print(f"Running sequence once: {sequence_file}")
                    self.execute_sequence_file(sequence_file)
            except Exception as e:
                print(f"Sequence execution error: {e}")
            finally:
                self.stop_sequence()

        self.current_thread = threading.Thread(target=sequence_thread)
        self.current_thread.daemon = True
        self.current_thread.start()
        return True

    def stop_sequence(self):
        """Stop currently running sequence"""
        if self.running:
            print("Stopping sequence")
            self.running = False
            self.stop_sound()

            if self.current_thread and self.current_thread.is_alive():
                self.current_thread.join(timeout=2.0)

            # Reset all DMX channels to 0
            try:
                for i in range(1, 513):
                    self.write_dmx(i, 0)
            except:
                pass

            # Turn off GPIO
            try:
                GPIO.output(self.config['control_pin'], False)
            except:
                pass

        return True

    def is_running(self):
        """Check if sequence is currently running"""
        return self.running

    def get_status(self):
        """Get current status"""
        return {
            'running': self.running,
            'loop_mode': self.loop_mode,
            'sound_playing': pygame.mixer.music.get_busy() if pygame.mixer.get_init() else False
        }

    def cleanup(self):
        """Clean up resources"""
        self.stop_sequence()

        try:
            GPIO.cleanup()
        except:
            pass

        try:
            if self.ser:
                self.ser.close()
        except:
            pass

        try:
            pygame.quit()
        except:
            pass

# Global executor instance
executor = None

def get_executor():
    """Get or create the global executor instance"""
    global executor
    if executor is None:
        executor = SequenceExecutor()
    return executor

def cleanup_executor():
    """Cleanup the global executor"""
    global executor
    if executor:
        executor.cleanup()
        executor = None
