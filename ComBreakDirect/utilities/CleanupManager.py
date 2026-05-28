"""
CleanupManager - Centralized maintenance for segment and break cleanup.

This is the factory's maintenance crew - runs in the background cleaning up
old temporary files (segments and pre-rendered commercial breaks).
"""

import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional


class CleanupManager:
    """Handles periodic cleanup of temporary files (segments and commercial breaks)."""

    def __init__(self, segment_root: Path, break_renderer=None):
        """
        Initialize cleanup manager.

        Args:
            segment_root: Root directory for HLS segments
            break_renderer: Optional CommercialBreakRenderer instance for break cleanup
        """
        self.segment_root = segment_root
        self.break_renderer = break_renderer
        self._cleanup_thread: Optional[threading.Thread] = None

    def start_cleanup_thread(self,
                            segment_max_age_minutes: int = 15,
                            break_max_age_hours: int = 4,
                            cleanup_interval_minutes: int = 5):
        """
        Start background cleanup thread.

        Args:
            segment_max_age_minutes: Delete segments older than this
            break_max_age_hours: Delete breaks older than this
            cleanup_interval_minutes: How often to run cleanup
        """
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            print("[CLEANUP_MANAGER] Cleanup thread already running")
            return

        def cleanup_loop():
            while True:
                time.sleep(cleanup_interval_minutes * 60)
                try:
                    # Clean old segments
                    self._cleanup_old_segments(segment_max_age_minutes)

                    # Clean old breaks if we have a renderer
                    if self.break_renderer:
                        self._cleanup_old_breaks(break_max_age_hours)

                except Exception as e:
                    print(f"[CLEANUP_MANAGER] Cleanup error: {e}")

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True, name="CleanupManager")
        self._cleanup_thread.start()
        print(f"[CLEANUP_MANAGER] Started cleanup thread (segments: {segment_max_age_minutes}min, "
              f"breaks: {break_max_age_hours}hr, interval: {cleanup_interval_minutes}min)")

    def _cleanup_old_segments(self, max_age_minutes: int):
        """Remove old HLS segment files."""
        cutoff_time = time.time() - (max_age_minutes * 60)
        cleaned_count = 0

        for channel_dir in self.segment_root.iterdir():
            if not channel_dir.is_dir():
                continue

            for segment_file in channel_dir.glob("*.ts"):
                try:
                    if segment_file.stat().st_mtime < cutoff_time:
                        segment_file.unlink(missing_ok=True)
                        cleaned_count += 1
                except Exception as e:
                    print(f"[CLEANUP_MANAGER] Error removing segment {segment_file.name}: {e}")

        if cleaned_count > 0:
            print(f"[CLEANUP_MANAGER] Cleaned up {cleaned_count} old segment(s)")

    def _cleanup_old_breaks(self, max_age_hours: int):
        """Remove old pre-rendered commercial break files."""
        if not self.break_renderer:
            return

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        stale_ids = []

        # Find stale breaks in cache
        for break_id, metadata in self.break_renderer.break_cache.items():
            created_at = metadata.get('created_at')
            if not isinstance(created_at, datetime):
                continue
            if created_at < cutoff_time:
                stale_ids.append(break_id)

        # Remove them
        for break_id in stale_ids:
            try:
                path = Path(self.break_renderer.break_cache[break_id]['path'])
                if path.exists():
                    path.unlink()
                del self.break_renderer.break_cache[break_id]
            except Exception as e:
                print(f"[CLEANUP_MANAGER] Error removing break {break_id}: {e}")

        if stale_ids:
            print(f"[CLEANUP_MANAGER] Cleaned up {len(stale_ids)} old commercial break(s)")
