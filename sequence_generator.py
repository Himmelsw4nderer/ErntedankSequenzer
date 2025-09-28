import os
import re
import ast
from pathlib import Path

class SequenceGenerator:
    def __init__(self, sequences_dir='sequences'):
        self.sequences_dir = sequences_dir
        Path(sequences_dir).mkdir(exist_ok=True)

    def validate_sequence(self, sequence_text):
        """Validate sequence syntax and commands"""
        errors = []
        warnings = []

        lines = sequence_text.strip().split('\n')
        line_number = 0

        for line in lines:
            line_number += 1
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Check for valid function calls
            if not self._is_valid_function_call(line):
                errors.append(f"Line {line_number}: Invalid function call: {line}")
                continue

            # Validate specific functions
            try:
                if line.startswith('write_dmx('):
                    self._validate_write_dmx(line, line_number, errors, warnings)
                elif line.startswith('sleep('):
                    self._validate_sleep(line, line_number, errors, warnings)
                elif line.startswith('play_sound('):
                    self._validate_play_sound(line, line_number, errors, warnings)
                elif line.startswith('wait_for_sound()'):
                    pass  # Always valid
                elif line.startswith('stop_sound()'):
                    pass  # Always valid
                else:
                    warnings.append(f"Line {line_number}: Unknown function: {line}")
            except Exception as e:
                errors.append(f"Line {line_number}: Error parsing {line}: {str(e)}")

        return errors, warnings

    def _is_valid_function_call(self, line):
        """Check if line looks like a valid function call"""
        # Basic pattern matching for function calls
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)$'
        return bool(re.match(pattern, line))

    def _validate_write_dmx(self, line, line_number, errors, warnings):
        """Validate write_dmx function call"""
        try:
            # Extract parameters using AST
            call = ast.parse(line).body[0].value
            if len(call.args) != 2:
                errors.append(f"Line {line_number}: write_dmx() requires exactly 2 arguments (address, value)")
                return

            # Validate address
            try:
                if isinstance(call.args[0], ast.Constant):
                    address = call.args[0].value
                    if not (1 <= address <= 512):
                        errors.append(f"Line {line_number}: DMX address must be between 1 and 512")
                elif isinstance(call.args[0], ast.Num):  # Python < 3.8 compatibility
                    address = call.args[0].n
                    if not (1 <= address <= 512):
                        errors.append(f"Line {line_number}: DMX address must be between 1 and 512")
            except:
                warnings.append(f"Line {line_number}: Could not validate DMX address")

            # Validate value
            try:
                if isinstance(call.args[1], ast.Constant):
                    value = call.args[1].value
                    if not (0 <= value <= 255):
                        errors.append(f"Line {line_number}: DMX value must be between 0 and 255")
                elif isinstance(call.args[1], ast.Num):  # Python < 3.8 compatibility
                    value = call.args[1].n
                    if not (0 <= value <= 255):
                        errors.append(f"Line {line_number}: DMX value must be between 0 and 255")
            except:
                warnings.append(f"Line {line_number}: Could not validate DMX value")

        except Exception as e:
            errors.append(f"Line {line_number}: Invalid write_dmx() syntax")

    def _validate_sleep(self, line, line_number, errors, warnings):
        """Validate sleep function call"""
        try:
            call = ast.parse(line).body[0].value
            if len(call.args) != 1:
                errors.append(f"Line {line_number}: sleep() requires exactly 1 argument (seconds)")
                return

            # Validate time value
            try:
                if isinstance(call.args[0], ast.Constant):
                    seconds = call.args[0].value
                    if seconds < 0:
                        errors.append(f"Line {line_number}: Sleep time cannot be negative")
                    elif seconds > 3600:  # 1 hour
                        warnings.append(f"Line {line_number}: Sleep time is very long ({seconds}s)")
                elif isinstance(call.args[0], ast.Num):  # Python < 3.8 compatibility
                    seconds = call.args[0].n
                    if seconds < 0:
                        errors.append(f"Line {line_number}: Sleep time cannot be negative")
                    elif seconds > 3600:  # 1 hour
                        warnings.append(f"Line {line_number}: Sleep time is very long ({seconds}s)")
            except:
                warnings.append(f"Line {line_number}: Could not validate sleep duration")

        except Exception as e:
            errors.append(f"Line {line_number}: Invalid sleep() syntax")

    def _validate_play_sound(self, line, line_number, errors, warnings):
        """Validate play_sound function call"""
        try:
            call = ast.parse(line).body[0].value
            if not (1 <= len(call.args) <= 2):
                errors.append(f"Line {line_number}: play_sound() requires 1-2 arguments (file, volume)")
                return

            # Validate sound file
            if isinstance(call.args[0], ast.Constant):
                filename = call.args[0].value
                if not isinstance(filename, str):
                    errors.append(f"Line {line_number}: Sound filename must be a string")
            elif isinstance(call.args[0], ast.Str):  # Python < 3.8 compatibility
                filename = call.args[0].s

            # Validate volume if provided
            if len(call.args) == 2:
                try:
                    if isinstance(call.args[1], ast.Constant):
                        volume = call.args[1].value
                        if not (0.0 <= volume <= 1.0):
                            errors.append(f"Line {line_number}: Volume must be between 0.0 and 1.0")
                    elif isinstance(call.args[1], ast.Num):  # Python < 3.8 compatibility
                        volume = call.args[1].n
                        if not (0.0 <= volume <= 1.0):
                            errors.append(f"Line {line_number}: Volume must be between 0.0 and 1.0")
                except:
                    warnings.append(f"Line {line_number}: Could not validate volume")

        except Exception as e:
            errors.append(f"Line {line_number}: Invalid play_sound() syntax")

    def generate_sequence(self, sequence_name, sequence_text):
        """Generate executable Python sequence file"""
        errors, warnings = self.validate_sequence(sequence_text)

        if errors:
            return False, errors, warnings

        # Create the sequence file content
        sequence_content = self._create_sequence_file(sequence_text)

        # Write to file
        sequence_path = os.path.join(self.sequences_dir, f"{sequence_name}.py")
        try:
            with open(sequence_path, 'w') as f:
                f.write(sequence_content)
            return True, [], warnings
        except Exception as e:
            return False, [f"Error writing sequence file: {str(e)}"], warnings

    def _create_sequence_file(self, sequence_text):
        """Create the complete sequence file content"""
        header = '''#!/usr/bin/env python3
"""
Generated sequence file
This file is automatically generated from the web interface.
Do not edit manually - changes will be overwritten.
"""

# Sequence execution - commands run directly at module level
try:
'''

        footer = '''
except Exception as e:
    print(f"Sequence error: {e}")
    raise
'''

        # Process sequence text and add indentation
        lines = sequence_text.strip().split('\n')
        indented_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                indented_lines.append(f"    {line}")
            elif line.startswith('#'):
                indented_lines.append(f"    {line}")
            else:
                indented_lines.append("")

        sequence_body = '\n'.join(indented_lines)

        return header + sequence_body + '\n' + footer

    def list_sequences(self):
        """List all available sequences"""
        sequences = []
        try:
            for file in os.listdir(self.sequences_dir):
                if file.endswith('.py'):
                    name = file[:-3]  # Remove .py extension
                    path = os.path.join(self.sequences_dir, file)
                    stat = os.stat(path)
                    sequences.append({
                        'name': name,
                        'file': file,
                        'path': path,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
        except Exception as e:
            print(f"Error listing sequences: {e}")

        return sorted(sequences, key=lambda x: x['modified'], reverse=True)

    def delete_sequence(self, sequence_name):
        """Delete a sequence file"""
        sequence_path = os.path.join(self.sequences_dir, f"{sequence_name}.py")
        try:
            if os.path.exists(sequence_path):
                os.remove(sequence_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting sequence: {e}")
            return False

    def load_sequence(self, sequence_name):
        """Load sequence source code"""
        sequence_path = os.path.join(self.sequences_dir, f"{sequence_name}.py")
        try:
            with open(sequence_path, 'r') as f:
                content = f.read()

            # Extract the sequence code from the generated file
            return self._extract_sequence_code(content)
        except Exception as e:
            print(f"Error loading sequence: {e}")
            return None

    def _extract_sequence_code(self, file_content):
        """Extract user sequence code from generated file"""
        lines = file_content.split('\n')
        sequence_lines = []
        in_sequence = False

        for line in lines:
            if 'try:' in line and 'commands run directly at module level' in file_content:
                in_sequence = True
                continue
            elif in_sequence and line.strip().startswith('except Exception'):
                break
            elif in_sequence:
                # Remove indentation (4 spaces)
                if line.startswith('    '):
                    sequence_lines.append(line[4:])
                elif line.strip() == '':
                    sequence_lines.append('')

        return '\n'.join(sequence_lines).strip()

    def get_example_sequences(self):
        """Get example sequences for the user"""
        examples = {
            'simple_dmx': '''# Simple DMX GPIO example
write_dmx(1, 255)  # Turn on channel 1 full brightness via GPIO
sleep(2)           # Wait 2 seconds
write_dmx(1, 0)    # Turn off channel 1''',

            'dmx_fade': '''# DMX fade effect using GPIO
# Fade in channel 1
for brightness in range(0, 256, 10):
    write_dmx(1, brightness)
    sleep(0.1)

sleep(1)

# Fade out channel 1
for brightness in range(255, -1, -10):
    write_dmx(1, brightness)
    sleep(0.1)''',

            'sound_and_light': '''# Sound and light show
play_sound('intro.wav', 0.8)  # Play intro at 80% volume
write_dmx(1, 255)             # Turn on light via GPIO
wait_for_sound()              # Wait for sound to finish
write_dmx(1, 0)               # Turn off light''',

            'complex_sequence': '''# Complex lighting sequence
# Fade up channels 1-4
write_dmx(1, 64)
write_dmx(2, 128)
write_dmx(3, 192)
write_dmx(4, 255)
sleep(1)

# Play sound with light show
play_sound('music.mp3', 1.0)
for i in range(10):
    write_dmx(1, 255)
    sleep(0.1)
    write_dmx(1, 0)
    sleep(0.1)

# Fade all to black
write_dmx(1, 0)
write_dmx(2, 0)
write_dmx(3, 0)
write_dmx(4, 0)'''
        }

        return examples
