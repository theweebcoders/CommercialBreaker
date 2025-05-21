import os
from pathlib import Path
import cv2
import numpy as np
import subprocess
import json
from ComBreak.VideoLoader import VideoLoader
from ComBreak.VideoFileManager import VideoFilesManager
from ComBreak.EnhancedInputHandler import EnhancedInputHandler
from ComBreak.VirtualCut import VirtualCut
from ComBreak.SilentBlackFrameDetector import SilentBlackFrameDetector
from ComBreak.ChapterExtractor import ChapterExtractor
from ComBreak.VideoCutter import VideoCutter
from ComBreak.TimestampManager import TimestampManager
from bisect import bisect_left
import config


class CommercialBreakerLogic:
    """A class that represents the main logic of the Commercial Breaker program."""

    def __init__(self):
        self.input_handler = EnhancedInputHandler()
        self.virtual_cut = VirtualCut()  # No longer passing duration_getter
        # Instantiate the SilentBlackFrameDetector
        self.silent_black_frame_detector = SilentBlackFrameDetector(self.input_handler)
        # Instantiate the ChapterExtractor
        self.chapter_extractor = ChapterExtractor(self.input_handler)
        # Instantiate the VideoCutter
        self.video_cutter = VideoCutter(self.input_handler, self.virtual_cut)
        # Instantiate the TimestampManager
        self.timestamp_manager = TimestampManager(self.input_handler)

    # ------------------ Orchestrating All Timestamp Methods ------------------
    def detect_commercials(self, input_path, output_path, progress_callback=None, status_callback=None,
                           low_power_mode=False, fast_mode=False, reset_callback=None):
        total_frames = 0
        total_videos = 0
        file_counter = 0
        video_files_data = [] # This might be redundant now as detection logic is separate

        # Clear the unprocessed files manager
        unprocessed_files_manager = VideoFilesManager()
        unprocessed_files_manager.clear_files()  # Ensure we start with a clean state

        # First, populate the unprocessed_files_manager with all potential video files
        if self.input_handler.has_input():
            # Enhanced mode - add ALL files from the input handler
            consolidated_paths = self.input_handler.get_consolidated_paths()
            if status_callback:
                status_callback(f"Found {len(consolidated_paths)} files to process")
                
            # Add each selected file to the unprocessed_files_manager
            for file_path in consolidated_paths:
                path_obj = Path(file_path)
                if path_obj.suffix.lower() in tuple(config.video_file_types):
                    unprocessed_files_manager.add_file(str(path_obj), str(path_obj.parent), path_obj.name)
                    if status_callback:
                        status_callback(f"Added {path_obj.name} for initial processing")
        else:
            # Legacy folder mode - add files from the input path
            for dirpath, _, filenames in os.walk(input_path):
                for filename in filenames:
                    if filename.endswith(tuple(config.video_file_types)):
                        original_file = Path(dirpath) / filename
                        unprocessed_files_manager.add_file(str(original_file), dirpath, filename)

        # Get an initial count of files
        initial_files = len(unprocessed_files_manager.get_files())
        if status_callback:
            status_callback(f"Starting with {initial_files} video files to check")

        # Now, try to extract chapters from the selected videos and remove those with chapters
        # Delegate to the ChapterExtractor instance
        self.chapter_extractor.extract_chapters(input_path, output_path, unprocessed_files_manager, status_callback, progress_callback, reset_callback)
        
        # Check how many files are left after chapter extraction
        remaining_files = len(unprocessed_files_manager.get_files())
        if status_callback:
            status_callback(f"After chapter extraction: {remaining_files} videos remaining for processing")
        
        if reset_callback:
            reset_callback()

        # Get the final list of files to be processed
        files_to_process = unprocessed_files_manager.get_files()
        total_videos = len(files_to_process)
        if status_callback:
            status_callback(f"Total files to be processed: {total_videos}")

        if low_power_mode:
            if status_callback:
                status_callback("Low Power Mode Enabled: Skipping black frame detection")
            # Delegate to the TimestampManager instance
            self.timestamp_manager.read_timestamps(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback
            )
        elif fast_mode:
            # Check for timestamps in plex_timestamps.txt first
            # Delegate to the TimestampManager instance
            self.timestamp_manager.read_timestamps(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback
            )
            # Then detect silent black frames for files not found in plex_timestamps.txt
            # Delegate to the SilentBlackFrameDetector instance
            self.silent_black_frame_detector.detect_silent_black_frames(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback,
                reset_callback
            )
        else:
            # Detect silent black frames first
            # Delegate to the SilentBlackFrameDetector instance
            self.silent_black_frame_detector.detect_silent_black_frames(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback,
                reset_callback
            )
            # Then read timestamps for any remaining files
            # Delegate to the TimestampManager instance
            self.timestamp_manager.read_timestamps(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback
            )

        # Final step: Clean up timestamps by reducing points that are too close together
        if status_callback:
            status_callback("Cleaning up timestamps...")
        # Delegate to the TimestampManager instance
        self.timestamp_manager.cleanup_timestamps(output_path, progress_callback, status_callback)
        if status_callback:
            status_callback("Timestamp cleanup complete!")

    # ------------------ Cutting Videos Methods (Facade) ------------------
    def cut_videos(self, input_path, output_path, progress_callback=None, status_callback=None, destructive_mode=False, cutless_mode=False):
        """Facade method to delegate video cutting to the VideoCutter instance."""
        self.video_cutter.cut_videos(input_path, output_path, progress_callback, status_callback, destructive_mode, cutless_mode)

    def delete_files(self, output_path):
        """Facade method to delegate file deletion to the VideoCutter instance."""
        # Note: delete_files is static in VideoCutter, so we call it via the class
        VideoCutter.delete_files(output_path)
