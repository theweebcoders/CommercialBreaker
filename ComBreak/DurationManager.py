import subprocess
import config
from ComBreak.utils import get_executable_path


class DurationManager:
    """Singleton manager for video duration extraction and caching."""

    _instance = None

    def __init__(self):
        if not hasattr(self, 'duration_cache'):
            self.duration_cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DurationManager, cls).__new__(cls)
        return cls._instance

    def get_duration(self, video_file_path):
        """
        Get video duration in milliseconds, using cache if available.

        Args:
            video_file_path: Path to the video file (str or Path)

        Returns:
            float: Duration in milliseconds

        Raises:
            Exception: If duration cannot be extracted
        """
        # Normalize path to string for consistent caching
        file_path = str(video_file_path)

        # Check cache first
        if file_path in self.duration_cache:
            return self.duration_cache[file_path]

        # Extract duration using ffprobe
        try:
            cmd = [
                get_executable_path("ffprobe", config.ffprobe_path),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"ffprobe failed with return code {result.returncode}: {result.stderr}")

            if not result.stdout.strip():
                raise Exception("ffprobe returned empty duration")

            duration_seconds = float(result.stdout.strip())
            duration_milliseconds = duration_seconds * 1000

            # Cache the result in milliseconds
            self.duration_cache[file_path] = duration_milliseconds

            return duration_milliseconds

        except ValueError as e:
            raise Exception(f"Could not parse duration as float: {result.stdout.strip()}") from e
        except Exception as e:
            raise Exception(f"Failed to extract duration from {file_path}: {str(e)}") from e

    def clear_cache(self):
        """Clear the duration cache."""
        self.duration_cache.clear()

    def get_cache_size(self):
        """Get the number of cached durations."""
        return len(self.duration_cache)


def get_duration_manager():
    """Get the singleton DurationManager instance."""
    return DurationManager()