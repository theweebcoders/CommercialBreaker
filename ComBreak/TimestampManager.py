import os
from pathlib import Path
import config

class TimestampManager:
    def __init__(self, input_handler):
        self.input_handler = input_handler

    # ------------------- Timestamp Cleanup Method -------------------
    def cleanup_timestamps(self, output_path, progress_callback=None, status_callback=None):
        """
        Clean up timestamp files by applying the reduction logic to remove points that are too close together.
        This method reads each timestamp file, applies the reduction, and writes back the cleaned-up timestamps.
        """
        # Find all timestamp files
        timestamp_files = []
        if self.input_handler.has_input():
            # Enhanced mode - look for timestamp files in the output folders
            for input_file in self.input_handler.get_consolidated_paths():
                output_dir = self.input_handler.get_output_path_for_file(input_file, output_path)
                if output_dir.exists():
                    for file in output_dir.glob("*.txt"):
                        # Exclude specific files like plex_timestamps.txt and failedtocut.txt
                        if file.name not in ["plex_timestamps.txt", "failedtocut.txt"]:
                            timestamp_files.append(file)
        else:
            # Legacy folder mode - walk through the output directory
            for dirpath, _, filenames in os.walk(output_path):
                for filename in filenames:
                    # Exclude specific files like plex_timestamps.txt and failedtocut.txt
                    if filename.endswith('.txt') and filename not in ["plex_timestamps.txt", "failedtocut.txt"]:
                        timestamp_files.append(Path(dirpath) / filename)

        total_files = len(timestamp_files)
        if status_callback:
            status_callback(f"Found {total_files} timestamp files to clean up")

        # Process each timestamp file
        for i, timestamp_file in enumerate(timestamp_files):
            try:
                if status_callback:
                    status_callback(f"Cleaning timestamp file {i+1} of {total_files}: {timestamp_file.name}")

                # Read the timestamps
                with open(timestamp_file, "r") as f:
                    timestamps = [float(line.strip()) for line in f if line.strip()] # Ensure empty lines are skipped

                # Apply the reduction logic
                reduced_timestamps = self.reduce_timestamps(timestamps)

                # Write back the reduced timestamps
                with open(timestamp_file, "w") as f:
                    for timestamp in reduced_timestamps:
                        f.write(f"{timestamp}\n")

                if progress_callback:
                    progress_callback(i + 1, total_files)

            except Exception as e:
                if status_callback:
                    status_callback(f"Error cleaning timestamp file {timestamp_file.name}: {e}")

    @staticmethod
    def reduce_timestamps(timestamps):
        """
        Eliminate timestamp points using a two-stage process:
        1. First remove timestamps that are less than starting buffer
        2. Then remove timestamps that are too close to the previous ones
        """
        if not timestamps:
            return []

        # Stage 1: Remove timestamps less than START_BUFFER
        filtered_by_buffer = [t for t in timestamps if t >= config.START_BUFFER]

        if not filtered_by_buffer:
            return []

        # Stage 2: Remove timestamps that are too close to the previous ones
        filtered_timestamps = [filtered_by_buffer[0]] # Start with the first valid timestamp

        for i in range(1, len(filtered_by_buffer)):
            timestamp = filtered_by_buffer[i]
            # Keep timestamp if it's sufficiently far from the last *kept* timestamp
            if timestamp - filtered_timestamps[-1] > config.TIMESTAMP_THRESHOLD:
                filtered_timestamps.append(timestamp)

        return filtered_timestamps

    # ------------------- Read Timestamps Method -------------------
    def read_timestamps(self, input_path, output_path, total_frames, video_files_data, total_videos,
                        file_counter, unprocessed_files_manager, progress_callback, status_callback):
        # Check if we're using enhanced input handling or legacy folder mode
        if self.input_handler.has_input():
            # Enhanced mode - look for matching files in plex_timestamps.txt
            input_files = self.input_handler.get_consolidated_paths()

            # Group files by their parent directory to read each plex_timestamps.txt only once
            files_by_dir = {}
            for f in input_files:
                parent_dir = str(Path(f).parent)
                if parent_dir not in files_by_dir:
                    files_by_dir[parent_dir] = []
                files_by_dir[parent_dir].append(f)

            for base_path_str, files_in_dir in files_by_dir.items():
                base_path = Path(base_path_str)
                plex_file_path = base_path / "plex_timestamps.txt"

                # Skip if no plex_timestamps.txt found in this directory
                if not plex_file_path.exists():
                    continue

                if status_callback:
                    status_callback(f"Reading Plex timestamps from: {plex_file_path}")

                plex_data = {}
                try:
                    with open(plex_file_path, "r", encoding='utf-8') as plex_file:
                        for line in plex_file:
                            if " = " in line:
                                plex_filename, timestamp = line.rsplit(" = ", 1)
                                plex_data[plex_filename.strip()] = timestamp.strip()
                except Exception as e:
                    if status_callback:
                        status_callback(f"Error reading {plex_file_path}: {e}")
                    continue # Skip this plex file if error reading

                # Check each file currently in the unprocessed manager against the plex data
                # Iterate over a copy of the list as we might modify it
                for video_file in list(unprocessed_files_manager.get_files()):
                    original_file, dirpath, filename = video_file.values()

                    # Only process files that belong to the current directory being checked
                    if str(Path(original_file).parent) != base_path_str:
                        continue

                    if filename in plex_data:
                        try:
                            output_dir = self.input_handler.get_output_path_for_file(original_file, output_path)
                            output_dir.mkdir(parents=True, exist_ok=True)

                            timestamp_file_path = output_dir / f"{filename}.txt"
                            with open(timestamp_file_path, "w") as output_file:
                                output_file.write(plex_data[filename] + "\n")

                            if status_callback:
                                status_callback(f"Found Plex timestamp for {filename}, wrote to {timestamp_file_path}")

                            # Remove from unprocessed manager
                            unprocessed_files_manager.remove_file(str(original_file), str(dirpath), filename)
                        except Exception as e:
                            if status_callback:
                                status_callback(f"Error processing Plex timestamp for {filename}: {e}")
        else:
            # Legacy folder mode
            plex_file_path = Path(input_path) / "plex_timestamps.txt"

            # Check if plex_timestamps.txt exists, if not, skip this step
            if not plex_file_path.exists():
                if status_callback:
                    status_callback(f"Plex timestamps file not found at: {plex_file_path}")
                return

            if status_callback:
                status_callback(f"Reading Plex timestamps from: {plex_file_path}")

            plex_data = {}
            try:
                with open(plex_file_path, "r", encoding='utf-8') as plex_file:
                    for line in plex_file:
                        if " = " in line:
                            plex_filename, timestamp = line.rsplit(" = ", 1)
                            plex_data[plex_filename.strip()] = timestamp.strip()
            except Exception as e:
                if status_callback:
                    status_callback(f"Error reading {plex_file_path}: {e}")
                return # Stop if error reading the main plex file

            # Iterate over a copy of the list as we might modify it
            for video_file in list(unprocessed_files_manager.get_files()):
                original_file, dirpath, filename = video_file.values()

                if filename in plex_data:
                    try:
                        output_dir = Path(output_path) / Path(dirpath).relative_to(input_path)
                        output_dir.mkdir(parents=True, exist_ok=True)

                        timestamp_file_path = output_dir / f"{filename}.txt"
                        with open(timestamp_file_path, "w") as output_file:
                            output_file.write(plex_data[filename] + "\n")

                        if status_callback:
                            status_callback(f"Found Plex timestamp for {filename}, wrote to {timestamp_file_path}")

                        # Remove from unprocessed manager
                        unprocessed_files_manager.remove_file(str(original_file), str(dirpath), filename)
                    except Exception as e:
                        if status_callback:
                            status_callback(f"Error processing Plex timestamp for {filename}: {e}")
