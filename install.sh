#!/bin/bash

# ErntedankSequenzer Installation Script
# This script sets up ErntedankSequenzer as a systemd service for automatic startup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="erntedanksequenzer"
SERVICE_USER="$(whoami)"
INSTALL_DIR="$SCRIPT_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}[INSTALL]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root!"
        print_error "Run it as the user who will operate the system."
        print_error "The script will use sudo when needed."
        exit 1
    fi
}

# Banner
print_banner() {
    echo -e "${PURPLE}"
    echo "=============================================================="
    echo "    ErntedankSequenzer - Installation Script"
    echo "    DMX & Sound Sequence Controller Setup"
    echo "=============================================================="
    echo -e "${NC}"
}

# Check if we're on a Raspberry Pi
check_platform() {
    print_status "Checking platform..."

    if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model; then
        print_success "Running on Raspberry Pi"
        PLATFORM="raspberry-pi"
    else
        print_warning "Not running on Raspberry Pi - GPIO features may not work"
        PLATFORM="generic-linux"
    fi
}

# Check system requirements
check_requirements() {
    print_status "Checking system requirements..."

    # Check if systemd is available
    if ! command -v systemctl &> /dev/null; then
        print_error "systemctl not found. This script requires systemd."
        exit 1
    fi

    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        print_error "Install with: sudo apt update && sudo apt install python3 python3-pip python3-venv"
        exit 1
    fi

    # Check if we have pip
    if ! python3 -m pip --version &> /dev/null; then
        print_warning "pip not available, installing..."
        sudo apt update
        sudo apt install -y python3-pip
    fi

    print_success "System requirements check passed"
}

# Install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."

    # Update package list
    sudo apt update

    # Install required system packages
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        alsa-utils \
        pulseaudio \
        pulseaudio-utils

    # Install GPIO libraries if on Raspberry Pi
    if [[ "$PLATFORM" == "raspberry-pi" ]]; then
        print_status "Installing Raspberry Pi specific packages..."
        sudo apt install -y \
            python3-rpi.gpio \
            rpi.gpio-common \
            raspi-gpio
    fi

    print_success "System dependencies installed"
}

# Set up user permissions
setup_permissions() {
    print_status "Setting up user permissions..."

    # Add user to necessary groups
    if [[ "$PLATFORM" == "raspberry-pi" ]]; then
        sudo usermod -a -G gpio "$SERVICE_USER" 2>/dev/null || true
        print_status "Added $SERVICE_USER to gpio group"
    fi

    sudo usermod -a -G audio "$SERVICE_USER" 2>/dev/null || true
    print_status "Added $SERVICE_USER to audio group"

    # Create udev rules for GPIO access (if needed)
    if [[ "$PLATFORM" == "raspberry-pi" ]]; then
        sudo tee /etc/udev/rules.d/99-gpio.rules > /dev/null << 'EOF'
# GPIO permissions for ErntedankSequenzer
KERNEL=="gpiochip*", GROUP="gpio", MODE="0664"
SUBSYSTEM=="gpio", GROUP="gpio", MODE="0664"
EOF
        print_status "Created GPIO udev rules"
    fi

    print_success "User permissions configured"
}

# Install Python dependencies
install_python_deps() {
    print_status "Setting up Python virtual environment..."

    cd "$INSTALL_DIR"

    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        print_status "Created virtual environment"
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install requirements
    if [[ -f "requirements.txt" ]]; then
        print_status "Installing Python dependencies..."
        pip install -r requirements.txt

        # Mark requirements as installed
        touch venv/requirements_installed.flag

        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping Python dependencies"
    fi

    deactivate
}

# Create systemd service file
create_service() {
    print_status "Creating systemd service..."

    # Create service file
    sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << EOF
[Unit]
Description=ErntedankSequenzer - DMX & Sound Sequence Controller
Documentation=https://github.com/user/ErntedankSequenzer
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
Environment=PYTHONUNBUFFERED=1
ExecStartPre=/bin/sleep 10
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run.py
ExecReload=/bin/kill -HUP \$MAINPID
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$INSTALL_DIR
ReadWritePaths=/tmp

# Resource limits
LimitNOFILE=65536
MemoryMax=512M

[Install]
WantedBy=multi-user.target
EOF

    print_success "Systemd service created: /etc/systemd/system/${SERVICE_NAME}.service"
}

# Create configuration directory and files
setup_config() {
    print_status "Setting up configuration..."

    cd "$INSTALL_DIR"

    # Create necessary directories
    mkdir -p logs sequences sounds

    # Set proper permissions
    chmod 755 logs sequences sounds

    # Create default config if it doesn't exist
    if [[ ! -f "config.json" ]]; then
        print_status "Creating default configuration..."
        cat > config.json << 'EOF'
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
    "auto_stop_on_error": true,
    "max_sequence_size": 1048576,
    "validation_timeout": 30,
    "sound_formats": [".wav", ".mp3", ".ogg", ".flac", ".m4a"],
    "gpio_cleanup_on_exit": true,
    "status_update_interval": 1.0,
    "sequence_execution_timeout": 3600,
    "log_level": "INFO",
    "enable_web_logging": true
}
EOF
        print_success "Default configuration created"
    else
        print_success "Configuration file already exists"
    fi

    # Make start script executable
    if [[ -f "start.sh" ]]; then
        chmod +x start.sh
    fi
}

# Enable and start service
enable_service() {
    print_status "Enabling and starting service..."

    # Reload systemd
    sudo systemctl daemon-reload

    # Enable service for automatic startup
    sudo systemctl enable "$SERVICE_NAME"

    # Start the service
    sudo systemctl start "$SERVICE_NAME"

    # Wait a moment for service to start
    sleep 3

    # Check service status
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service started successfully"
    else
        print_warning "Service may have failed to start, checking status..."
        sudo systemctl status "$SERVICE_NAME" --no-pager -l
    fi
}

# Create helper scripts
create_helpers() {
    print_status "Creating helper scripts..."

    # Create status script
    cat > "$INSTALL_DIR/service-status.sh" << 'EOF'
#!/bin/bash
echo "=== ErntedankSequenzer Service Status ==="
sudo systemctl status erntedanksequenzer --no-pager -l
echo ""
echo "=== Recent Logs ==="
sudo journalctl -u erntedanksequenzer -n 20 --no-pager
EOF
    chmod +x "$INSTALL_DIR/service-status.sh"

    # Create restart script
    cat > "$INSTALL_DIR/service-restart.sh" << 'EOF'
#!/bin/bash
echo "Restarting ErntedankSequenzer service..."
sudo systemctl restart erntedanksequenzer
sleep 3
sudo systemctl status erntedanksequenzer --no-pager -l
EOF
    chmod +x "$INSTALL_DIR/service-restart.sh"

    # Create stop script
    cat > "$INSTALL_DIR/service-stop.sh" << 'EOF'
#!/bin/bash
echo "Stopping ErntedankSequenzer service..."
sudo systemctl stop erntedanksequenzer
sudo systemctl status erntedanksequenzer --no-pager -l
EOF
    chmod +x "$INSTALL_DIR/service-stop.sh"

    # Create logs viewer script
    cat > "$INSTALL_DIR/view-logs.sh" << 'EOF'
#!/bin/bash
echo "=== ErntedankSequenzer Logs ==="
echo "Press Ctrl+C to exit"
echo ""
sudo journalctl -u erntedanksequenzer -f
EOF
    chmod +x "$INSTALL_DIR/view-logs.sh"

    print_success "Helper scripts created"
}

# Final setup and information
final_setup() {
    print_status "Performing final setup..."

    # Get IP address
    IP_ADDRESS=$(hostname -I | awk '{print $1}' | head -1)
    WEB_PORT=$(grep -o '"web_port": *[0-9]*' config.json 2>/dev/null | grep -o '[0-9]*' || echo "5000")

    print_success "Installation completed successfully!"
    echo ""
    echo -e "${GREEN}=== Installation Summary ===${NC}"
    echo -e "Service Name: ${BLUE}$SERVICE_NAME${NC}"
    echo -e "Install Directory: ${BLUE}$INSTALL_DIR${NC}"
    echo -e "Service User: ${BLUE}$SERVICE_USER${NC}"
    echo -e "Platform: ${BLUE}$PLATFORM${NC}"
    echo ""
    echo -e "${GREEN}=== Access Information ===${NC}"
    if [[ -n "$IP_ADDRESS" ]]; then
        echo -e "Web Interface: ${BLUE}http://$IP_ADDRESS:$WEB_PORT${NC}"
        echo -e "Local Access: ${BLUE}http://localhost:$WEB_PORT${NC}"
    else
        echo -e "Web Interface: ${BLUE}http://localhost:$WEB_PORT${NC}"
    fi
    echo ""
    echo -e "${GREEN}=== Service Management ===${NC}"
    echo -e "Check status: ${BLUE}sudo systemctl status $SERVICE_NAME${NC}"
    echo -e "View logs: ${BLUE}sudo journalctl -u $SERVICE_NAME -f${NC}"
    echo -e "Restart: ${BLUE}sudo systemctl restart $SERVICE_NAME${NC}"
    echo -e "Stop: ${BLUE}sudo systemctl stop $SERVICE_NAME${NC}"
    echo -e "Disable: ${BLUE}sudo systemctl disable $SERVICE_NAME${NC}"
    echo ""
    echo -e "${GREEN}=== Helper Scripts ===${NC}"
    echo -e "Status: ${BLUE}./service-status.sh${NC}"
    echo -e "Restart: ${BLUE}./service-restart.sh${NC}"
    echo -e "Stop: ${BLUE}./service-stop.sh${NC}"
    echo -e "View Logs: ${BLUE}./view-logs.sh${NC}"
    echo ""
    echo -e "${YELLOW}=== Next Steps ===${NC}"
    echo "1. The service is now running and will start automatically on boot"
    echo "2. Access the web interface using the URL above"
    echo "3. Upload sound files and create sequences"
    echo "4. Check GPIO connections for DMX output"
    if [[ "$PLATFORM" == "raspberry-pi" ]]; then
        echo "5. Reboot to ensure all group permissions are active: sudo reboot"
    fi
    echo ""
    print_warning "If you made changes to user groups, you may need to log out and back in"
    print_warning "or reboot for the changes to take full effect."
}

# Cleanup function for errors
cleanup() {
    print_error "Installation failed or was interrupted"
    print_status "Cleaning up..."

    # Remove service file if it was created
    if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        sudo rm "/etc/systemd/system/${SERVICE_NAME}.service"
        sudo systemctl daemon-reload
        print_status "Removed service file"
    fi

    exit 1
}

# Main installation function
main() {
    print_banner

    # Set up error handling
    trap cleanup ERR

    print_header "Starting ErntedankSequenzer installation..."

    check_root
    check_platform
    check_requirements
    install_system_deps
    setup_permissions
    install_python_deps
    setup_config
    create_service
    create_helpers
    enable_service
    final_setup

    print_success "Installation completed successfully! 🎉"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --uninstall)
            print_header "Uninstalling ErntedankSequenzer service..."
            sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
            sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
            sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
            sudo systemctl daemon-reload
            print_success "Service uninstalled"
            exit 0
            ;;
        --help|-h)
            echo "ErntedankSequenzer Installation Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --uninstall    Remove the systemd service"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "This script will:"
            echo "  1. Install system dependencies"
            echo "  2. Set up Python virtual environment"
            echo "  3. Configure user permissions"
            echo "  4. Create systemd service for automatic startup"
            echo "  5. Enable and start the service"
            echo ""
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
    shift
done

# Run main installation
main
