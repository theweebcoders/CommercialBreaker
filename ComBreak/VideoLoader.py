import subprocess
from typing import Optional, Tuple
import config
from ComBreak.utils import get_executable_path

# OpenCV constants for compatibility with existing code
CAP_PROP_FPS = 5
CAP_PROP_POS_MSEC = 0
CAP_PROP_FRAME_COUNT = 7
DEFAULT_FPS = 24.0

# Cache probed metadata so repeated loaders for the same file do not rescan it
_VIDEO_INFO_CACHE: dict[str, Tuple[int, int, float, float, int]] = {}


class VideoCapture:
    """Mock OpenCV VideoCapture using FFmpeg subprocess."""

    def __init__(self, video_file):
        self.video_file = str(video_file)
        # Get all metadata in ONE ffprobe call for speed (with caching)
        self.width, self.height, self.fps, self.duration, self.total_frames = self._get_video_info()
        self.frame_size_bytes = self.width * self.height  # grayscale = 1 byte per pixel
        self.current_frame_num = 0
        self.process = None

    def _get_video_info(self):
        """Return cached or freshly probed metadata for the current file."""
        cached = _VIDEO_INFO_CACHE.get(self.video_file)
        if cached:
            return cached

        info = self._probe_video_info()
        _VIDEO_INFO_CACHE[self.video_file] = info
        return info

    def _probe_video_info(self):
        """Get video dimensions, actual frame count, and duration using ffprobe."""
        probe_variants = [
            ('-count_packets', 'nb_read_packets'),
            ('-count_frames', 'nb_read_frames'),
        ]

        last_error = None
        for count_flag, frame_field in probe_variants:
            try:
                return self._run_ffprobe(count_flag, frame_field)
            except RuntimeError as exc:
                last_error = exc

        # If all probes failed, raise the last captured error
        raise RuntimeError(
            f"Unable to read video metadata for {self.video_file}: {last_error}"
        ) from last_error

    def _run_ffprobe(self, count_flag: str, frame_field: str):
        """Invoke ffprobe with the requested counting strategy."""
        cmd = [
            get_executable_path("ffprobe", config.ffprobe_path),
            '-v', 'error',
            count_flag,
            '-select_streams', 'v:0',
            '-show_entries', f'stream=width,height,{frame_field}:format=duration',
            '-of', 'csv=p=0',
            self.video_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffprobe failed")

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("ffprobe returned no output")

        stream_parts = lines[0].split(',')
        if len(stream_parts) < 3:
            raise RuntimeError("ffprobe stream output missing fields")

        try:
            width = int(stream_parts[0])
            height = int(stream_parts[1])
        except ValueError as exc:
            raise RuntimeError("Invalid width/height in ffprobe output") from exc

        frame_count = self._parse_frame_count(stream_parts[2])
        duration = self._parse_duration(lines[1] if len(lines) > 1 else None)

        # Calculate REAL FPS from actual frames and duration
        fps = frame_count / duration if duration > 0 else DEFAULT_FPS

        return width, height, fps, duration, frame_count

    def _parse_frame_count(self, value: str) -> int:
        """Convert a frame-count string to int, raising on failure."""
        try:
            # Some ffprobe builds return floats; ensure we coerce properly
            return int(float(value))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid frame count '{value}'") from exc

    def _parse_duration(self, value: Optional[str]) -> float:
        """Return a positive duration, falling back to a separate probe if needed."""
        if value:
            try:
                duration = float(value)
                if duration > 0:
                    return duration
            except ValueError:
                pass

        # Fallback probe for duration
        return self._get_duration_fallback()

    def _get_duration_fallback(self):
        """Fallback method to get duration from format info."""
        cmd = [
            get_executable_path("ffprobe", config.ffprobe_path),
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            self.video_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Unable to determine duration for {self.video_file}: {result.stderr.strip()}"
            )
        try:
            duration = float(result.stdout.strip())
        except ValueError as exc:
            raise RuntimeError("Invalid duration reported by ffprobe") from exc
        return duration

    def read(self):
        """Read next frame from video stream."""
        if self.process is None:
            # Start ffmpeg process on first read
            self.process = subprocess.Popen([
                get_executable_path("ffmpeg", config.ffmpeg_path),
                '-hide_banner',
                '-loglevel', 'error',
                '-nostats',
                '-i', self.video_file,
                '-f', 'rawvideo',
                '-pix_fmt', 'gray',  # Grayscale output (1 byte per pixel)
                'pipe:1'
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)

        # Read one frame worth of bytes
        frame_bytes = self.process.stdout.read(self.frame_size_bytes)

        if len(frame_bytes) < self.frame_size_bytes:
            # End of video or error
            return False, None

        self.current_frame_num += 1
        # Return frame as bytearray for compatibility
        return True, bytearray(frame_bytes)

    def get(self, prop_id):
        """Get video property (OpenCV compatibility)."""
        if prop_id == CAP_PROP_FPS:
            return self.fps
        elif prop_id == CAP_PROP_POS_MSEC:
            # Calculate current timestamp from frame number
            return (self.current_frame_num / self.fps) * 1000
        elif prop_id == CAP_PROP_FRAME_COUNT:
            return self.total_frames
        return 0

    def isOpened(self):
        """Check if video is opened."""
        return True

    def release(self):
        """Release video resources."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


class VideoLoader:
    """A class that represents a video loader."""

    def __init__(self, video_file):
        self.cap = VideoCapture(video_file)
        self.frame_count = 0

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                raise StopIteration
            self.frame_count += 1
            if self.frame_count % config.FRAME_RATE == 0:
                return frame

    def get_frame_count(self):
        """Get the number of frames after sampling by FRAME_RATE."""
        total = self.cap.get(CAP_PROP_FRAME_COUNT)
        if total == 0:
            return 0
        # Ensure at least 1 frame for very short segments
        return max(1, int(total / config.FRAME_RATE))

    def release(self):
        self.cap.release()
