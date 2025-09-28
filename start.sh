#!/bin/bash

# ErntedankSequenzer Startup Script
# This script starts the web-based sequence controller

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Banner
echo -e "${BLUE}"
echo "=================================================="
echo "    ErntedankSequenzer - Startup Script"
echo "    DMX & Sound Sequence Controller"
echo "=================================================="
echo -e "${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Check if requirements are installed
if [ ! -f "venv/requirements_installed.flag" ]; then
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        touch venv/requirements_installed.flag
        print_success "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
else
    print_status "Dependencies already installed"
fi

# Check if config file exists
if [ ! -f "config.json" ]; then
    print_warning "config.json not found, using defaults"
fi

# Create necessary directories
print_status "Creating directories..."
mkdir -p sequences sounds logs webapp/static/uploads

# Check hardware permissions
print_status "Checking hardware permissions..."

# Check serial port access
if [ -c "/dev/ttyUSB0" ] || [ -c "/dev/ttyACM0" ]; then
    if ! groups $USER | grep -q dialout; then
        print_warning "User not in dialout group. DMX may not work."
        print_warning "Run: sudo usermod -a -G dialout \$USER"
        print_warning "Then log out and back in."
    fi
else
    print_warning "No DMX serial device found at /dev/ttyUSB0 or /dev/ttyACM0"
fi

# Check GPIO access
if ! groups $USER | grep -q gpio; then
    print_warning "User not in gpio group. GPIO control may not work."
    print_warning "Run: sudo usermod -a -G gpio \$USER"
fi

# Get network information
IP_ADDRESS=$(hostname -I | awk '{print $1}')
if [ -n "$IP_ADDRESS" ]; then
    PORT=$(grep -o '"web_port": *[0-9]*' config.json 2>/dev/null | grep -o '[0-9]*' || echo "5000")
    print_success "Server will be available at: http://$IP_ADDRESS:$PORT"
    print_success "Local access: http://localhost:$PORT"
else
    print_warning "Could not determine IP address"
fi

# Parse command line arguments
CLI_MODE=false
SEQUENCE=""
LOOP_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --cli)
            CLI_MODE=true
            shift
            ;;
        --sequence|-s)
            SEQUENCE="$2"
            CLI_MODE=true
            shift 2
            ;;
        --loop|-l)
            LOOP_MODE=true
            shift
            ;;
        --test-dmx)
            CLI_MODE=true
            TEST_DMX=true
            shift
            ;;
        --test-sound)
            CLI_MODE=true
            TEST_SOUND=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cli                Run in command-line mode"
            echo "  --sequence, -s NAME  Run specific sequence"
            echo "  --loop, -l          Run in loop mode"
            echo "  --test-dmx          Test DMX output"
            echo "  --test-sound        Test sound system"
            echo "  --help, -h          Show this help"
            echo ""
            echo "Web mode (default):"
            echo "  $0"
            echo ""
            echo "CLI examples:"
            echo "  $0 --cli --sequence my_sequence"
            echo "  $0 --cli --sequence my_sequence --loop"
            echo "  $0 --cli --test-dmx"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build command
CMD="python3 run.py"

if [ "$CLI_MODE" = true ]; then
    CMD="$CMD --cli"

    if [ -n "$SEQUENCE" ]; then
        CMD="$CMD --sequence $SEQUENCE"
    fi

    if [ "$LOOP_MODE" = true ]; then
        CMD="$CMD --loop"
    fi

    if [ "$TEST_DMX" = true ]; then
        CMD="$CMD --test-dmx"
    fi

    if [ "$TEST_SOUND" = true ]; then
        CMD="$CMD --test-sound"
    fi
fi

print_status "Starting ErntedankSequenzer..."
print_status "Command: $CMD"
print_status "Press Ctrl+C to stop"
echo ""

# Handle cleanup on exit
cleanup() {
    print_status "Shutting down gracefully..."
    exit 0
}
trap cleanup INT TERM

# Start the application
exec $CMD
