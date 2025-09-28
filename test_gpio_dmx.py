#!/usr/bin/env python3
"""
GPIO DMX Test Script
Test script to verify GPIO-based DMX512 output functionality
Run this on a Raspberry Pi to test the DMX implementation
"""

import sys
import time
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("Warning: RPi.GPIO not available - running in simulation mode")
    GPIO_AVAILABLE = False

def simulate_gpio_output(pin, state):
    """Simulate GPIO output for non-Pi environments"""
    state_str = "HIGH" if state else "LOW"
    print(f"  GPIO {pin} -> {state_str}")

class GPIODMXTester:
    def __init__(self, data_pin=18, enable_pin=22):
        self.data_pin = data_pin
        self.enable_pin = enable_pin
        self.gpio_available = GPIO_AVAILABLE

        if self.gpio_available:
            self.init_gpio()
        else:
            print("Running in GPIO simulation mode")

    def init_gpio(self):
        """Initialize GPIO pins for DMX output"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.data_pin, GPIO.OUT)
            GPIO.setup(self.enable_pin, GPIO.OUT)

            # Initialize pins (DMX idle state)
            GPIO.output(self.data_pin, GPIO.HIGH)
            GPIO.output(self.enable_pin, GPIO.LOW)

            print(f"GPIO initialized - Data: GPIO{self.data_pin}, Enable: GPIO{self.enable_pin}")
        except Exception as e:
            print(f"Error initializing GPIO: {e}")
            self.gpio_available = False

    def gpio_output(self, pin, state):
        """Set GPIO output state (real or simulated)"""
        if self.gpio_available:
            GPIO.output(pin, state)
        else:
            simulate_gpio_output(pin, state)

    def send_dmx_byte(self, byte_value, verbose=False):
        """Send a single byte using DMX512 protocol timing"""
        bit_time = 4e-6  # 4 microseconds per bit (250kbps)

        if verbose:
            print(f"    Sending byte: 0x{byte_value:02X} ({byte_value})")

        # Start bit (always 0)
        self.gpio_output(self.data_pin, GPIO.LOW if self.gpio_available else False)
        if not self.gpio_available:
            time.sleep(0.001)  # Longer delay for simulation
        else:
            time.sleep(bit_time)

        # Data bits (LSB first)
        for i in range(8):
            bit = (byte_value >> i) & 1
            state = GPIO.HIGH if bit else GPIO.LOW if self.gpio_available else bool(bit)
            self.gpio_output(self.data_pin, state)

            if not self.gpio_available:
                time.sleep(0.001)
            else:
                time.sleep(bit_time)

        # Stop bits (2 stop bits, both HIGH)
        self.gpio_output(self.data_pin, GPIO.HIGH if self.gpio_available else True)
        if not self.gpio_available:
            time.sleep(0.002)  # 2 stop bits
        else:
            time.sleep(bit_time * 2)

    def send_dmx_packet(self, dmx_data, verbose=False):
        """Send complete DMX512 packet"""
        if verbose:
            print(f"  Sending DMX packet with {len(dmx_data)} bytes")

        # Enable DMX output
        self.gpio_output(self.enable_pin, GPIO.LOW if self.gpio_available else False)

        # Send BREAK (low for 100μs)
        self.gpio_output(self.data_pin, GPIO.LOW if self.gpio_available else False)
        if not self.gpio_available:
            time.sleep(0.01)  # Longer delay for simulation
        else:
            time.sleep(100e-6)

        # Send MARK AFTER BREAK (high for 12μs)
        self.gpio_output(self.data_pin, GPIO.HIGH if self.gpio_available else True)
        if not self.gpio_available:
            time.sleep(0.005)
        else:
            time.sleep(12e-6)

        # Send data bytes
        for i, byte_val in enumerate(dmx_data):
            if verbose and i < 10:  # Show first 10 bytes in verbose mode
                self.send_dmx_byte(byte_val, verbose=True)
            else:
                self.send_dmx_byte(byte_val, verbose=False)

    def test_basic_output(self):
        """Test basic DMX output functionality"""
        print("\n=== Basic DMX Output Test ===")

        # Create simple test packet: start code + 5 channels
        dmx_data = [0, 255, 128, 64, 32, 16]  # Start code + 5 channels

        print(f"Testing with {len(dmx_data)} bytes:")
        for i, val in enumerate(dmx_data):
            if i == 0:
                print(f"  Start Code: {val}")
            else:
                print(f"  Channel {i}: {val}")

        self.send_dmx_packet(dmx_data, verbose=True)
        print("Basic test completed")

    def test_channel_sweep(self):
        """Test sweeping through multiple channels"""
        print("\n=== Channel Sweep Test ===")

        num_channels = 16
        dmx_data = [0] + [0] * 512  # Start code + 512 channels

        for channel in range(1, num_channels + 1):
            print(f"Testing channel {channel}")

            # Clear all channels
            for i in range(1, 513):
                dmx_data[i] = 0

            # Set current channel to full brightness
            dmx_data[channel] = 255

            self.send_dmx_packet(dmx_data[:channel + 1])
            time.sleep(0.5)

        print("Channel sweep completed")

    def test_fade_effect(self):
        """Test fade effect on channel 1"""
        print("\n=== Fade Effect Test ===")

        dmx_data = [0] + [0] * 512

        # Fade in
        print("Fading in channel 1...")
        for brightness in range(0, 256, 16):
            dmx_data[1] = brightness
            print(f"  Channel 1: {brightness}")
            self.send_dmx_packet(dmx_data[:2])
            time.sleep(0.1)

        time.sleep(0.5)

        # Fade out
        print("Fading out channel 1...")
        for brightness in range(255, -1, -16):
            dmx_data[1] = max(0, brightness)
            print(f"  Channel 1: {max(0, brightness)}")
            self.send_dmx_packet(dmx_data[:2])
            time.sleep(0.1)

        print("Fade test completed")

    def test_timing_accuracy(self):
        """Test timing accuracy of DMX output"""
        print("\n=== Timing Accuracy Test ===")

        dmx_data = [0, 255]  # Start code + 1 channel

        print("Sending 10 packets and measuring timing...")
        start_time = time.time()

        for i in range(10):
            print(f"  Packet {i+1}/10")
            self.send_dmx_packet(dmx_data)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 10

        print(f"Total time: {total_time:.3f} seconds")
        print(f"Average time per packet: {avg_time:.3f} seconds")
        print(f"Theoretical minimum (2 bytes): ~0.0009 seconds")

        if not self.gpio_available:
            print("Note: Timing measurements are not accurate in simulation mode")

    def cleanup(self):
        """Clean up GPIO resources"""
        if self.gpio_available:
            try:
                GPIO.cleanup()
                print("GPIO cleanup completed")
            except:
                pass
        else:
            print("GPIO cleanup (simulated)")

def main():
    parser = argparse.ArgumentParser(description='Test GPIO-based DMX512 output')
    parser.add_argument('--data-pin', type=int, default=18, help='GPIO pin for DMX data (default: 18)')
    parser.add_argument('--enable-pin', type=int, default=22, help='GPIO pin for DMX enable (default: 22)')
    parser.add_argument('--test', choices=['basic', 'sweep', 'fade', 'timing', 'all'],
                       default='all', help='Which test to run (default: all)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    print("GPIO DMX Test Script")
    print("===================")
    print(f"Data Pin: GPIO {args.data_pin}")
    print(f"Enable Pin: GPIO {args.enable_pin}")

    if not GPIO_AVAILABLE:
        print("\n⚠️  WARNING: Running in simulation mode")
        print("    Install RPi.GPIO and run on Raspberry Pi for real GPIO testing")

    tester = GPIODMXTester(args.data_pin, args.enable_pin)

    try:
        if args.test == 'basic' or args.test == 'all':
            tester.test_basic_output()

        if args.test == 'sweep' or args.test == 'all':
            tester.test_channel_sweep()

        if args.test == 'fade' or args.test == 'all':
            tester.test_fade_effect()

        if args.test == 'timing' or args.test == 'all':
            tester.test_timing_accuracy()

        print("\n✅ All tests completed successfully!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
    finally:
        tester.cleanup()

if __name__ == '__main__':
    main()
