#!/usr/bin/env python3
"""
ErntedankSequenzer - Startup Script
Main entry point for the web application and sequence controller
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging(config):
    """Setup logging configuration"""
    log_level = getattr(logging, config.get('log_level', 'INFO').upper())

    # Get absolute path to project root and create logs directory
    project_root = Path(__file__).parent.absolute()
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)

    # Clear any existing handlers to prevent duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure logging with absolute paths
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logs_dir / 'sequenzer.log'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Force reconfiguration
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Log file: {logs_dir / 'sequenzer.log'}")
    return logger

def load_config(config_file='config.json'):
    """Load configuration from JSON file"""
    default_config = {
        'control_pin': 17,
        'serial_port': '/dev/ttyS0',
        'baud_rate': 250000,
        'sounds_directory': 'sounds',
        'sequences_directory': 'sequences',
        'web_host': '0.0.0.0',
        'web_port': 5000,
        'web_debug': False
    }

    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                return {**default_config, **config}
    except Exception as e:
        print(f"Error loading config: {e}")
        print("Using default configuration")

    return default_config

def create_directories(config):
    """Create necessary directories"""
    directories = [
        config['sounds_directory'],
        config['sequences_directory'],
        'logs',
        'webapp/static/uploads'
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"Created directory: {directory}")

def check_dependencies():
    """Check if required dependencies are available"""
    missing_deps = []

    try:
        import flask
    except ImportError:
        missing_deps.append('flask')

    try:
        import serial
    except ImportError:
        missing_deps.append('pyserial')

    try:
        import pygame
    except ImportError:
        missing_deps.append('pygame')

    # GPIO is optional (only needed on Raspberry Pi)
    try:
        import RPi.GPIO
    except ImportError:
        print("Warning: RPi.GPIO not available - GPIO control will be disabled")

    if missing_deps:
        print(f"Missing required dependencies: {', '.join(missing_deps)}")
        print("Please install them using:")
        print(f"pip install {' '.join(missing_deps)}")
        return False

    return True

def run_webapp(config, logger):
    """Run the Flask web application"""
    try:
        # Import Flask app
        from webapp.app import app
        import logging as flask_logging

        # Configure Flask app
        app.config['SECRET_KEY'] = config.get('secret_key', 'your-secret-key-change-this')

        # Set up webapp logging
        project_root = Path(__file__).parent.absolute()
        logs_dir = project_root / 'logs'
        webapp_log_file = logs_dir / 'webapp.log'

        # Configure Flask app logger
        app_logger = app.logger
        app_logger.setLevel(flask_logging.INFO)

        # Remove default handlers
        app_logger.handlers.clear()

        # Add file handler for Flask app
        app_file_handler = flask_logging.FileHandler(webapp_log_file)
        app_formatter = flask_logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        app_file_handler.setFormatter(app_formatter)
        app_logger.addHandler(app_file_handler)

        # Configure werkzeug logger
        werkzeug_logger = flask_logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(flask_logging.INFO)

        # Remove existing handlers to prevent duplicates
        werkzeug_logger.handlers.clear()

        # Add file handler for werkzeug
        werkzeug_file_handler = flask_logging.FileHandler(webapp_log_file)
        werkzeug_file_handler.setFormatter(app_formatter)
        werkzeug_logger.addHandler(werkzeug_file_handler)

        logger.info(f"Starting web server on {config['web_host']}:{config['web_port']}")
        logger.info(f"Web server logs: {webapp_log_file}")

        app.run(
            host=config['web_host'],
            port=config['web_port'],
            debug=config['web_debug'],
            threaded=True
        )

    except KeyboardInterrupt:
        logger.info("Shutting down web server...")
    except Exception as e:
        logger.error(f"Error running web server: {e}")
        raise

def run_cli_mode(config, logger, args):
    """Run in command-line mode for testing"""
    from sequence_executor import SequenceExecutor
    import time

    executor = SequenceExecutor()

    try:
        if args.sequence:
            sequence_file = os.path.join(config['sequences_directory'], f"{args.sequence}.py")
            if os.path.exists(sequence_file):
                logger.info(f"Running sequence: {args.sequence}")
                if args.loop:
                    executor.run_sequence(sequence_file, loop=True)
                    input("Press Enter to stop...")
                else:
                    executor.run_sequence(sequence_file, loop=False)
                    while executor.is_running():
                        time.sleep(0.1)
            else:
                logger.error(f"Sequence file not found: {sequence_file}")

        elif args.test_dmx:
            logger.info("Testing DMX output...")
            for i in range(1, 9):
                executor.write_dmx(i, 255)
                time.sleep(0.5)
                executor.write_dmx(i, 0)

        elif args.test_sound:
            if args.sound_file:
                sound_path = os.path.join(config['sounds_directory'], args.sound_file)
                if os.path.exists(sound_path):
                    logger.info(f"Playing sound: {args.sound_file}")
                    executor.play_sound(args.sound_file)
                    executor.wait_for_sound()
                else:
                    logger.error(f"Sound file not found: {sound_path}")
            else:
                logger.error("Please specify a sound file with --sound-file")

    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        executor.cleanup()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='ErntedankSequenzer - DMX & Sound Sequence Controller'
    )

    parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Configuration file path (default: config.json)'
    )

    parser.add_argument(
        '--cli',
        action='store_true',
        help='Run in command-line mode instead of web mode'
    )

    parser.add_argument(
        '--sequence', '-s',
        help='Run specific sequence (CLI mode only)'
    )

    parser.add_argument(
        '--loop', '-l',
        action='store_true',
        help='Run sequence in loop mode (CLI mode only)'
    )

    parser.add_argument(
        '--test-dmx',
        action='store_true',
        help='Test DMX output (CLI mode only)'
    )

    parser.add_argument(
        '--test-sound',
        action='store_true',
        help='Test sound output (CLI mode only)'
    )

    parser.add_argument(
        '--sound-file',
        help='Sound file to test (use with --test-sound)'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version='ErntedankSequenzer 1.0.0'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Setup logging
    logger = setup_logging(config)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Create necessary directories
    create_directories(config)

    # Show startup information
    logger.info("=" * 50)
    logger.info("ErntedankSequenzer Starting Up")
    logger.info("=" * 50)
    logger.info(f"Configuration file: {args.config}")
    logger.info(f"Sounds directory: {config['sounds_directory']}")
    logger.info(f"Sequences directory: {config['sequences_directory']}")

    if args.cli:
        logger.info("Running in CLI mode")
        run_cli_mode(config, logger, args)
    else:
        logger.info("Running in web mode")
        logger.info(f"Web interface will be available at: http://localhost:{config['web_port']}")
        run_webapp(config, logger)

if __name__ == '__main__':
    main()
