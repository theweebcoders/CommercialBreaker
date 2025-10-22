"""
Audio Track Selector - Automatically selects the appropriate audio track based on language preference.

Probes video files for available audio tracks and selects the best match
for the configured default language.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import config
from .ExecutableUtils import get_executable_path


class AudioTrackSelector:
    """Handles automatic audio track selection based on language preferences."""

    def __init__(self):
        self.default_language = getattr(config, 'DEFAULT_LANGUAGE', 'english').lower()
        self.language_variations = getattr(config, 'LANGUAGE_VARIATIONS', {})

        # Fallback if config doesn't have the new settings yet
        if not self.language_variations:
            self.language_variations = {
                'english': ['eng', 'english', 'english dub', 'inglês', 'en', 'en-us', 'en-gb', '英語', 'anglais', 'en_US', 'en_GB'],
                'japanese': ['jpn', 'japanese', 'jap', 'jp', 'ja', '日本語', 'japonais', 'japonês', 'ja_JP']
            }

        # Cache FFprobe path for Windows compatibility
        self.ffprobe_bin = get_executable_path("ffprobe", getattr(config, "ffprobe_path", None))

    def get_audio_tracks(self, file_path: Path) -> List[Dict]:
        """
        Probe a video file and return information about all audio tracks.

        Returns a list of dicts with keys: index, codec, language, title
        """
        cmd = [
            self.ffprobe_bin, '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 'a',  # Audio streams only
            str(file_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            streams = data.get('streams', [])

            tracks = []
            audio_stream_counter = 0
            for stream in streams:
                track = {
                    'index': stream.get('index'),  # Actual stream index in file
                    'stream_index': audio_stream_counter,  # Position among audio streams (0-based)
                    'codec': stream.get('codec_name', 'unknown'),
                    'language': stream.get('tags', {}).get('language', '').lower(),
                    'title': stream.get('tags', {}).get('title', '').lower(),
                    'channels': stream.get('channels', 2),
                    'sample_rate': stream.get('sample_rate', '48000')
                }
                tracks.append(track)
                audio_stream_counter += 1

            return tracks

        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            # If probing fails, return empty list (will use default track)
            return []

    def find_best_audio_track(self, file_path: Path, preferred_language: Optional[str] = None) -> Optional[int]:
        """
        Find the best audio track index based on language preference.

        Returns the stream index of the best match, or None to use default.
        """
        tracks = self.get_audio_tracks(file_path)
        if not tracks:
            return None  # Use default track

        # Use specified language or fall back to config default
        target_language = (preferred_language or self.default_language).lower()

        # Get variations for the target language
        variations = self.language_variations.get(target_language, [target_language])
        variations = [v.lower() for v in variations]

        # Simple search: find first track that matches any variation
        for i, track in enumerate(tracks):
            track_lang = track.get('language', '').lower()

            # Check if the track language matches any of our variations
            if track_lang and track_lang in variations:
                # Found a match!
                return i

        # No match found, use first track (default)
        return 0 if tracks else None

    def get_ffmpeg_audio_mapping(self, file_path: Path, preferred_language: Optional[str] = None) -> List[str]:
        """
        Get FFmpeg command arguments for selecting the appropriate audio track.

        Returns a list of FFmpeg arguments like ['-map', '0:v', '-map', '0:a:1']
        """
        track_index = self.find_best_audio_track(file_path, preferred_language)

        # Always map video
        args = ['-map', '0:v:0?']  # First video stream (optional)

        if track_index is not None:
            # Map specific audio track
            args.extend(['-map', f'0:a:{track_index}'])
        else:
            # Map first audio track (default)
            args.extend(['-map', '0:a:0?'])

        return args

    def get_stream_copy_mapping(self, file_path: Path, preferred_language: Optional[str] = None) -> List[str]:
        """
        Get FFmpeg arguments for stream copy with appropriate audio selection.

        This version is for when we're doing -c copy (no re-encoding).
        """
        track_index = self.find_best_audio_track(file_path, preferred_language)

        args = []

        if track_index is not None and track_index > 0:
            # Need to explicitly select the audio track
            args = ['-map', '0:v:0?', '-map', f'0:a:{track_index}']
        # If track_index is 0 or None, we can use default behavior

        return args


# Singleton instance
_audio_selector = None

def get_audio_selector() -> AudioTrackSelector:
    """Get or create the singleton AudioTrackSelector instance."""
    global _audio_selector
    if _audio_selector is None:
        _audio_selector = AudioTrackSelector()
    return _audio_selector