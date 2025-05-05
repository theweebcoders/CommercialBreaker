import os
from pathlib import Path
import subprocess
import json
import config
# Import the utility function directly
from ComBreak.utils import get_executable_path

class ChapterExtractor:
    def __init__(self, input_handler):
        self.input_handler = input_handler

    # ------------------- Extract Chapters Methods -------------------
    def extract_chapters(self, input_path, output_path, unprocessed_files_manager, status_callback=None, progress_callback=None, reset_callback=None):
        total_videos = 0
        processed_videos = 0

        # Use enhanced input handler if available, otherwise fall back to legacy folder mode
        if self.input_handler.has_input():
            input_files = self.input_handler.get_consolidated_paths()
            total_videos = len(input_files)

            for i, file_path in enumerate(input_files):
                processed_videos += 1
                file_path_obj = Path(file_path)
                filename = file_path_obj.name

                if status_callback:
                    status_callback(f"Looking for chapters in {processed_videos} of {total_videos} videos")
                if progress_callback:
                    progress_callback(processed_videos, total_videos)

                if chapters := self.get_chapters(file_path):
                    # Log that we found chapters
                    if status_callback:
                        status_callback(f"Found chapters in {filename}")

                    # Determine output directory based on input file
                    output_dir = self.input_handler.get_output_path_for_file(file_path, output_path)
                    output_dir.mkdir(parents=True, exist_ok=True)

                    # Create and write chapters to a text file
                    with open(output_dir / f"{filename}.txt", "w") as f:
                        for chapter in chapters:
                            f.write(f"{chapter['start']}\n")

                    # Debug log
                    if status_callback:
                        status_callback(f"Wrote chapters to {output_dir / f'{filename}.txt'}")
                        status_callback(f"Removing {filename} from unprocessed_files_manager")

                    # Remove this file from the unprocessed files manager since we found chapters
                    # First need to check if the file is in the manager
                    files_matching = unprocessed_files_manager.get_files(original_file=file_path)
                    if files_matching:
                        unprocessed_files_manager.remove_file(file_path, str(file_path_obj.parent), filename)
                    else:
                        # If file wasn't in manager yet, we need to make sure it isn't added later
                        if status_callback:
                            status_callback(f"File {filename} not in manager yet, marking as processed")
                else:
                    # Debug log
                    if status_callback:
                        status_callback(f"No chapters found in {filename}")

                    # Add to unprocessed_files_manager if no chapters found
                    unprocessed_files_manager.add_file(file_path, str(file_path_obj.parent), filename)
                    if reset_callback:
                        reset_callback()
        else:
            # Legacy folder mode
            # Count total videos
            for dirpath, _, filenames in os.walk(input_path):
                for filename in filenames:
                    if filename.endswith(tuple(config.video_file_types)):
                        total_videos += 1

            # Process videos
            for dirpath, _, filenames in os.walk(input_path):
                for filename in filenames:
                    if not filename.endswith(tuple(config.video_file_types)):
                        continue

                    processed_videos += 1
                    original_file = Path(dirpath) / filename

                    # Call status callback if provided
                    if status_callback:
                        status_callback(f"Looking for chapters in {processed_videos} of {total_videos} videos")
                    if progress_callback:
                        progress_callback(processed_videos, total_videos)

                    if chapters := self.get_chapters(str(original_file)):
                        relative_path = Path(dirpath).relative_to(input_path)
                        output_dir = Path(output_path) / relative_path
                        output_dir.mkdir(parents=True, exist_ok=True)

                        # Create and write chapters to a text file in the output directory
                        with open(output_dir / f"{filename}.txt", "w") as f:
                            for chapter in chapters:
                                f.write(f"{chapter['start']}\n")

                        # Remove this file from the unprocessed files manager since we found chapters
                        unprocessed_files_manager.remove_file(str(original_file), str(dirpath), filename)
                    else:
                        # If no chapters are found, add the video file to the VideoFilesManager object
                        unprocessed_files_manager.add_file(str(original_file), str(dirpath), filename)
                        if reset_callback:
                            reset_callback()

    @staticmethod
    def get_chapters(video_file):
        chapters = []
        try:
            command = [
                get_executable_path("ffprobe", config.ffprobe_path),
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_chapters',
                video_file
            ]
            output = subprocess.check_output(command).decode()
            chapters_data = json.loads(output)

            # Extract start times of each chapter in seconds
            for chapter in chapters_data.get('chapters', []):
                start_time = float(chapter['start_time'])
                end_time = float(chapter['end_time'])
                chapters.append({'start': start_time, 'end': end_time})
        except Exception as e:
            print(f"Failed to extract chapters for {video_file}. Error: {e}")
        return chapters
