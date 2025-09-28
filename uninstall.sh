#!/bin/bash

# ErntedankSequenzer Uninstall Script
# This script removes ErntedankSequenzer systemd service and cleans up installation

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
    echo -e "${PURPLE}[UNINSTALL]${NC} $1"
}

# Banner
print_banner() {
    echo -e "${PURPLE}"
    echo "=============================================================="
    echo "    ErntedankSequenzer - Uninstall Script"
    echo "    DMX & Sound Sequence Controller Removal"
    echo "=============================================================="
    echo -e "${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root!"
        print_error "Run it as the same user who installed the service."
        print_error "The script will use sudo when needed."
        exit 1
    fi
}

# Stop and disable service
remove_service() {
    print_status "Removing systemd service..."

    # Stop the service if it's running
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "Stopping $SERVICE_NAME service..."
        sudo systemctl stop "$SERVICE_NAME"
    fi

    # Disable the service
    if sudo systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        print_status "Disabling $SERVICE_NAME service..."
        sudo systemctl disable "$SERVICE_NAME"
    fi

    # Remove service file
    if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
        print_status "Removing service file..."
        sudo rm "/etc/systemd/system/${SERVICE_NAME}.service"
        sudo systemctl daemon-reload
        print_success "Service file removed"
    else
        print_warning "Service file not found"
    fi

    print_success "Service removed successfully"
}

# Remove udev rules
remove_udev_rules() {
    print_status "Removing udev rules..."

    if [[ -f "/etc/udev/rules.d/99-gpio.rules" ]]; then
        sudo rm "/etc/udev/rules.d/99-gpio.rules"
        print_success "GPIO udev rules removed"
    else
        print_status "No GPIO udev rules found"
    fi
}

# Clean up helper scripts
cleanup_helpers() {
    print_status "Removing helper scripts..."

    cd "$SCRIPT_DIR"

    local scripts=(
        "service-status.sh"
        "service-restart.sh"
        "service-stop.sh"
        "view-logs.sh"
    )

    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            rm "$script"
            print_status "Removed $script"
        fi
    done
}

# Ask about data removal
ask_remove_data() {
    echo ""
    print_warning "Do you want to remove application data?"
    echo "This will delete:"
    echo "  - Virtual environment (venv/)"
    echo "  - Log files (logs/)"
    echo "  - Configuration file (config.json)"
    echo ""
    echo "Note: Sound files and sequences will be preserved"
    echo ""
    read -p "Remove application data? [y/N]: " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Removing application data..."

        # Remove virtual environment
        if [[ -d "venv" ]]; then
            rm -rf "venv"
            print_status "Virtual environment removed"
        fi

        # Remove logs
        if [[ -d "logs" ]]; then
            rm -rf "logs"
            print_status "Log files removed"
        fi

        # Ask about config file
        if [[ -f "config.json" ]]; then
            read -p "Remove configuration file (config.json)? [y/N]: " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm "config.json"
                print_status "Configuration file removed"
            fi
        fi

        # Remove __pycache__ directories
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true

        print_success "Application data cleaned up"
    else
        print_status "Application data preserved"
    fi
}

# Ask about system packages
ask_remove_packages() {
    echo ""
    print_warning "Do you want to remove system packages that were installed?"
    echo "This will attempt to remove:"
    echo "  - Python packages (if installed by this script)"
    echo "  - Audio packages (pulseaudio, alsa-utils)"
    echo ""
    print_warning "Only remove if these packages are not used by other applications!"
    echo ""
    read -p "Remove system packages? [y/N]: " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Removing system packages..."

        # List of packages that might have been installed
        local packages=(
            "python3-rpi.gpio"
            "rpi.gpio-common"
            "raspi-gpio"
            "pulseaudio-utils"
        )

        print_status "Attempting to remove packages (errors are normal if not installed)..."
        for package in "${packages[@]}"; do
            if dpkg -l | grep -q "^ii.*$package"; then
                print_status "Removing $package..."
                sudo apt remove -y "$package" 2>/dev/null || true
            fi
        done

        # Clean up
        sudo apt autoremove -y 2>/dev/null || true

        print_success "System packages cleanup completed"
    else
        print_status "System packages preserved"
    fi
}

# Final cleanup and summary
final_cleanup() {
    print_status "Performing final cleanup..."

    # Remove any remaining systemd files
    sudo systemctl daemon-reload

    # Clear systemd cache
    sudo systemctl reset-failed "$SERVICE_NAME" 2>/dev/null || true

    print_success "Uninstallation completed!"
    echo ""
    echo -e "${GREEN}=== Uninstall Summary ===${NC}"
    echo -e "✓ Service stopped and disabled"
    echo -e "✓ Service file removed"
    echo -e "✓ Helper scripts removed"
    echo -e "✓ System cleanup completed"
    echo ""
    echo -e "${YELLOW}=== What Remains ===${NC}"
    echo "The following may still be present:"
    echo "  - Project source code (in current directory)"
    echo "  - Sound files (in sounds/ directory)"
    echo "  - Sequence files (in sequences/ directory)"
    echo "  - User group memberships (gpio, audio)"
    echo ""
    echo -e "${BLUE}=== Manual Cleanup (if needed) ===${NC}"
    echo "To completely remove all traces:"
    echo "1. Delete this directory: rm -rf $SCRIPT_DIR"
    echo "2. Remove from user groups: sudo deluser $USER gpio"
    echo "3. Remove from user groups: sudo deluser $USER audio"
    echo ""
    print_success "ErntedankSequenzer has been uninstalled! 🗑️"
}

# Show what will be removed
show_removal_plan() {
    echo ""
    echo -e "${YELLOW}=== Uninstall Plan ===${NC}"
    echo "The following will be removed:"
    echo "  ✓ Systemd service: $SERVICE_NAME"
    echo "  ✓ Service file: /etc/systemd/system/${SERVICE_NAME}.service"
    echo "  ✓ Helper scripts (service-*.sh, view-logs.sh)"
    echo "  ✓ GPIO udev rules (if present)"
    echo ""
    echo "You will be asked about:"
    echo "  ? Application data (venv, logs, config)"
    echo "  ? System packages (if you want to remove them)"
    echo ""
    echo "This will NOT remove:"
    echo "  • Source code files"
    echo "  • Sound files"
    echo "  • Sequence files"
    echo ""
    read -p "Continue with uninstallation? [y/N]: " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Uninstallation cancelled by user"
        exit 0
    fi
}

# Main uninstall function
main() {
    print_banner

    print_header "Starting ErntedankSequenzer removal..."

    check_root
    show_removal_plan
    remove_service
    remove_udev_rules
    cleanup_helpers
    ask_remove_data
    ask_remove_packages
    final_cleanup
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_REMOVE=true
            shift
            ;;
        --keep-data)
            KEEP_DATA=true
            shift
            ;;
        --help|-h)
            echo "ErntedankSequenzer Uninstall Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force        Skip confirmation prompts"
            echo "  --keep-data    Preserve application data"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "This script will:"
            echo "  1. Stop and disable the systemd service"
            echo "  2. Remove service files"
            echo "  3. Clean up helper scripts"
            echo "  4. Optionally remove application data"
            echo "  5. Optionally remove system packages"
            echo ""
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main uninstall
main
