import os
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
from ComBreak.DurationManager import get_duration_manager


class BumpCalculator:
    """Compute and persist durations for Toonami bump assets."""

    def __init__(self, status_callback: Optional[Callable[[str], None]] = None) -> None:
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        self.duration_manager = get_duration_manager()
        self.status_callback = status_callback

    def _status(self, message: str) -> None:
        """Send status updates to both stdout and the optional callback."""
        print(message)
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as exc:  # Callback errors should not break execution
                print(f"Warning: status callback failed with error: {exc}")

    def run(self) -> None:
        """Calculate durations for all usable bumps and store them in the database."""
        self._status("Gathering bump file list from nice_list table...")

        if not self.db_manager.table_exists("nice_list"):
            self.error_manager.send_error_level(
                source="BumpCalculator",
                operation="run",
                message="Unable to calculate bump durations",
                details="Table 'nice_list' does not exist",
                suggestion="Run Lineup Prep to generate bump metadata before recalculating durations"
            )
            return

        try:
            rows = self.db_manager.fetchall(
                "SELECT FULL_FILE_PATH FROM nice_list WHERE TRIM(IFNULL(FULL_FILE_PATH, '')) <> ''"
            )
            file_paths = [row[0] for row in rows]
        except Exception as exc:
            self.error_manager.send_error_level(
                source="BumpCalculator",
                operation="run",
                message="Failed to load bump metadata",
                details=str(exc),
                suggestion="Verify the Toonami database is accessible and try again"
            )
            return

        if not file_paths:
            self.error_manager.send_warning(
                source="BumpCalculator",
                operation="run",
                message="No bump entries available",
                details="The nice_list table does not contain any usable bumps",
                suggestion="Add bump files and re-run Lineup Prep before preparing the channel"
            )
            return

        unique_paths = self._deduplicate_paths(file_paths)
        total = len(unique_paths)

        if total == 0:
            self.error_manager.send_warning(
                source="BumpCalculator",
                operation="run",
                message="No valid bump paths found",
                details="All bump entries had empty or duplicate file paths",
                suggestion="Inspect the nice_list table for invalid entries"
            )
            return

        self._status(f"Calculating durations for {total} bump files...")

        duration_rows: List[dict] = []
        missing_files: List[str] = []

        for index, raw_path in enumerate(unique_paths, start=1):
            display_name = Path(raw_path).name or raw_path
            self._status(f"[{index}/{total}] Measuring duration for {display_name}")

            duration_ms = self._probe_duration(raw_path)
            if duration_ms is None:
                missing_files.append(raw_path)
                continue

            duration_rows.append({
                "FULL_FILE_PATH": raw_path,
                "duration": int(round(duration_ms))
            })

        if not duration_rows:
            self.error_manager.send_error_level(
                source="BumpCalculator",
                operation="run",
                message="Failed to record bump durations",
                details="All bumps were skipped because their files were missing or unreadable",
                suggestion="Ensure the bump files are accessible from this machine and try again"
            )
            return

        # Deduplicate by FULL_FILE_PATH, keeping last occurrence
        seen = {}
        for row in duration_rows:
            seen[row["FULL_FILE_PATH"]] = row
        duration_rows = list(seen.values())

        self._status(f"Storing durations for {len(duration_rows)} bumps...")

        try:
            self.db_manager.replace_table_data('bump_durations', duration_rows)
        except Exception as exc:
            self.error_manager.send_error_level(
                source="BumpCalculator",
                operation="run",
                message="Failed to persist bump durations",
                details=str(exc),
                suggestion="Check database write permissions and retry"
            )
            return

        if missing_files:
            missing_sample = ", ".join(Path(path).name or path for path in missing_files[:5])
            sample_text = f" (examples: {missing_sample})" if missing_sample else ""
            self.error_manager.send_warning(
                source="BumpCalculator",
                operation="run",
                message=f"Skipped {len(missing_files)} bump files because they were unavailable",
                details=f"Files could not be accessed or ffprobe failed{sample_text}",
                suggestion="Verify these bumps exist at the recorded paths or update nice_list entries"
            )

        self._status("Bump duration calculation complete.")

    def _deduplicate_paths(self, paths: Iterable[str]) -> List[str]:
        seen = set()
        unique_paths = []
        for path in paths:
            normalized = self._normalize_path_string(path)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_paths.append(normalized)
        return unique_paths

    def _normalize_path_string(self, path: str) -> Optional[str]:
        if not path:
            return None
        cleaned = path.strip()
        if not cleaned:
            return None
        # Some entries may contain alternative paths separated by the Theta character
        if "Θ" in cleaned:
            cleaned = cleaned.split("Θ", 1)[0].strip()
        # Normalize redundant separators without touching leading slashes
        return os.path.normpath(cleaned)

    def _probe_duration(self, full_path: str) -> Optional[float]:
        try:
            return self.duration_manager.get_duration(full_path)
        except FileNotFoundError:
            return None
        except Exception as exc:
            self.error_manager.send_warning(
                source="BumpCalculator",
                operation="_probe_duration",
                message=f"Could not read duration for {full_path}",
                details=str(exc),
                suggestion="Confirm the file is accessible and not corrupted"
            )
            return None
