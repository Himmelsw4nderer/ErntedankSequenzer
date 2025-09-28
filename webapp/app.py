from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename

# Get absolute paths to ensure correct working directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
os.chdir(PROJECT_ROOT)

# Add project root to path to import our modules
sys.path.insert(0, str(PROJECT_ROOT))

from sequence_generator import SequenceGenerator
from sequence_executor import get_executor, cleanup_executor

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize generator with absolute paths
generator = SequenceGenerator(sequences_dir=str(PROJECT_ROOT / 'sequences'))

# Template helper functions
@app.template_filter('format_file_size')
def format_file_size(bytes):
    """Format file size in human readable format"""
    if bytes == 0:
        return '0 Bytes'

    k = 1024
    sizes = ['Bytes', 'KB', 'MB', 'GB']
    i = int(bytes.bit_length() - 1) // 10 if bytes > 0 else 0
    i = min(i, len(sizes) - 1)

    return f"{bytes / (k ** i):.1f} {sizes[i]}"

@app.template_filter('format_timestamp')
def format_timestamp(timestamp):
    """Format timestamp in human readable format"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M')

@app.route('/')
def index():
    """Main sequence editor page"""
    sequences = generator.list_sequences()
    examples = generator.get_example_sequences()
    return render_template('index.html', sequences=sequences, examples=examples)

@app.route('/sounds')
def sounds():
    """Sound file management page"""
    try:
        sounds_dir = PROJECT_ROOT / 'sounds'
        sounds = []

        if sounds_dir.exists():
            for file in sounds_dir.iterdir():
                if file.is_file() and file.suffix.lower() in ['.wav', '.mp3', '.ogg', '.flac', '.m4a']:
                    stat = file.stat()
                    sounds.append({
                        'name': file.name,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })

        config = load_config()
        supported_formats = config.get('sound_formats', ['.wav', '.mp3', '.ogg', '.flac', '.m4a'])

        return render_template('sounds.html', sounds=sorted(sounds, key=lambda x: x['name']),
                             supported_formats=supported_formats)
    except Exception as e:
        return render_template('sounds.html', sounds=[], supported_formats=['.wav', '.mp3', '.ogg', '.flac', '.m4a'],
                             error=str(e))

@app.route('/editor')
@app.route('/editor/<sequence_name>')
def editor(sequence_name=None):
    """Sequence editor page"""
    sequence_code = ""
    if sequence_name:
        sequence_code = generator.load_sequence(sequence_name)
        if sequence_code is None:
            sequence_code = ""
            sequence_name = None

    examples = generator.get_example_sequences()
    return render_template('editor.html',
                         sequence_name=sequence_name,
                         sequence_code=sequence_code,
                         examples=examples)

@app.route('/api/validate', methods=['POST'])
def validate_sequence():
    """Validate sequence syntax"""
    try:
        data = request.get_json()
        sequence_text = data.get('sequence', '')

        errors, warnings = generator.validate_sequence(sequence_text)

        return jsonify({
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        })
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [f"Validation error: {str(e)}"],
            'warnings': []
        }), 500

@app.route('/api/save', methods=['POST'])
def save_sequence():
    """Save sequence to file"""
    try:
        data = request.get_json()
        sequence_name = data.get('name', '').strip()
        sequence_text = data.get('sequence', '')

        if not sequence_name:
            return jsonify({
                'success': False,
                'error': 'Sequence name is required'
            }), 400

        # Validate name
        if not sequence_name.replace('_', '').replace('-', '').isalnum():
            return jsonify({
                'success': False,
                'error': 'Sequence name can only contain letters, numbers, hyphens and underscores'
            }), 400

        success, errors, warnings = generator.generate_sequence(sequence_name, sequence_text)

        if success:
            return jsonify({
                'success': True,
                'warnings': warnings,
                'message': f'Sequence "{sequence_name}" saved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'errors': errors,
                'warnings': warnings
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Save error: {str(e)}'
        }), 500

@app.route('/api/sequences')
def list_sequences():
    """List all sequences"""
    try:
        sequences = generator.list_sequences()
        return jsonify({
            'success': True,
            'sequences': sequences
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sequences/<sequence_name>')
def get_sequence(sequence_name):
    """Get sequence content"""
    try:
        sequence_code = generator.load_sequence(sequence_name)
        if sequence_code is None:
            return jsonify({
                'success': False,
                'error': 'Sequence not found'
            }), 404

        return jsonify({
            'success': True,
            'name': sequence_name,
            'code': sequence_code
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sequences/<sequence_name>', methods=['DELETE'])
def delete_sequence(sequence_name):
    """Delete sequence"""
    try:
        # Stop sequence if it's running
        executor = get_executor()
        if executor.is_running():
            executor.stop_sequence()

        success = generator.delete_sequence(sequence_name)
        if success:
            return jsonify({
                'success': True,
                'message': f'Sequence "{sequence_name}" deleted'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Sequence not found or could not be deleted'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/control/start/<sequence_name>')
def start_sequence(sequence_name):
    """Start sequence execution"""
    try:
        executor = get_executor()

        # Check if sequence file exists
        sequence_path = PROJECT_ROOT / 'sequences' / f'{sequence_name}.py'
        if not sequence_path.exists():
            return jsonify({
                'success': False,
                'error': 'Sequence file not found'
            }), 404

        # Start sequence in loop mode
        success = executor.run_sequence(str(sequence_path), loop=True)

        if success:
            return jsonify({
                'success': True,
                'message': f'Started sequence "{sequence_name}" in loop mode'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Sequence is already running'
            }), 409

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/control/run/<sequence_name>')
def run_sequence_once(sequence_name):
    """Run sequence once"""
    try:
        executor = get_executor()

        # Check if sequence file exists
        sequence_path = PROJECT_ROOT / 'sequences' / f'{sequence_name}.py'
        if not sequence_path.exists():
            return jsonify({
                'success': False,
                'error': 'Sequence file not found'
            }), 404

        # Run sequence once
        success = executor.run_sequence(str(sequence_path), loop=False)

        if success:
            return jsonify({
                'success': True,
                'message': f'Running sequence "{sequence_name}" once'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Sequence is already running'
            }), 409

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/control/stop')
def stop_sequence():
    """Stop sequence execution"""
    try:
        executor = get_executor()
        success = executor.stop_sequence()

        return jsonify({
            'success': True,
            'message': 'Sequence stopped'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/control/status')
def get_status():
    """Get current execution status"""
    try:
        executor = get_executor()
        status = executor.get_status()

        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/feedback/actions')
def get_actions():
    """Get recent sequence actions for feedback"""
    try:
        executor = get_executor()
        limit = request.args.get('limit', 50, type=int)
        actions = executor.get_recent_actions(limit)

        return jsonify({
            'success': True,
            'actions': actions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/feedback/clear', methods=['POST'])
def clear_actions():
    """Clear the action log"""
    try:
        executor = get_executor()
        executor.clear_action_log()

        return jsonify({
            'success': True,
            'message': 'Action log cleared'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/feedback/stream')
def stream_actions():
    """Server-Sent Events stream for real-time action updates"""
    def generate():
        executor = get_executor()
        last_count = 0

        # Send initial data
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to action stream'})}\n\n"

        while True:
            try:
                current_actions = executor.get_recent_actions(10)
                current_count = len(executor.action_log)

                # Send new actions if log has grown
                if current_count > last_count:
                    new_actions = list(executor.action_log)[last_count:]
                    for action in new_actions:
                        yield f"data: {json.dumps(action)}\n\n"
                    last_count = current_count

                import time
                time.sleep(1)  # Check for updates every second

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    from flask import Response
    return Response(generate(), mimetype='text/plain', headers={'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache'})

@app.route('/api/sounds')
def list_sounds():
    """List available sound files"""
    try:
        sounds_dir = PROJECT_ROOT / 'sounds'
        sounds = []

        if sounds_dir.exists():
            for file in sounds_dir.iterdir():
                if file.is_file() and file.suffix.lower() in ['.wav', '.mp3', '.ogg', '.flac', '.m4a']:
                    stat = file.stat()
                    sounds.append({
                        'name': file.name,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })

        return jsonify({
            'success': True,
            'sounds': sorted(sounds, key=lambda x: x['name'])
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/examples')
def get_examples():
    """Get example sequences"""
    try:
        examples = generator.get_example_sequences()
        return jsonify({
            'success': True,
            'examples': examples
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sounds/upload', methods=['POST'])
def upload_sound():
    """Upload a sound file"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Load config to get supported formats
        config = load_config()
        supported_formats = config.get('sound_formats', ['.wav', '.mp3', '.ogg', '.flac', '.m4a'])

        # Check file extension
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()

        if file_ext not in supported_formats:
            return jsonify({
                'success': False,
                'error': f'Unsupported file format. Supported formats: {", ".join(supported_formats)}'
            }), 400

        # Check file size (limit to 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if file.content_length and file.content_length > max_size:
            return jsonify({
                'success': False,
                'error': 'File too large. Maximum size is 50MB'
            }), 400

        # Create sounds directory if it doesn't exist
        sounds_dir = PROJECT_ROOT / 'sounds'
        sounds_dir.mkdir(exist_ok=True)

        # Check if file already exists
        file_path = sounds_dir / filename
        if file_path.exists():
            return jsonify({
                'success': False,
                'error': f'File "{filename}" already exists'
            }), 409

        # Save the file
        file.save(str(file_path))

        # Get file info
        stat = file_path.stat()

        return jsonify({
            'success': True,
            'message': f'Successfully uploaded "{filename}"',
            'file': {
                'name': filename,
                'size': stat.st_size,
                'modified': stat.st_mtime
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Upload error: {str(e)}'
        }), 500

@app.route('/sounds/<filename>')
def serve_sound(filename):
    """Serve sound files for preview"""
    from flask import send_from_directory
    try:
        # Sanitize filename
        filename = secure_filename(filename)
        sounds_dir = PROJECT_ROOT / 'sounds'

        # Check if file exists and is in sounds directory
        file_path = sounds_dir / filename
        if not file_path.exists():
            return "Sound file not found", 404

        return send_from_directory(str(sounds_dir), filename)
    except Exception as e:
        return f"Error serving sound file: {str(e)}", 500

@app.route('/api/sounds/<filename>', methods=['DELETE'])
def delete_sound(filename):
    """Delete a sound file"""
    try:
        # Sanitize filename
        filename = secure_filename(filename)
        file_path = PROJECT_ROOT / 'sounds' / filename

        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': 'Sound file not found'
            }), 404

        # Delete the file
        file_path.unlink()

        return jsonify({
            'success': True,
            'message': f'Successfully deleted "{filename}"'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Delete error: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Cleanup on shutdown
import atexit
atexit.register(cleanup_executor)

def load_config(config_file=None):
    """Load configuration from JSON file"""
    if config_file is None:
        config_file = PROJECT_ROOT / 'config.json'
    else:
        config_file = Path(config_file)

    default_config = {
        'sound_formats': ['.wav', '.mp3', '.ogg', '.flac', '.m4a']
    }

    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                return {**default_config, **config}
    except Exception:
        pass

    return default_config

if __name__ == '__main__':
    # Create necessary directories
    (PROJECT_ROOT / 'sequences').mkdir(exist_ok=True)
    (PROJECT_ROOT / 'sounds').mkdir(exist_ok=True)
    (PROJECT_ROOT / 'logs').mkdir(exist_ok=True)

    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
