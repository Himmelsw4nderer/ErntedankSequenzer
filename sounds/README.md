# Sound Files Directory

This directory contains audio files that can be used in your sequences.

## Supported Formats

- WAV (.wav)
- MP3 (.mp3)
- OGG (.ogg)
- FLAC (.flac)
- M4A (.m4a)

## Usage

Place your audio files in this directory and reference them in your sequences using the `play_sound()` function:

```python
play_sound('your_audio_file.mp3')
play_sound('sound_effect.wav', 0.8)  # 80% volume
```

## Example Files

To get started, you can add some example files:

- `intro.wav` - Opening music or announcement
- `music.mp3` - Background music for light shows
- `effect.wav` - Sound effects for specific moments
- `outro.flac` - Closing music

## Tips

1. Keep file sizes reasonable to avoid memory issues
2. Use appropriate bit rates for your content (128-320 kbps for MP3)
3. Normalize audio levels to avoid volume jumps
4. Test playback before using in sequences
5. Consider using shorter loops for repeating background music

## File Organization

You can organize files in subdirectories if needed:

```python
play_sound('intro/welcome.mp3')
play_sound('effects/thunder.wav')
```

Just make sure to include the subdirectory path in your sequence code.