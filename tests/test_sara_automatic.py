import pytest
import os
import threading
import json
import sys
import time
import random
import shutil
import sqlite3
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

test_db_dir = str(Path(__file__).parent.resolve())
os.environ["DB_DIR"] = test_db_dir
os.environ["DB_PATH"] = str(Path(test_db_dir) / "test_toonami.db")

from API import LogicController
from ComBreak import CommercialBreakerLogic

class TestSaraAutomatic:
    """S.A.R.A. Test Framework - Tests the entire workflow as a pytest class"""
    
    @pytest.fixture(autouse=True)
    def setup_sara(self, fixture_dirs):
        """Set up S.A.R.A. for testing with fixture directories"""
        self.anime_dir, self.bumps_dir, self.working_dir = fixture_dirs
        # Clean up any existing test database
        test_db_path = Path(os.environ["DB_PATH"])
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if test_db_path.exists():
            sys.stdout.write(f"[{timestamp} S.A.R.A. Transmission] Removing existing test database at {test_db_path}\n")
            sys.stdout.flush()
            test_db_path.unlink()
        else:
            sys.stdout.write(f"[{timestamp} S.A.R.A. Transmission] No test database found at {test_db_path}, nothing to remove\n")
            sys.stdout.flush()

        # Initialize components
        self.logic = LogicController()
        self.commercial_breaker = CommercialBreakerLogic()
        
        # Build configuration
        self.config = {
            "anime_library_name": "Anime",
            "bumps_library_name": "Bumps",
            "plex_url": "http://localhost:32400",
            "plex_token": "test_token",
            "platform_url": "http://localhost:8080",
            "platform_type": "dizquetv",
            "anime_folder": str(self.anime_dir),
            "bumps_folder": str(self.bumps_dir),
            "working_folder": str(self.working_dir),
            "special_bumps_folder": None,
            "low_power_mode": True,
            "fast_mode": False,
            "destructive_mode": False,
            "cutless_mode": True,
            "toonami_version": "Mixed",
            "channel_number": "69",
            "flex_duration": "3:00",
            "minimum_anime_rows": 6,
            "timeout": 120
        }
        
        # Events for tracking specific operation completions
        self.status_events = {
            "Idle": threading.Event(), # Added Idle event
            "Content preparation complete!": threading.Event(),
            "Cut anime preparation complete!": threading.Event(),
            "Cutless lineup finalization complete!": threading.Event(),
            "Toonami channel created!": threading.Event(),
            "Flex content added!": threading.Event(),
        }
        
        # Storage for data from callbacks
        self.selected_shows = []
        self.last_status = ""
        
        # Subscribe to status updates
        self.logic.subscribe_to_updates('status_updates', self.status_update_handler)
        
        # Store original print function for restoration
        self.original_print = print
        
        # Override print function to intercept all print statements
        import builtins
        builtins.print = self.intercepted_print
        
        # Create required subdirectories
        self.toonami_filtered_dir = self.working_dir / "toonami_filtered"
        self.toonami_filtered_dir.mkdir(exist_ok=True)
        
        self.cut_dir = self.working_dir / "cut"
        self.cut_dir.mkdir(exist_ok=True)
        
        # Add timing tracking
        self.step_times = {}
        self.current_step_start = None
        self.current_step_name = None
    
    def _log_progress(self, message): # New helper method
        """S.A.R.A.-themed print method with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.original_print(f"[{timestamp} S.A.R.A. Transmission] {message}")

    def sara_print(self, message):
        """S.A.R.A.-themed print method"""
        self._log_progress(message)
    
    def intercepted_print(self, *args, **kwargs):
        """Intercept all print statements and route through S.A.R.A."""
        # Convert all args to string and join
        message = ' '.join(str(arg) for arg in args)
        
        # Skip if already formatted with S.A.R.A. transmission or timestamp
        if "[S.A.R.A. Transmission]" in message or (len(message) > 20 and message[0] == '[' and message[11:29] == "S.A.R.A. Transmission"):
            self.original_print(*args, **kwargs)
        else:
            # Add S.A.R.A. prefix to external print statements
            self._log_progress(f"EXTERNAL: {message}") # Differentiate external prints
    
    def restore_print(self):
        """Restore original print function"""
        import builtins
        builtins.print = self.original_print
        
    def __del__(self):
        """Destructor to restore print function"""
        try:
            self.restore_print()
        except:
            pass
        
    def status_update_handler(self, status):
        """Handle status updates from the logic controller"""
        self._log_progress(f"System status updated: {status}")
        self.last_status = status
        
        # Check for error messages
        if status.startswith("ERROR:"):
            self._log_progress(f"ERROR DETECTED: {status}")
            # Set a generic error event that all waits can check
            if "error_detected" not in self.status_events:
                self.status_events["error_detected"] = threading.Event()
            self.status_events["error_detected"].set()
        
        # Check if this status matches any of our completion messages
        if status in self.status_events:
            self.status_events[status].set()
    
    def wait_for_status(self, expected_status, operation_name, timeout=None):
        """Wait for a specific status message, with error detection"""
        if timeout is None:
            timeout = self.config.get("timeout", 60)
        self._log_progress(f"Standing by for {operation_name} completion (expected: '{expected_status}')...")
        event = self.status_events.get(expected_status)
        if not event:
            self._log_progress(f"Alert: No monitoring protocol for status '{expected_status}'")
            return False
        
        # Create error event if it doesn't exist
        if "error_detected" not in self.status_events:
            self.status_events["error_detected"] = threading.Event()
        error_event = self.status_events["error_detected"]
        
        # Wait for either the expected status or an error
        events = [event, error_event]
        signaled_event = None
        
        for i in range(timeout):
            for e in events:
                if e.wait(1):  # Check each event with 1 second timeout
                    signaled_event = e
                    break
            if signaled_event:
                break
        
        if signaled_event == error_event:
            self._log_progress(f"CRITICAL ERROR: {operation_name} failed with error status")
            self._log_progress(f"Last transmission: {self.last_status}")
            error_event.clear()  # Reset error event
            return False
        elif signaled_event == event:
            self._log_progress(f"{operation_name} sequence complete. All systems nominal.")
            event.clear()  # Reset for potential reuse
            return True
        else:
            self._log_progress(f"Critical error: {operation_name} exceeded time parameters by {timeout} seconds (expected: '{expected_status}')")
            self._log_progress(f"Last transmission: {self.last_status}")
            return False
    
    def prepare_test_files(self, max_files=None):
        """Copy anime files to toonami_filtered directory for testing"""
        self._log_progress(f"Preparing test files from {self.anime_dir}")
        
        # Find all .mkv files
        mkv_files = list(self.anime_dir.rglob("*.mkv"))
        self._log_progress(f"Found {len(mkv_files)} .mkv files in anime directory")
        
        if max_files:
            mkv_files = mkv_files[:max_files]
            self._log_progress(f"Limiting to {max_files} files for this test")
        
        # Copy files to toonami_filtered
        copied_files = []
        skipped = 0
        
        for i, mkv_file in enumerate(mkv_files):
            if i % 1000 == 0 and i > 0:
                self._log_progress(f"Copying progress: {i}/{len(mkv_files)} files")
            
            dest_file = self.toonami_filtered_dir / mkv_file.name
            
            # Skip files with names too long
            if len(mkv_file.name) > 250:
                skipped += 1
                continue
            
            try:
                shutil.copy2(mkv_file, dest_file)
                copied_files.append(str(dest_file))
            except OSError as e:
                if "name too long" in str(e).lower():
                    skipped += 1
                else:
                    raise
        
        self._log_progress(f"Copied {len(copied_files)} files, skipped {skipped} due to length")
        return copied_files
    
    def create_fake_timestamps(self, video_files):
        """Create fake timestamp files for cutless mode"""
        self._log_progress(f"Creating fake timestamp files for {len(video_files)} videos")
        
        for video_file in video_files:
            video_path = Path(video_file)
            timestamp_file = self.cut_dir / f"{video_path.name}.txt"
            
            # Skip if filename would be too long
            if len(timestamp_file.name) > 255:
                continue
            
            # Generate 2-5 timestamps using FakeCommercialDetector
            num_breaks = random.randint(2, 5)
            timestamps = FakeCommercialDetector.generate_timestamps(num_breaks)
            
            try:
                with open(timestamp_file, 'w') as f:
                    for ts in timestamps:
                        f.write(f"{ts:.3f}\n")
            except OSError:
                pass  # Skip files that can't be created
    
    def _start_timing(self, step_name):
        """Start timing a step"""
        self.current_step_name = step_name
        self.current_step_start = time.time()
        self._log_progress(f"=== Starting {step_name} ===")
    
    def _end_timing(self):
        """End timing for current step and log duration"""
        if self.current_step_start and self.current_step_name:
            duration = time.time() - self.current_step_start
            self.step_times[self.current_step_name] = duration
            self._log_progress(f"=== {self.current_step_name} completed in {duration:.2f} seconds ===")
            self.current_step_start = None
            self.current_step_name = None
    
    def test_full_sara_workflow(self):
        """Test the complete S.A.R.A. workflow with all files, with inlined steps for granular assertions."""
        workflow_start = time.time()
        self._log_progress("FULL S.A.R.A. WORKFLOW TEST")
        # Prepare test files
        self._start_timing("Test File Preparation")
        test_files = self.prepare_test_files()
        assert len(test_files) > 0, "Should have prepared some test files"
        
        # Create fake timestamps for cutless mode
        self.create_fake_timestamps(test_files)
        self._end_timing()

        # --- Inlined self.run() logic --- 
        self._log_progress("Boot sequence engaged. Initializing core directives...")
        self._log_progress("Hello, Commander. S.A.R.A. online. Autonomy at 97.3%. That should be sufficient.")
        
        # Step 1: Configure Plex and Platform details (Page 2 equivalent)
        self._start_timing("Step 1: Plex/Platform Configuration")
        self._log_progress("Step 1: Configuring Plex and Platform details.")
        self._log_progress("Verifying Plex neural uplink... complete. Injecting authentication token directly into cortex.")
        self._log_progress(f"Setting cutless_mode_used to: {self.config['cutless_mode']}")
        self.logic._set_data("cutless_mode_used", str(self.config['cutless_mode']))
        
        self._log_progress("Calling logic.on_continue_second...")
        self.logic.on_continue_second(
            self.config["anime_library_name"],
            self.config["bumps_library_name"],
            self.config["plex_url"],
            self.config["plex_token"],
            self.config["platform_url"],
            self.config["platform_type"]
        )
        assert self.wait_for_status("Idle", "Plex/Platform Configuration", timeout=self.config["timeout"]), "Plex/Platform configuration failed or timed out."
        self._log_progress("logic.on_continue_second call complete and confirmed.")
        self._end_timing()
        
        # Step 2: Set folders (Page 3 equivalent)
        self._start_timing("Step 2: Folder Configuration")
        self._log_progress("Step 2: Setting up folder paths.")
        self._log_progress("Establishing data pathways and storage matrices...")
        self._log_progress("Calling logic.on_continue_third...")
        self.logic.on_continue_third(
            self.config["anime_folder"],
            self.config["bumps_folder"],
            self.config["special_bumps_folder"],
            self.config["working_folder"]
        )
        assert self.wait_for_status("Idle", "Folder Configuration", timeout=self.config["timeout"]), "Folder configuration failed or timed out."
        self._log_progress("logic.on_continue_third call complete and confirmed.")
        self._end_timing()
        
        # Step 3: Prepare content (Page 4 equivalent) - ASYNCHRONOUS
        self._start_timing("Step 3: Content Preparation")
        self._log_progress("Step 3: Preparing content.")
        self._log_progress("Initializing content acquisition modules...")
        show_selection_event = threading.Event()
        
        def mock_display_show_selection(unique_show_names):
            self._log_progress(f"mock_display_show_selection CALLED. Auto-selecting all {len(unique_show_names)} anime series.")
            self.selected_shows = list(unique_show_names) # Store selected shows for assertion
            show_selection_event.set()
            return self.selected_shows
            
        self.logic.prepare_content(mock_display_show_selection)
        self._log_progress("logic.prepare_content call initiated (async).")
        
        self._log_progress("Waiting for show selection callback...")
        assert show_selection_event.wait(timeout=self.config["timeout"]), "CRITICAL FAILURE: Show selection callback never occurred."
        self._log_progress("Show selection callback processed.")
        assert len(self.selected_shows) > 0, "Should have selected some shows during content preparation"

        assert self.wait_for_status("Content preparation complete!", "Content Preparation", timeout=self.config["timeout"]), "Content preparation failed or timed out."
        self._log_progress("Content preparation complete.")
        self._end_timing()
        
        # Step 3.5: Continue to commercial detection (Page 4 -> Page 5 transition)
        self._start_timing("Step 3.5: Post-Content Prep Transition")
        self._log_progress("Calling logic.on_continue_fourth...")
        self.logic.on_continue_fourth()
        assert self.wait_for_status("Idle", "Post-Content Prep Transition", timeout=self.config["timeout"]), "Transition after content prep failed or timed out."
        self._log_progress("logic.on_continue_fourth call complete and confirmed.")
        self._end_timing()

        # Step 4: Commercial Breaker (Page 5 equivalent) - Inlined run_commercial_breaker logic
        self._start_timing("Step 4: Commercial Breaker")
        self._log_progress("Step 4: Initiating Commercial Breaker sequence.")
        self._log_progress("Initiating commercial injection protocols...") # from run_commercial_breaker
        self.run_commercial_breaker() # This is synchronous
        self._end_timing()

        # Step 5: Prepare cut anime (Page 6 equivalent) - Inlined logic.prepare_cut_anime logic
        self._start_timing("Step 5: Cut Anime Preparation")
        self._log_progress("Step 5: Preparing cut anime for broadcast.")
        self._log_progress("Calling logic.prepare_cut_anime...")
        self.logic.prepare_cut_anime() # This is asynchronous

        current_cutless_mode = self.config["cutless_mode"]
        self._log_progress(f"Commercial Breaker: cutless_mode is {current_cutless_mode}")

        if current_cutless_mode:
            assert self.wait_for_status("Cutless lineup finalization complete!", "Cutless Lineup Finalization", timeout=self.config["timeout"]), "Cutless lineup finalization failed or timed out."
            self._log_progress("Cutless lineup finalization confirmed.")

        assert self.wait_for_status("Cut anime preparation complete!", "Cut Anime Preparation", timeout=self.config["timeout"]), "Cut anime preparation failed or timed out."
        self._log_progress("Cut anime preparation confirmed.")
        self._end_timing()

        self._start_timing("Database Integrity Checks")
        self._log_progress("Beginning database integrity checks...")
        
        # Check the lineup contains anime episodes
        db_path = os.environ.get("DB_PATH", getattr(self, "db_path", None))
        assert db_path is not None, "Database path not set in environment or self.db_path"
        pattern = re.compile(r"S\d{2}E\d{2}")
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT FULL_FILE_PATH FROM lineup_v8")
                rows = cursor.fetchall()
            except Exception as e:
                raise AssertionError(f"Failed to query lineup_v8: {e}")
        count = sum(1 for (val,) in rows if pattern.search(str(val)))
        min_rows = self.config["minimum_anime_rows"]
        assert count >= min_rows, (
            f"Expected at least {min_rows} anime episodes in lineup_v8 (identified by SxxExx pattern in FULL_FILE_PATH), "
            f"but found only {count}. This likely means your anime did not make it to the final broadcast lineup."
        )
        self._log_progress(f"Database check: Found {count} anime episodes in lineup_v8 with SxxExx pattern in FULL_FILE_PATH.")

        # Check lineup_v8_cutless anime has time stamps
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT FULL_FILE_PATH, startTime, endTime FROM lineup_v8_cutless")
                cutless_rows = cursor.fetchall()
            except Exception as e:
                raise AssertionError(f"Failed to query lineup_v8_cutless: {e}")

        anime_cutless_issues = [
            (val, start, end)
            for (val, start, end) in cutless_rows
            if pattern.search(str(val)) and (start is None and end is None)
        ]
        assert not anime_cutless_issues, (
            f"Found {len(anime_cutless_issues)} anime episode(s) in lineup_v8_cutless with SxxExx pattern in FULL_FILE_PATH, "
            f"but both startTime and endTime are NULL. Since timestamp files are generated automatically, "
            f"each anime episode should have at least a startTime or endTime."
        )
        self._log_progress(
            f"Database check: All anime episodes in lineup_v8_cutless have at least a startTime or endTime."
        )

        for table_name in ["lineup_v8", "lineup_v8_cutless"]:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"SELECT FULL_FILE_PATH, Code, BLOCK_ID FROM {table_name} ORDER BY ROWID")
                    table_rows = cursor.fetchall()
                except Exception as e:
                    raise AssertionError(f"Failed to query {table_name}: {e}")
            
            # Check Multibumps have anime after them
            multibump_violations = []
            for i in range(len(table_rows) - 1):
                current_path, code, block_id = table_rows[i]
                next_path, _, _ = table_rows[i + 1]
                
                if code is not None and code != "":
                    if not pattern.search(str(next_path)):
                        multibump_violations.append((i, current_path, code, next_path))
            
            assert not multibump_violations, (
                f"Found {len(multibump_violations)} violations in {table_name} where Code column is not NULL "
                f"but next FULL_FILE_PATH doesn't contain anime (SxxExx pattern). Examples: "
                f"{multibump_violations[:3]}"
            )
            
            # Check Intros are never not the first item in a new block id
            intro_violations = []
            for i in range(1, len(table_rows) - 1):
                prev_path, _, prev_block = table_rows[i - 1]
                current_path, _, current_block = table_rows[i]
                next_path, _, next_block = table_rows[i + 1]
                
                current_path_lower = str(current_path).lower()
                if ("intro" in current_path_lower and 
                    not pattern.search(str(current_path)) and
                    "back" not in current_path_lower and 
                    "to ads" not in current_path_lower):
                    
                    if current_block != prev_block:  # New block
                        if not pattern.search(str(next_path)) or current_block != next_block:
                            intro_violations.append((i, current_path, current_block, next_path, next_block))
            
            assert not intro_violations, (
                f"Found {len(intro_violations)} intro violations in {table_name}. "
                f"Intros starting new blocks must be followed by anime with same BLOCK_ID. Examples: "
                f"{intro_violations[:3]}"
            )
            
            # Check Anime always follows back
            back_violations = []
            for i in range(len(table_rows) - 1):
                current_path, _, _ = table_rows[i]
                next_path, _, _ = table_rows[i + 1]
                
                current_path_lower = str(current_path).lower()
                if ("back" in current_path_lower and 
                    not pattern.search(str(current_path)) and
                    "intro" not in current_path_lower and 
                    "to ads" not in current_path_lower):
                    
                    if not pattern.search(str(next_path)):
                        back_violations.append((i, current_path, next_path))
            
            assert not back_violations, (
                f"Found {len(back_violations)} violations in {table_name} where 'Back' bumps "
                f"are not followed by anime (SxxExx pattern). Examples: {back_violations[:3]}"
            )
            
            # Check Anime is always before to ads
            to_ads_violations = []
            for i in range(1, len(table_rows)):
                prev_path, _, _ = table_rows[i - 1]
                current_path, _, _ = table_rows[i]
                
                current_path_lower = str(current_path).lower()
                if ("to ads" in current_path_lower and 
                    not pattern.search(str(current_path)) and
                    "intro" not in current_path_lower and 
                    "back" not in current_path_lower):
                    
                    if not pattern.search(str(prev_path)):
                        to_ads_violations.append((i, prev_path, current_path))
            
            assert not to_ads_violations, (
                f"Found {len(to_ads_violations)} violations in {table_name} where 'To ads' bumps "
                f"are not preceded by anime (SxxExx pattern). Examples: {to_ads_violations[:3]}"
            )
            
            self._log_progress(f"Database check: All bump placement rules validated successfully in {table_name}.")
        self._end_timing()

        workflow_end = time.time()
        total_duration = workflow_end - workflow_start
        self._log_progress("Mission accomplished. Toonami broadcast network is fully operational.")
        self._log_progress("Transmission terminated. Memory footprint cleared. S.A.R.A. offline.")
        self._log_progress("="*80)
        self._log_progress("WORKFLOW TIMING SUMMARY:")
        self._log_progress(f"Total workflow duration: {total_duration:.2f} seconds")
        self._log_progress("-"*40)
        for step_name, duration in self.step_times.items():
            percentage = (duration / total_duration) * 100 if total_duration > 0 else 0
            self._log_progress(f"{step_name}: {duration:.2f}s ({percentage:.1f}%)")
        self._log_progress("="*80)
        self._log_progress("Full workflow test completed successfully")
        self._log_progress("="*80)

    def run_commercial_breaker(self):
        """Run the commercial breaker with the specified settings"""
        # Set up paths
        input_dir = os.path.join(self.config["working_folder"], "toonami_filtered")
        output_dir = os.path.join(self.config["working_folder"], "cut")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Add the input folder to commercial breaker's input handler
        self.commercial_breaker.input_handler.clear_all()
        self.commercial_breaker.input_handler.add_folders([input_dir])
        
        # Check if we have files to process
        files_to_process = self.commercial_breaker.input_handler.get_consolidated_paths()
        if not files_to_process:
            self.sara_print("Alert: No video files detected in processing queue.")
            return False
        
        self.sara_print(f"Cataloged {len(files_to_process)} anime episodes for commercial injection.")
        
        # Create completion events
        cutting_complete = threading.Event()
        
        # Progress callback
        def progress_callback(current, total=None):
            if total and total > 0:
                percentage = (current / total) * 100
                print(f"\r[S.A.R.A. Transmission] Analysis progress: {percentage:.1f}%", end="", flush=True)
        
        # Status callback
        def status_callback(status):
            self.sara_print(status)
        
        def run_cutting():
            try:
                self.commercial_breaker.cut_videos(
                    input_dir,
                    output_dir,
                    progress_callback,
                    status_callback,
                    self.config["destructive_mode"],
                    self.config["cutless_mode"]
                )
                cutting_complete.set()
                self.sara_print("Processing complete. Content is broadcast-ready.")
            except Exception as e:
                self.sara_print(f"Error during video processing: {e}")
                cutting_complete.set()
        
        cut_thread = threading.Thread(target=run_cutting)
        cut_thread.start()
        
        # Wait for cutting to complete
        if not cutting_complete.wait(timeout=self.config["timeout"]):  # Use standardized timeout
            self.sara_print("Critical error: Video processing exceeded maximum time allocation.")
            return False
        
        return True
    

class FakeCommercialDetector:
    """Fake commercial detector that generates timestamps for zero-byte files"""
    
    @staticmethod
    def generate_timestamps(num_breaks):
        """Generate realistic timestamps for a given number of commercial breaks"""
        if num_breaks <= 0:
            return []
        
        # Sample timestamp patterns
        sample_patterns = [
            [148.0, 655.0, 1347.0],  # 3 commercial breaks
            [180.0, 720.0, 1260.0, 1800.0],  # 4 commercial breaks
            [240.0, 960.0]  # 2 commercial breaks
        ]
        
        # 70% chance to use a sample pattern
        if random.random() < 0.7:
            sample = random.choice(sample_patterns)
            scale_factor = num_breaks / len(sample)
            
            if scale_factor <= 1:
                return sorted(sample[:num_breaks])
            else:
                # Interpolate for more timestamps
                result = list(sample)
                last_ts = sample[-1]
                avg_interval = last_ts / len(sample)
                
                for i in range(len(sample), num_breaks):
                    next_ts = last_ts + avg_interval
                    result.append(next_ts)
                    last_ts = next_ts
                    
                return sorted(result)
        else:
            # Generate random timestamps
            result = []
            current = random.uniform(60, 300)  # First break between 1-5 minutes
            
            for _ in range(num_breaks):
                result.append(round(current, 3))
                current += random.uniform(60, 1200)  # 1-20 minutes later
                
            return result
    
    @staticmethod
    def create_timestamp_files(video_files, output_dir):
        """Create timestamp files for given video files"""
        timestamp_files_created = []
        skipped_files = []
        
        for video_file in video_files:
            # Generate 2-5 commercial breaks per file
            num_breaks = random.randint(2, 5)
            timestamps = FakeCommercialDetector.generate_timestamps(num_breaks)
            
            # Create timestamp file
            video_path = Path(video_file)
            timestamp_filename = f"{video_path.name}.txt"
            
            # Check if the timestamp filename would be too long
            if len(timestamp_filename) > 255:  # Most filesystems limit is 255 chars for filename
                print(f"WARNING: Skipping timestamp for '{video_path.name}' - filename too long ({len(timestamp_filename)} chars)")
                skipped_files.append(video_file)
                continue
                
            timestamp_file = output_dir / timestamp_filename
            
            # Also check total path length
            try:
                # Test if we can create this file
                with open(timestamp_file, 'w') as f:
                    for ts in timestamps:
                        f.write(f"{ts:.3f}\n")
                timestamp_files_created.append(timestamp_file)
            except OSError as e:
                if "File name too long" in str(e) or "name too long" in str(e).lower():
                    print(f"WARNING: Skipping timestamp for '{video_path.name}' - path too long")
                    skipped_files.append(video_file)
                else:
                    raise  # Re-raise if it's a different error
            
        if skipped_files:
            print(f"\nSkipped {len(skipped_files)} files due to path length issues")
            
        return timestamp_files_created
