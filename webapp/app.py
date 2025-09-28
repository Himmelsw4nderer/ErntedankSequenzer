from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import sys
import json
from datetime import datetime

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sequence_generator import SequenceGenerator
from sequence_executor import get_executor, cleanup_executor

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize generator
generator = SequenceGenerator(sequences_dir='../sequences')

@app.route('/')
def index():
    """Main sequence editor page"""
    sequences = generator.list_sequences()
    examples = generator.get_example_sequences()
    return render_template('index.html', sequences=sequences, examples=examples)

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
        sequence_path = os.path.join('../sequences', f'{sequence_name}.py')
        if not os.path.exists(sequence_path):
            return jsonify({
                'success': False,
                'error': 'Sequence file not found'
            }), 404

        # Start sequence in loop mode
        success = executor.run_sequence(sequence_path, loop=True)

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
        sequence_path = os.path.join('../sequences', f'{sequence_name}.py')
        if not os.path.exists(sequence_path):
            return jsonify({
                'success': False,
                'error': 'Sequence file not found'
            }), 404

        # Run sequence once
        success = executor.run_sequence(sequence_path, loop=False)

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

@app.route('/api/sounds')
def list_sounds():
    """List available sound files"""
    try:
        sounds_dir = '../sounds'
        sounds = []

        if os.path.exists(sounds_dir):
            for file in os.listdir(sounds_dir):
                if file.lower().endswith(('.wav', '.mp3', '.ogg', '.flac')):
                    file_path = os.path.join(sounds_dir, file)
                    stat = os.stat(file_path)
                    sounds.append({
                        'name': file,
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

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Cleanup on shutdown
import atexit
atexit.register(cleanup_executor)

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('../sequences', exist_ok=True)
    os.makedirs('../sounds', exist_ok=True)

    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
