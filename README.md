# ErntedankSequenzer

A web-based DMX and sound sequence controller for Raspberry Pi, designed for creating synchronized light and sound shows.

## Features

- **Web Interface**: Easy-to-use browser-based sequence editor
- **DMX Control**: Send commands to DMX lighting equipment via GPIO pins
- **Sound Playback**: Play audio files synchronized with lighting
- **Sequence Editor**: Built-in code editor with syntax validation
- **Real-time Control**: Start, stop, and monitor sequences remotely
- **Loop Mode**: Run sequences continuously or just once
- **Example Library**: Pre-built examples to get started quickly

## Hardware Requirements

- Raspberry Pi (3B+ or newer recommended)
- DMX interface (GPIO-based DMX output circuit)
- Audio output (built-in audio jack, USB audio interface, or HAT)
- GPIO pins for DMX data output and control

## Software Requirements

- Python 3.7 or newer
- Raspberry Pi OS (Raspbian) or compatible Linux distribution

## Installation

### Automated Installation (Recommended)

The easiest way to install ErntedankSequenzer is using the automated installer:

```bash
# Clone the repository
git clone <repository-url>
cd ErntedankSequenzer

# Run the automated installer
./install.sh
```

The installer will:
- Install system dependencies
- Set up Python virtual environment
- Configure user permissions (gpio, audio groups)
- Create systemd service for automatic startup
- Enable the service to start on boot

After installation, the web interface will be available at `http://your-pi-ip:5000`

### Manual Installation

If you prefer to install manually:

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-venv python3-dev python3-rpi.gpio alsa-utils pulseaudio

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Add user to required groups
sudo usermod -a -G gpio $USER
sudo usermod -a -G audio $USER

# Create directories
mkdir -p logs sequences sounds
```

### Hardware Setup

#### DMX Interface
The system uses GPIO pins to generate DMX512 protocol signals. You'll need a DMX output circuit connected to your Raspberry Pi.

**Required Hardware:**
- RS485/RS422 transceiver IC (e.g., SN75176, MAX485)
- DMX connector (3-pin or 5-pin XLR)
- Basic resistors and capacitors for signal conditioning

**GPIO Connections:**
- GPIO 18 (default): DMX data output
- GPIO 22 (default): DMX enable/disable
- Connect to your DMX interface circuit

**Basic Circuit:**
```
RPi GPIO 18 -----> RS485 Data Input (DI)
RPi GPIO 22 -----> RS485 Driver Enable (DE/RE)
RS485 A     -----> XLR Pin 3 (DMX+)  
RS485 B     -----> XLR Pin 2 (DMX-)
GND         -----> XLR Pin 1 (Ground)
```

- Update `config.json` with your specific GPIO pin assignments

#### Audio Setup
```bash
# Test audio output
speaker-test -t wav -c 2

# If using USB audio, you may need to set it as default
sudo nano /usr/share/alsa/alsa.conf
# Change defaults.pcm.card and defaults.ctl.card to your USB device number
```

### Service Management

If you used the automated installer, the service is managed with systemd:

```bash
# Check service status
sudo systemctl status erntedanksequenzer

# View logs
sudo journalctl -u erntedanksequenzer -f

# Restart service
sudo systemctl restart erntedanksequenzer

# Stop service
sudo systemctl stop erntedanksequenzer

# Disable auto-start
sudo systemctl disable erntedanksequenzer
```

Helper scripts are also created:
- `./service-status.sh` - Check service status
- `./service-restart.sh` - Restart service
- `./view-logs.sh` - View live logs
- `./service-stop.sh` - Stop service

### Uninstallation

To remove the service and clean up:

```bash
./uninstall.sh
```

### Configuration

Edit `config.json` to match your hardware setup:

```json
{
    "control_pin": 17,
    "dmx_data_pin": 18,
    "dmx_enable_pin": 22,
    "sounds_directory": "sounds",
    "web_host": "0.0.0.0",
    "web_port": 5000
}
```

### 5. Add Sound Files

Place your audio files in the `sounds/` directory. Supported formats:
- WAV (.wav)
- MP3 (.mp3)
- OGG (.ogg)
- FLAC (.flac)
- M4A (.m4a)

## Usage

### Accessing the Web Interface

If you used the automated installer, ErntedankSequenzer runs as a system service and starts automatically on boot.

**Access the web interface at:** `http://your-pi-ip:5000`

**Manual startup** (if not using the service):
```bash
# Activate virtual environment
source venv/bin/activate

# Start the web server
python3 run.py
```

### Service Status

Check if the service is running:
```bash
./service-status.sh
# or
sudo systemctl status erntedanksequenzer
```

### Command Line Usage (Development/Testing)

For testing and development, you can run sequences directly:
```bash
# Stop the service first (if running)
sudo systemctl stop erntedanksequenzer

# Activate virtual environment
source venv/bin/activate

# Run a specific sequence once
python3 run.py --cli --sequence my_sequence

# Run a sequence in loop mode
python3 run.py --cli --sequence my_sequence --loop

# Test DMX output
python3 run.py --cli --test-dmx

# Test sound playback
python3 run.py --cli --test-sound --sound-file test.wav

# Restart the service when done
sudo systemctl start erntedanksequenzer
```

## Creating Sequences

### Available Functions

#### DMX Control
```python
write_dmx(address, value)
# address: DMX channel (1-512)
# value: DMX value (0-255)

# Example
write_dmx(1, 255)  # Set channel 1 to full brightness
write_dmx(1, 0)    # Turn off channel 1
```

#### Sound Control
```python
play_sound(filename, volume=1.0)
# filename: Audio file in sounds directory
# volume: Volume level (0.0-1.0)

# Examples
play_sound('music.mp3')
play_sound('effect.wav', 0.7)  # 70% volume
```

#### Timing Functions
```python
sleep(seconds)
# seconds: Time to wait (float)

wait_for_sound()  # Wait for current sound to finish
stop_sound()      # Stop currently playing sound

# Examples
sleep(2.5)        # Wait 2.5 seconds
sleep(0.1)        # Wait 100ms
```

### Example Sequence

```python
# Simple light and sound show
play_sound('intro.mp3', 0.8)
write_dmx(1, 255)  # Turn on main light
sleep(1)

# Flash effect
for i in range(5):
    write_dmx(2, 255)  # Flash light on
    sleep(0.1)
    write_dmx(2, 0)    # Flash light off
    sleep(0.1)

wait_for_sound()   # Wait for intro to finish
write_dmx(1, 0)    # Turn off main light
```

## Web Interface

### Main Dashboard
- View all saved sequences
- Start/stop sequence execution
- Monitor current status
- Access quick examples

### Sequence Editor
- Syntax-highlighted code editor
- Real-time validation
- Function reference panel
- Save and run sequences directly

### Control Panel
- Start sequences in loop mode
- Run sequences once
- Stop all execution
- View detailed status

## Configuration

### config.json Options

```json
{
    "control_pin": 17,              // GPIO pin for additional control
    "dmx_data_pin": 18,             // GPIO pin for DMX data output
    "dmx_enable_pin": 22,           // GPIO pin for DMX enable/disable
    "sounds_directory": "sounds",   // Audio files directory
    "sequences_directory": "sequences", // Generated sequences directory
    "web_host": "0.0.0.0",         // Web server host (0.0.0.0 for all interfaces)
    "web_port": 5000,              // Web server port
    "web_debug": false,            // Enable Flask debug mode
    "dmx_channels": 512,           // Number of DMX channels
    "max_sequence_size": 1048576,  // Maximum sequence file size (bytes)
    "log_level": "INFO"            // Logging level
}
```

### Troubleshooting

### Service Issues

**Service won't start:**
- Check service status: `sudo systemctl status erntedanksequenzer`
- View detailed logs: `sudo journalctl -u erntedanksequenzer -f`
- Verify configuration: `cat config.json`
- Check file permissions in project directory

**Service starts but web interface not accessible:**
- Verify service is running: `./service-status.sh`
- Check if port is in use: `sudo netstat -tlnp | grep :5000`
- Verify firewall settings: `sudo ufw status`
- Check config.json for correct web_host and web_port

### Hardware Issues

**DMX not working:**
- Check GPIO permissions: `sudo usermod -a -G gpio $USER`
- Verify correct GPIO pins in config.json
- Test GPIO output with multimeter or oscilloscope
- Ensure DMX hardware interface is properly connected
- Reboot after adding user to gpio group

**Audio not playing:**
- Check audio device: `aplay -l`
- Test with: `speaker-test -c2`
- Verify volume levels: `alsamixer`
- Check if user is in audio group: `groups $USER`

**Permission errors:**
- Ensure user is in required groups: `groups $USER`
- Reboot after group changes take effect
- Check service runs as correct user: `sudo systemctl status erntedanksequenzer`

### Debug Mode

Enable debug logging by setting `log_level` to `DEBUG` in config.json. Logs are saved to `logs/sequenzer.log`.

### Service Installation

To run as a system service:

```bash
# Create service file
sudo nano /etc/systemd/system/sequenzer.service

# Add service configuration
[Unit]
Description=ErntedankSequenzer
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ErntedankSequenzer
Environment=PATH=/home/pi/ErntedankSequenzer/venv/bin
ExecStart=/home/pi/ErntedankSequenzer/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable sequenzer.service
sudo systemctl start sequenzer.service
```

## API Reference

### REST Endpoints

- `GET /api/sequences` - List all sequences
- `POST /api/save` - Save sequence
- `DELETE /api/sequences/<name>` - Delete sequence
- `GET /api/control/start/<name>` - Start sequence (loop)
- `GET /api/control/run/<name>` - Run sequence once
- `GET /api/control/stop` - Stop execution
- `GET /api/control/status` - Get current status
- `POST /api/validate` - Validate sequence code

## Development

### Project Structure

```
ErntedankSequenzer/
├── run.py                    # Main startup script
├── config.json              # Configuration file
├── requirements.txt         # Python dependencies
├── sequence_executor.py     # Sequence execution engine
├── sequence_generator.py    # Sequence code generation
├── sequenz.py              # Original sequence (legacy)
├── webapp/                 # Web application
│   ├── app.py              # Flask application
│   ├── templates/          # HTML templates
│   └── static/             # CSS, JS, images
├── sequences/              # Generated sequence files
├── sounds/                 # Audio files
└── logs/                   # Log files
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please check:
1. This README file
2. Log files in `logs/sequenzer.log`
3. GitHub issues page
4. Hardware documentation

## Version History

- **1.0.0** - Initial release with web interface and sequence editor
- Based on original sequenz.py DMX and sound control system