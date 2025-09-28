# ErntedankSequenzer Installation Guide

This guide provides step-by-step instructions for installing ErntedankSequenzer on your Raspberry Pi.

## Quick Start

For most users, the automated installation is recommended:

```bash
git clone <your-repository-url>
cd ErntedankSequenzer
./install.sh
```

The system will be accessible at `http://your-pi-ip:5000` after installation completes.

## System Requirements

### Hardware
- **Raspberry Pi 3B+ or newer** (recommended)
- **SD card**: 16GB or larger, Class 10 or better
- **Audio output**: Built-in 3.5mm jack, USB audio, or HAT
- **DMX hardware**: GPIO-based DMX interface circuit
- **Network connection**: Ethernet or WiFi

### Software
- **Raspberry Pi OS** (Raspbian) - Lite or Desktop version
- **Python 3.7+** (usually pre-installed)
- **Internet connection** for downloading dependencies

## Pre-Installation Setup

### 1. Prepare Raspberry Pi OS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Enable SSH (if using headless setup)
sudo systemctl enable ssh
sudo systemctl start ssh
```

### 2. Configure Audio (if needed)

```bash
# Test audio output
speaker-test -t wav -c 2

# For USB audio devices, check available devices
aplay -l

# Set USB audio as default (if needed)
sudo nano /usr/share/alsa/alsa.conf
# Edit: defaults.pcm.card 1 (replace 0 with your USB device number)
```

### 3. Enable GPIO and Hardware Interfaces

```bash
# Run raspi-config
sudo raspi-config

# Navigate to:
# 3 Interface Options → Enable what you need
# 5 Advanced Options → Expand Filesystem (if needed)

# Reboot
sudo reboot
```

## Installation Methods

### Method 1: Automated Installation (Recommended)

1. **Clone the repository:**
```bash
git clone <your-repository-url>
cd ErntedankSequenzer
```

2. **Run the installer:**
```bash
./install.sh
```

3. **Wait for completion** - The installer will:
   - Install system dependencies
   - Create Python virtual environment
   - Set up user permissions
   - Create systemd service
   - Start the service automatically

4. **Access the web interface:**
   - Open browser to `http://your-pi-ip:5000`
   - Or `http://localhost:5000` if browsing from the Pi

### Method 2: Manual Installation

If you prefer manual control or need to troubleshoot:

```bash
# 1. Clone repository
git clone <your-repository-url>
cd ErntedankSequenzer

# 2. Install system dependencies
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-rpi.gpio \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Set up permissions
sudo usermod -a -G gpio $USER
sudo usermod -a -G audio $USER

# 6. Create directories
mkdir -p logs sequences sounds

# 7. Log out and back in (for group changes)
# or reboot: sudo reboot

# 8. Test the application
python3 run.py
```

## Hardware Setup

### DMX Interface Circuit

You need to build a simple DMX interface using an RS485 transceiver:

**Required Components:**
- RS485/RS422 transceiver IC (SN75176, MAX485, or similar)
- 3-pin or 5-pin XLR connector (female)
- 120Ω termination resistor
- Small breadboard or PCB
- Jumper wires

**Connections:**
```
Raspberry Pi → RS485 IC → XLR Connector
GPIO 18     → DI (Data Input)
GPIO 22     → DE/RE (Driver Enable)
3.3V        → VCC
GND         → GND
            → A → XLR Pin 3 (DMX+)
            → B → XLR Pin 2 (DMX-)
            → GND → XLR Pin 1 (Ground)
```

**Notes:**
- Add 120Ω resistor between A and B if this is the last device in chain
- Use twisted pair cable for DMX connections
- Keep cable lengths under 1000m total

### GPIO Pin Configuration

Default pin assignments (configurable in `config.json`):

```json
{
    "control_pin": 17,      // General control pin
    "dmx_data_pin": 18,     // DMX data output
    "dmx_enable_pin": 22    // DMX enable/disable
}
```

**Pin Usage Warning:** Make sure these pins aren't used by other HATs or devices.

## Configuration

### Basic Configuration

Edit `config.json` after installation:

```json
{
    "control_pin": 17,
    "dmx_data_pin": 18,
    "dmx_enable_pin": 22,
    "sounds_directory": "sounds",
    "sequences_directory": "sequences",
    "web_host": "0.0.0.0",
    "web_port": 5000,
    "web_debug": false,
    "dmx_channels": 512,
    "sound_formats": [".wav", ".mp3", ".ogg", ".flac", ".m4a"],
    "log_level": "INFO"
}
```

### Network Configuration

**Local Network Access:**
- Default: Accessible from any device on local network
- Web interface: `http://raspberry-pi-ip:5000`

**Security Considerations:**
- Change default port if needed: `"web_port": 8080`
- Restrict access: `"web_host": "127.0.0.1"` (localhost only)
- Use firewall: `sudo ufw allow 5000`

## Service Management

### Service Commands

```bash
# Check status
sudo systemctl status erntedanksequenzer

# Start service
sudo systemctl start erntedanksequenzer

# Stop service  
sudo systemctl stop erntedanksequenzer

# Restart service
sudo systemctl restart erntedanksequenzer

# Enable auto-start (on boot)
sudo systemctl enable erntedanksequenzer

# Disable auto-start
sudo systemctl disable erntedanksequenzer

# View logs
sudo journalctl -u erntedanksequenzer -f
```

### Helper Scripts

The installer creates convenient scripts:

```bash
./service-status.sh     # Check service status
./service-restart.sh    # Restart service
./service-stop.sh       # Stop service
./view-logs.sh          # View live logs
```

## Testing Installation

### 1. Test GPIO DMX Output

```bash
# Test GPIO DMX functionality
python3 test_gpio_dmx.py --test basic
```

### 2. Test Web Interface

1. Open browser to `http://your-pi-ip:5000`
2. You should see the ErntedankSequenzer interface
3. Try creating a simple sequence:
   ```python
   write_dmx(1, 255)  # Turn on channel 1
   sleep(2)           # Wait 2 seconds  
   write_dmx(1, 0)    # Turn off channel 1
   ```

### 3. Test Sound System

1. Upload a sound file through web interface
2. Create sequence with sound:
   ```python
   play_sound('test.wav')
   wait_for_sound()
   ```

## Troubleshooting

### Service Won't Start

```bash
# Check detailed status
sudo systemctl status erntedanksequenzer -l

# Check logs for errors
sudo journalctl -u erntedanksequenzer -n 50

# Common fixes:
sudo systemctl daemon-reload
sudo systemctl restart erntedanksequenzer
```

### Permission Errors

```bash
# Verify user groups
groups $USER

# Should include: gpio, audio

# If missing, add and reboot:
sudo usermod -a -G gpio,audio $USER
sudo reboot
```

### DMX Not Working

```bash
# Test GPIO access
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO OK')"

# Check pin configuration in config.json
cat config.json | grep -E "(dmx_|gpio)"

# Test with multimeter on GPIO pins during sequence execution
```

### Audio Issues

```bash
# Check audio devices
aplay -l

# Test audio output
speaker-test -c2

# Check volume levels
alsamixer

# Verify user in audio group
groups $USER | grep audio
```

### Web Interface Issues

```bash
# Check if service is running
sudo systemctl is-active erntedanksequenzer

# Check port availability
sudo netstat -tlnp | grep :5000

# Check firewall
sudo ufw status

# Try local access
curl http://localhost:5000
```

## Uninstallation

To completely remove ErntedankSequenzer:

```bash
./uninstall.sh
```

The uninstaller will:
- Stop and disable the service
- Remove service files
- Optionally remove application data
- Clean up system packages (optional)
- Preserve sequences and sound files

## Advanced Configuration

### Custom GPIO Pins

If you need different GPIO pins, edit `config.json`:

```json
{
    "dmx_data_pin": 20,    // Change from default 18
    "dmx_enable_pin": 21   // Change from default 22  
}
```

Then restart the service:
```bash
sudo systemctl restart erntedanksequenzer
```

### Performance Tuning

For better performance with complex sequences:

```json
{
    "status_update_interval": 0.5,  // Faster status updates
    "validation_timeout": 60,       // Longer validation timeout
    "log_level": "WARNING"          // Reduce logging
}
```

### Multiple Instances

To run multiple instances (different ports):

1. Copy the entire directory
2. Change `web_port` in config.json
3. Create separate service with different name
4. Install with custom service name

## Support

### Log Files

Check these locations for troubleshooting:

- **Service logs**: `sudo journalctl -u erntedanksequenzer`
- **Application logs**: `logs/sequenzer.log`
- **Web server logs**: `logs/webapp.log`

### Common Log Messages

- `"GPIO initialized"` - Hardware setup successful
- `"DMX GPIO: Channel X = Y"` - DMX output working
- `"Playing sound: file.wav"` - Audio system working
- `"Sequence validation passed"` - Code syntax correct

### Getting Help

1. Check logs for error messages
2. Verify hardware connections
3. Test individual components (GPIO, audio, network)
4. Check system resources (`htop`, `df -h`)
5. Review configuration files

---

**Installation Complete!** 🎉

Your ErntedankSequenzer should now be running and accessible via web browser. Start by uploading some sound files and creating your first sequence!