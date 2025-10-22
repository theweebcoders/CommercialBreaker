"""
Commercial Break Renderer - Pre-renders commercial breaks for precise timing.

Phase 2 focus: core break selection, rendering, and caching primitives without
the background scheduler (added in later phases).
"""

from __future__ import annotations

import random
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import config
from .ExecutableUtils import get_executable_path
from .AudioTrackSelector import get_audio_selector


@dataclass(frozen=True)
class Commercial:
    """Represents a commercial asset in the library."""

    file_path: str
    duration: int  # Duration in milliseconds
    title: str


class CommercialBreakRenderer:
    """Builds and caches pre-rendered commercial break assets."""

    def __init__(self, commercial_folder: str, temp_folder: str):
        self.commercial_folder = Path(commercial_folder)
        self.temp_folder = Path(temp_folder)

        self.temp_folder.mkdir(parents=True, exist_ok=True)

        # Cache: break_id -> metadata dict with path + duration + created_at
        self.break_cache = {}
        self.duration_cache = {}
        self._codec_cache = {}
        self._commercial_library: Optional[List[Commercial]] = None
        self._codec_cache = {}

        # Cache FFmpeg/FFprobe paths for Windows compatibility
        self.ffmpeg_bin = get_executable_path("ffmpeg", getattr(config, "ffmpeg_path", None))
        self.ffprobe_bin = get_executable_path("ffprobe", getattr(config, "ffprobe_path", None))

        # Load existing pre-rendered breaks from disk into cache
        self._load_existing_breaks()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def plan_break(self, break_id: str, target_duration_ms: int) -> str:
        safe_break_id = self._sanitize_id(break_id)
        output_file = self.temp_folder / f"{safe_break_id}.mkv"

        # Check both original and sanitized ID in cache
        metadata = self.break_cache.get(break_id) or self.break_cache.get(safe_break_id)
        if not metadata:
            metadata = {
                'id': break_id,
                'path': str(output_file),
                'created_at': None,
                'duration_ms': target_duration_ms,
                'commercials': None,
            }
            self.break_cache[break_id] = metadata
            # Also cache with sanitized ID for lookup after disk load
            if safe_break_id != break_id:
                self.break_cache[safe_break_id] = metadata
        else:
            metadata['duration_ms'] = target_duration_ms

        return str(output_file)

    def get_or_build_break(self, break_id: str, target_duration_ms: int) -> Optional[dict]:
        """Return a cached break or build a new one."""

        # Check both original and sanitized ID
        safe_break_id = self._sanitize_id(break_id)
        cached = self.break_cache.get(break_id) or self.break_cache.get(safe_break_id)
        if cached and cached.get('created_at') and Path(cached['path']).exists():
            return cached

        self.plan_break(break_id, target_duration_ms)

        metadata = self.build_commercial_break(target_duration_ms, break_id)
        if metadata:
            self.break_cache[break_id] = metadata
            # Also cache with sanitized ID
            if safe_break_id != break_id:
                self.break_cache[safe_break_id] = metadata
        return metadata

    def pre_render_window(self, break_requests: List[dict], window_ms: int):
        if not break_requests:
            return

        for request in sorted(break_requests, key=lambda b: b.get('offset_ms', 0)):
            if request.get('offset_ms', 0) > window_ms:
                break
            self.get_or_build_break(request['id'], request['duration_ms'])

    def build_commercial_break(self, flex_duration_ms: int, break_id: str) -> Optional[dict]:
        """Build a fresh pre-rendered break and return its metadata."""

        commercials = self.select_commercials_for_duration(flex_duration_ms)
        if not commercials:
            return None

        output_file = self.render_commercial_break(commercials, break_id, flex_duration_ms)
        if not output_file:
            return None

        output_path = Path(output_file)
        actual_duration_ms = self._get_video_duration_ms(output_path)
        if actual_duration_ms <= 0:
            actual_duration_ms = flex_duration_ms

        return {
            'id': break_id,
            'path': str(output_path),
            'created_at': datetime.now(timezone.utc),
            'duration_ms': flex_duration_ms,
            'actual_duration_ms': actual_duration_ms,
            'commercials': commercials,
        }

    def pre_render_upcoming_breaks(self, channel_data: dict, hours_ahead: float = 1.0):
        """Pre-render breaks based on current position in looping channel timeline."""

        programs = channel_data.get('programs', [])
        if not programs:
            return

        # Calculate current position in channel loop
        channel_start = self._parse_iso(channel_data.get('startTime'))
        tz = channel_start.tzinfo if (channel_start and channel_start.tzinfo) else timezone.utc
        current_time = datetime.now(tz)

        channel_duration_ms = channel_data.get('duration', 0)
        if channel_duration_ms <= 0:
            return

        # Get current position in loop (milliseconds into the channel)
        elapsed_ms = int((current_time - channel_start).total_seconds() * 1000)
        current_position_ms = elapsed_ms % channel_duration_ms

        # Calculate window (current position + hours ahead, wrapping around if needed)
        window_duration_ms = int(hours_ahead * 60 * 60 * 1000)
        window_end_ms = current_position_ms + window_duration_ms

        # Find all commercial break programs in the window
        timeline_ms = 0
        for program in programs:
            program_duration = program.get('duration', 0)
            program_start_ms = timeline_ms
            program_end_ms = timeline_ms + program_duration

            # Check if this program is a commercial break
            title = (program.get('title') or '').lower()
            file_path = program.get('file', '')
            is_commercial_break = 'commercial break' in title or '_pre_rendered_breaks' in file_path

            if is_commercial_break:
                # Check if break falls within window (accounting for loop wrap-around)
                in_window = False
                if window_end_ms <= channel_duration_ms:
                    # No wrap-around
                    in_window = (current_position_ms <= program_start_ms < window_end_ms)
                else:
                    # Window wraps around - check both parts
                    in_window = (program_start_ms >= current_position_ms) or (program_start_ms < (window_end_ms % channel_duration_ms))

                if in_window:
                    # Extract break_id from file path (include "break_" prefix)
                    import re
                    match = re.search(r'(break_[^/]+)\.mkv', file_path)
                    if match:
                        break_id = match.group(1)
                        print(f"[BREAK_RENDERER] Pre-rendering: {break_id} at position {program_start_ms}ms")
                        self.get_or_build_break(break_id, program_duration)

            timeline_ms += program_duration

    def start_background_renderer(self, get_channels_callback, interval_minutes: int = 30):
        """Start a background thread that keeps the break cache warm."""

        if not callable(get_channels_callback):
            raise ValueError('get_channels_callback must be callable')

        def render_loop():
            import time

            while True:
                try:
                    channels = list(get_channels_callback() or [])

                    for channel in channels:
                        if not self._is_valid_channel(channel):
                            continue

                        lookahead_hours = max(1.0, interval_minutes / 60.0 + 1.0)
                        self.pre_render_upcoming_breaks(channel, hours_ahead=lookahead_hours)
                except Exception as exc:  # pragma: no cover - best effort logging
                    print(f"[BREAK_RENDERER] Error: {exc}")
                finally:
                    time.sleep(interval_minutes * 60)

        import threading

        thread = threading.Thread(target=render_loop, name="CommercialBreakRenderer", daemon=True)
        thread.start()
        return thread

    def identify_upcoming_breaks(self, channel_data: dict, start_time: datetime, end_time: datetime) -> List[dict]:
        """Find commercial break opportunities between bumps within a window."""

        programs = channel_data.get('programs', [])
        breaks = []

        start_ref = start_time
        end_ref = end_time

        for idx, program in enumerate(programs[:-1]):
            next_program = programs[idx + 1]

            if not self._is_bump_program(program) or not self._is_bump_program(next_program):
                continue

            program_stop = self._parse_iso(program.get('stop'))
            if not program_stop:
                continue

            if program_stop.tzinfo is None and start_ref.tzinfo is not None:
                program_stop = program_stop.replace(tzinfo=start_ref.tzinfo)
            elif program_stop.tzinfo is not None and start_ref.tzinfo is None:
                start_ref = start_ref.replace(tzinfo=program_stop.tzinfo)
                end_ref = end_ref.replace(tzinfo=program_stop.tzinfo)

            if not (start_ref <= program_stop <= end_ref):
                continue

            flex_duration = next_program.get('duration') or next_program.get('endPosition')
            if not isinstance(flex_duration, int):
                continue

            # Generate deterministic break_id matching LoadingDock logic
            # Use block_id and endPosition to ensure same ID across server restarts
            block_id = program.get('block_id') or next_program.get('block_id') or f'idx_{idx}'
            end_marker = program.get('endPosition') or program.get('seekPosition') or idx
            network = channel_data.get('name', '')
            break_id = f"break_{block_id}_{network}_{end_marker}_{flex_duration}"

            breaks.append({
                'id': break_id,
                'start_time': program_stop,
                'duration_ms': flex_duration,
            })

        return breaks

    def select_commercials_for_duration(self, target_ms: int, used_commercials: Optional[Iterable[str]] = None) -> List[dict]:
        """Pick commercials that sum to the target duration, trimming the last if needed."""

        library = self._load_commercial_library()
        if not library or target_ms <= 0:
            return []

        used_set = set(used_commercials or [])
        available = [c for c in library if c.file_path not in used_set]

        if not available:
            return []

        # CRITICAL FIX: Probe durations on-demand for small subset instead of all commercials
        selected: List[dict] = []
        remaining = target_ms
        max_attempts = 200

        random.shuffle(available)

        idx = 0
        while remaining > 0 and max_attempts > 0 and idx < len(available):
            commercial = available[idx]
            idx += 1
            max_attempts -= 1

            duration = self._ensure_commercial_duration(commercial)
            if duration <= 0:
                continue

            if duration <= remaining:
                selected.append({
                    'file_path': commercial.file_path,
                    'duration': duration,
                    'title': commercial.title,
                })
                remaining -= duration
            else:
                selected.append({
                    'file_path': commercial.file_path,
                    'duration': duration,
                    'title': commercial.title,
                    'trim_duration': remaining,
                })
                remaining = 0

        if remaining > 0:
            return []

        return selected

    def render_commercial_break(self, commercials: List[dict], break_id: str, target_duration_ms: int) -> Optional[Path]:
        """Render a pre-stitched break using FFmpeg concat."""

        if not commercials:
            return None

        safe_break_id = self._sanitize_id(break_id)
        output_file = self.temp_folder / f"{safe_break_id}.mkv"
        concat_file = self.temp_folder / f"{safe_break_id}_concat.txt"
        temp_segments: List[Path] = []

        try:
            with concat_file.open('w', encoding='utf-8') as fh:
                for idx, commercial in enumerate(commercials):
                    segment = self._prepare_segment(
                        Path(commercial['file_path']),
                        safe_break_id,
                        idx,
                        commercial.get('trim_duration'),
                    )
                    temp_segments.append(segment)
                    fh.write(f"file '{self._format_concat_entry(segment)}'\n")

            cmd = [
                self.ffmpeg_bin, '-hide_banner', '-loglevel', 'error',
                '-f', 'concat', '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-f', 'matroska',
                '-avoid_negative_ts', 'make_zero',
                '-y', str(output_file)
            ]
            subprocess.run(cmd, check=True)

            return output_file if output_file.exists() else None
        except subprocess.CalledProcessError as e:
            print(f"[BREAK_RENDERER] ERROR: Failed to render break {break_id}")
            print(f"[BREAK_RENDERER] FFmpeg command failed during concat")
            return None
        finally:
            if concat_file.exists():
                concat_file.unlink()
            for segment in temp_segments:
                if segment.exists():
                    segment.unlink()

    def _prepare_segment(self, source: Path, break_id: str, index: int, trim_duration_ms: Optional[int]) -> Path:
        segment_path = self.temp_folder / f"{break_id}_seg_{index}.mkv"
        if segment_path.exists():
            segment_path.unlink()

        duration_seconds = None
        if trim_duration_ms is not None and trim_duration_ms > 0:
            duration_seconds = max(0.0, trim_duration_ms / 1000.0)

        try:
            codec = self._get_video_codec(source)
            if codec == 'h264' and duration_seconds is None:
                self._remux_to_mkv(source, segment_path, duration_seconds)
            else:
                raise subprocess.CalledProcessError(returncode=1, cmd=[self.ffmpeg_bin, 'copy-codec-unsupported'])
        except subprocess.CalledProcessError:
            if segment_path.exists():
                segment_path.unlink()
            self._transcode_to_mkv(source, segment_path, duration_seconds)

        return segment_path

    def _ensure_commercial_duration(self, commercial: Commercial) -> int:
        if commercial.duration is not None and commercial.duration > 0:
            return commercial.duration

        duration = self._get_video_duration_ms(Path(commercial.file_path))
        if duration <= 0:
            return 0

        object.__setattr__(commercial, 'duration', duration)
        return duration

    def cleanup_old_breaks(self, cutoff_time: datetime):
        """Remove cached break files older than the cutoff."""

        stale_ids = []
        for break_id, metadata in self.break_cache.items():
            created_at = metadata.get('created_at')
            if not isinstance(created_at, datetime):
                continue
            if created_at < cutoff_time:
                stale_ids.append(break_id)

        for break_id in stale_ids:
            path = Path(self.break_cache[break_id]['path'])
            if path.exists():
                path.unlink()
            del self.break_cache[break_id]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_existing_breaks(self):
        """Load existing pre-rendered breaks from disk into cache."""
        if not self.temp_folder.exists():
            return

        loaded_count = 0
        for break_file in self.temp_folder.glob("*.mkv"):
            # Extract break_id from filename (reverse of _sanitize_id)
            # The filename is sanitized, so we need to reconstruct the original break_id
            sanitized_id = break_file.stem

            # Get file modification time as created_at
            mtime = break_file.stat().st_mtime
            created_at = datetime.fromtimestamp(mtime, tz=timezone.utc)

            # Get duration by probing the file
            try:
                duration_ms = self._get_video_duration_ms(break_file)
            except Exception:
                # If we can't get duration, skip this file
                continue

            # Reconstruct break_id (best effort - use sanitized version)
            # Since we can't perfectly reverse sanitize, use the filename as the ID
            break_id = sanitized_id

            # Add to cache
            self.break_cache[break_id] = {
                'id': break_id,
                'path': str(break_file),
                'created_at': created_at,
                'duration_ms': duration_ms,
                'commercials': None,  # We don't know which commercials were used
            }
            loaded_count += 1

        if loaded_count > 0:
            print(f"[BREAK_RENDERER] Loaded {loaded_count} existing pre-rendered break(s) from disk")

    def _load_commercial_library(self) -> List[Commercial]:
        if self._commercial_library is not None:
            return self._commercial_library

        commercials: List[Commercial] = []
        if not self.commercial_folder.exists():
            self._commercial_library = commercials
            return commercials

        for file_path in self.commercial_folder.rglob('*'):
            if file_path.suffix.lower() not in {'.mp4', '.mkv', '.mov', '.ts'}:
                continue

            commercials.append(Commercial(
                file_path=str(file_path),
                duration=-1,
                title=f"Commercial - {file_path.stem}"
            ))

        self._commercial_library = commercials
        print(f"[COMMERCIAL_RENDERER] Catalogued {len(commercials)} commercial files (durations probed on demand)")
        return commercials

    def _get_video_duration_ms(self, file_path: Path) -> int:
        """Probe video duration (ms) with caching."""

        if not file_path.exists():
            return 0

        cache_key = str(file_path.resolve())
        modified_ns = file_path.stat().st_mtime_ns

        cached = self.duration_cache.get(cache_key)
        if cached and cached['mtime_ns'] == modified_ns:
            return cached['duration_ms']

        cmd = [
            self.ffprobe_bin, '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0', str(file_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration_seconds = float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
            return 0

        duration_ms = max(0, round(duration_seconds * 1000))
        if duration_ms <= 0:
            return 0

        if modified_ns is not None:
            self.duration_cache[cache_key] = {
                'mtime_ns': modified_ns,
                'duration_ms': duration_ms
            }

        return duration_ms

    def _remux_to_mkv(self, source: Path, destination: Path, duration_seconds: Optional[float]):
        cmd = [
            self.ffmpeg_bin, '-hide_banner', '-loglevel', 'error',
            '-i', str(source)
        ]

        # Get audio track selection for stream copy
        audio_selector = get_audio_selector()
        track_mapping = audio_selector.get_stream_copy_mapping(source)
        if track_mapping:
            cmd.extend(track_mapping)

        if duration_seconds is not None and duration_seconds > 0:
            cmd += ['-t', f"{duration_seconds:.3f}"]

        cmd += [
            '-c', 'copy',
            '-f', 'matroska',
            '-y', str(destination)
        ]

        subprocess.run(cmd, check=True)

    def _transcode_to_mkv(self, source: Path, destination: Path, duration_seconds: Optional[float]):
        cmd = [
            self.ffmpeg_bin, '-hide_banner', '-loglevel', 'error',
            '-i', str(source)
        ]

        # Get audio track selection
        audio_selector = get_audio_selector()
        track_mapping = audio_selector.get_ffmpeg_audio_mapping(source)
        cmd.extend(track_mapping)

        if duration_seconds is not None and duration_seconds > 0:
            cmd += ['-t', f"{duration_seconds:.3f}"]

        cmd += [
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-ac', '2',
            '-b:a', '192k',
            '-f', 'matroska',
            '-y', str(destination)
        ]

        subprocess.run(cmd, check=True)

    def _get_video_codec(self, source: Path) -> Optional[str]:
        cache_key = str(source)
        if cache_key in self._codec_cache:
            return self._codec_cache[cache_key]

        cmd = [
            self.ffprobe_bin, '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(source)
        ]

        codec = None
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            codec_name = result.stdout.strip().lower()
            codec = codec_name if codec_name else None
        except subprocess.CalledProcessError:
            codec = None

        self._codec_cache[cache_key] = codec
        return codec

    @staticmethod
    def _sanitize_id(value: str) -> str:
        return re.sub(r'[^A-Za-z0-9_-]+', '_', value)

    @staticmethod
    def _format_concat_entry(path: Path) -> str:
        return str(path).replace("'", "\\'")

    @staticmethod
    def _is_bump_program(program: dict) -> bool:
        title = (program.get('title') or '').lower()
        file_path = (program.get('file') or program.get('file_path') or '').lower()
        return 'bump' in title or '/bump/' in file_path

    @staticmethod
    def _is_valid_channel(channel: dict) -> bool:
        return isinstance(channel, dict) and channel.get('programs')

    @staticmethod
    def _parse_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
