import RPi.GPIO as GPIO
import time
import pygame
import threading
import os
import json
from pathlib import Path
from collections import deque
from datetime import datetime

class SequenceExecutor:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.running = False
        self.current_thread = None
        self.loop_mode = False
        self.current_sequence_name = None
        self.loop_count = 0

        # Feedback system - store recent actions for real-time updates
        self.action_log = deque(maxlen=100)  # Keep last 100 actions
        self.action_listeners = set()  # Websocket connections or similar

        # Initialize hardware
        self.init_gpio()
        self.init_pygame()

        # Initialize DMX data array (start code + 512 channels)
        self.dmx_data = [0] * 513  # Index 0 is start code, 1-512 are channels

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        default_config = {
            'control_pin': 17,
            'dmx_data_pin': 18,
            'dmx_enable_pin': 22,
            'sounds_directory': 'sounds',
            'dmx_channels': 512
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
        """Initialize GPIO for DMX output"""
        try:
            GPIO.setmode(GPIO.BCM)

            # Setup control pin
            GPIO.setup(self.config['control_pin'], GPIO.OUT)
            GPIO.output(self.config['control_pin'], GPIO.LOW)

            # Setup DMX pins
            GPIO.setup(self.config['dmx_data_pin'], GPIO.OUT)
            GPIO.setup(self.config['dmx_enable_pin'], GPIO.OUT)

            # Initialize DMX pins (idle state)
            GPIO.output(self.config['dmx_data_pin'], GPIO.HIGH)  # DMX idle is HIGH
            GPIO.output(self.config['dmx_enable_pin'], GPIO.LOW)  # Enable output

            print(f"GPIO initialized - Data pin: {self.config['dmx_data_pin']}, Enable pin: {self.config['dmx_enable_pin']}")
        except Exception as e:
            print(f"Error initializing GPIO: {e}")
            # Don't fail completely - allow software to run without GPIO

    def send_dmx_packet(self):
        """Send complete DMX512 packet via GPIO"""
        try:
            data_pin = self.config['dmx_data_pin']

            # DMX512 timing (microseconds)
            # Break: 88μs minimum (we use 100μs)
            # Mark After Break: 8μs minimum (we use 12μs)
            # Bit time: 4μs per bit (250kbps)

            # Send BREAK (low for 100μs)
            GPIO.output(data_pin, GPIO.LOW)
            time.sleep(100e-6)  # 100 microseconds

            # Send MARK AFTER BREAK (high for 12μs)
            GPIO.output(data_pin, GPIO.HIGH)
            time.sleep(12e-6)  # 12 microseconds

            # Send data (start code + channels)
            for byte_value in self.dmx_data:
                self.send_dmx_byte(byte_value)

        except Exception as e:
            print(f"Error sending DMX packet: {e}")

    def send_dmx_byte(self, byte_value):
        """Send a single byte using DMX512 protocol timing"""
        try:
            data_pin = self.config['dmx_data_pin']
            bit_time = 4e-6  # 4 microseconds per bit (250kbps)

            # Start bit (always 0)
            GPIO.output(data_pin, GPIO.LOW)
            time.sleep(bit_time)

            # Data bits (LSB first)
            for i in range(8):
                bit = (byte_value >> i) & 1
                GPIO.output(data_pin, GPIO.HIGH if bit else GPIO.LOW)
                time.sleep(bit_time)

            # Stop bits (2 stop bits, both HIGH)
            GPIO.output(data_pin, GPIO.HIGH)
            time.sleep(bit_time * 2)  # 2 stop bits

        except Exception as e:
            print(f"Error sending DMX byte: {e}")

    def init_pygame(self):
        """Initialize pygame mixer for sound"""
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Error initializing pygame: {e}")

    def write_dmx(self, address, value):
        """Send DMX value to specified address"""
        clamped_value = min(255, max(0, int(value)))
        clamped_address = min(512, max(1, int(address)))

        # Log the action
        self.log_action('dmx', f"Channel {clamped_address} → {clamped_value}", {
            'address': clamped_address,
            'value': clamped_value
        })

        try:
            # Update DMX data array
            self.dmx_data[clamped_address] = clamped_value

            # Send complete DMX packet
            self.send_dmx_packet()

            print(f"DMX GPIO: Channel {clamped_address} = {clamped_value}")
        except Exception as e:
            error_msg = f"Error sending DMX via GPIO: {e}"
            print(error_msg)
            self.log_action('error', error_msg, {'address': clamped_address, 'value': clamped_value})

    def play_sound(self, sound_file, volume=1.0):
        """Play sound file with specified volume"""
        clamped_volume = min(1.0, max(0.0, volume))

        try:
            sound_path = os.path.join(self.config['sounds_directory'], sound_file)
            if not os.path.exists(sound_path):
                error_msg = f"Sound file not found: {sound_path}"
                print(error_msg)
                self.log_action('error', error_msg, {'file': sound_file, 'volume': clamped_volume})
                return

            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.set_volume(clamped_volume)
            pygame.mixer.music.play()

            # Log the action
            self.log_action('sound', f"Playing '{sound_file}' (vol: {clamped_volume:.1f})", {
                'file': sound_file,
                'volume': clamped_volume
            })
            print(f"Playing sound: {sound_file} at volume {clamped_volume}")

        except Exception as e:
            error_msg = f"Error playing sound: {e}"
            print(error_msg)
            self.log_action('error', error_msg, {'file': sound_file, 'volume': clamped_volume})

    def sleep(self, seconds):
        """Sleep for specified number of seconds"""
        if seconds > 0:
            # Log the action
            self.log_action('sleep', f"Waiting {seconds}s", {'duration': float(seconds)})
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
            self.log_action('sound', "Sound stopped", {})
        except Exception as e:
            error_msg = f"Error stopping sound: {e}"
            print(error_msg)
            self.log_action('error', error_msg, {})

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

            # Log sequence execution start
            sequence_name = os.path.basename(sequence_file).replace('.py', '')
            if self.loop_mode:
                self.loop_count += 1
                self.log_action('loop', f"Loop #{self.loop_count} started", {
                    'sequence': sequence_name,
                    'loop_number': self.loop_count
                })
            else:
                self.log_action('sequence', f"Executing '{sequence_name}'", {'sequence': sequence_name})

            # Execute the sequence
            exec(sequence_code, exec_globals)

            # Log sequence execution completion
            if self.loop_mode:
                self.log_action('loop', f"Loop #{self.loop_count} completed", {
                    'sequence': sequence_name,
                    'loop_number': self.loop_count
                })
            else:
                self.log_action('sequence', f"'{sequence_name}' completed", {'sequence': sequence_name})

        except Exception as e:
            error_msg = f"Error executing sequence: {e}"
            print(error_msg)
            self.log_action('error', error_msg, {'sequence': sequence_file})
            raise

    def run_sequence(self, sequence_file, loop=False):
        """Run sequence in a separate thread"""
        if self.running:
            print("Sequence already running")
            return False

        self.running = True
        self.loop_mode = loop
        self.loop_count = 0
        self.current_sequence_name = os.path.basename(sequence_file).replace('.py', '')

        # Log sequence start
        mode = "loop mode" if loop else "once"
        self.log_action('system', f"Starting '{self.current_sequence_name}' in {mode}", {
            'sequence': self.current_sequence_name,
            'mode': 'loop' if loop else 'once'
        })

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
                error_msg = f"Sequence execution error: {e}"
                print(error_msg)
                self.log_action('error', error_msg, {'sequence': self.current_sequence_name})
            finally:
                self.stop_sequence()

        self.current_thread = threading.Thread(target=sequence_thread)
        self.current_thread.daemon = True
        self.current_thread.start()
        return True

    def stop_sequence(self):
        """Stop currently running sequence"""
        if self.running:
            # Log sequence stop
            if self.current_sequence_name:
                if self.loop_mode and self.loop_count > 0:
                    self.log_action('system', f"Stopped '{self.current_sequence_name}' after {self.loop_count} loops", {
                        'sequence': self.current_sequence_name,
                        'loops_completed': self.loop_count
                    })
                else:
                    self.log_action('system', f"Stopped '{self.current_sequence_name}'", {
                        'sequence': self.current_sequence_name
                    })

            print("Stopping sequence")
            self.running = False
            self.stop_sound()

            if self.current_thread and self.current_thread.is_alive():
                self.current_thread.join(timeout=2.0)

            # Reset all DMX channels to 0
            try:
                # Reset DMX data array
                for i in range(1, 513):
                    self.dmx_data[i] = 0

                # Send the reset packet
                self.send_dmx_packet()

                self.log_action('dmx', f"Reset all DMX channels to 0", {'channels_reset': 512})
            except Exception as e:
                print(f"Error resetting DMX channels: {e}")

            # Turn off GPIO
            try:
                GPIO.output(self.config['control_pin'], False)
                self.log_action('system', "GPIO control pin turned off", {})
            except:
                pass

            # Reset state
            self.current_sequence_name = None
            self.loop_count = 0

        return True

    def is_running(self):
        """Check if sequence is currently running"""
        return self.running

    def get_status(self):
        """Get current status"""
        return {
            'running': self.running,
            'loop_mode': self.loop_mode,
            'sound_playing': pygame.mixer.music.get_busy() if pygame.mixer.get_init() else False,
            'current_sequence': self.current_sequence_name,
            'loop_count': self.loop_count if self.loop_mode else 0
        }

    def cleanup(self):
        """Clean up resources"""
        self.log_action('system', "Shutting down sequence executor", {})
        self.stop_sequence()

        try:
            GPIO.cleanup()
        except:
            pass

        # No serial connection to close in GPIO mode
        pass

        try:
            pygame.quit()
        except:
            pass

    def log_action(self, action_type, message, data=None):
        """Log an action for real-time feedback"""
        action = {
            'timestamp': datetime.now().isoformat(),
            'type': action_type,
            'message': message,
            'data': data or {}
        }

        self.action_log.append(action)
        print(f"[{action_type.upper()}] {message}")

    def get_recent_actions(self, limit=50):
        """Get recent actions for the webapp"""
        return list(self.action_log)[-limit:]

    def clear_action_log(self):
        """Clear the action log"""
        self.action_log.clear()
        self.log_action('system', "Action log cleared", {})

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
