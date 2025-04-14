import os
from pathlib import Path
import cv2
import numpy as np
import subprocess
import json
from ComBreak.VideoLoader import VideoLoader
from ComBreak.VideoFileManager import VideoFilesManager
from ComBreak.EnhancedInputHandler import EnhancedInputHandler
from bisect import bisect_left
import config


class CommercialBreakerLogic:
    """A class that represents the main logic of the Commercial Breaker program."""

    def __init__(self):
        self.video_durations = {}
        self.input_handler = EnhancedInputHandler()

    @staticmethod
    def get_executable_path(executable_name, config_path):
        try:
            subprocess.run([executable_name, "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return executable_name  # Executable is on PATH
        except subprocess.CalledProcessError:
            return config_path  # Use config path if not on PATH

    # ------------------ Cutting Videos Methods ------------------
    @staticmethod
    def reduce_timestamps(timestamps):
        """Eliminate timestamp points that are closer to the previous ones than a certain threshold and less than starting buffer."""
        return [
            x for i, x in enumerate(timestamps)
            if (i == 0 or x - timestamps[i - 1] > config.TIMESTAMP_THRESHOLD) and x >= config.START_BUFFER
        ]

    @staticmethod
    def delete_files(output_path):
        """Delete .txt files in the specified directory and its subdirectories."""
        for dirpath, dirnames, filenames in os.walk(output_path):
            for filename in filenames:
                if filename.endswith('.txt'):
                    Path(dirpath, filename).unlink()

    def rename_files(self, output_dir):
        """Rename .mp4 files in the specified directory."""
        output_path = Path(output_dir)
        files = list(output_path.iterdir())
        mp4_files = [f for f in files if f.suffix == '.mp4']
        # Sort based on part number found at the end of the filename
        mp4_files.sort(key=lambda x: int(x.stem.split(' ')[-1]) if ' ' in x.stem else 0)

        for f in mp4_files:
            new_name = (
                f.name.replace(' 000', ' 1')
                      .replace(' 001', ' 2')
                      .replace(' 002', ' 3')
                      .replace(' 003', ' 4')
                      .replace(' 004', ' 5')
                      .replace(' 005', ' 6')
                      .replace(' 006', ' 7')
                      .replace(' 007', ' 8')
                      .replace(' 008', ' 9')
                      .replace(' 009', ' 10')
                      .replace(' 010', ' 11')
                      .replace(' 011', ' 12')
                      .replace(' 012', ' 13')
                      .replace(' 013', ' 14')
                      .replace(' 014', ' 15')
                      .replace(' 015', ' 16')
                      .replace(' 016', ' 17')
                      .replace(' 017', ' 18')
                      .replace(' 018', ' 19')
                      .replace(' 019', ' 20')
            )
            f.rename(output_path / new_name)

    def cut_videos(self, input_path, output_path, progress_callback=None, status_callback=None, destructive_mode=False):
        # Handle both legacy folder mode and enhanced input mode
        if self.input_handler.has_input():
            # Enhanced mode with files and/or folders
            video_files_data, output_dirs, total_videos = self.gather_video_files_to_cut_enhanced(output_path)
        else:
            # Legacy folder-only mode
            video_files_data, output_dirs, total_videos = self.gather_video_files_to_cut(input_path, output_path)
        
        failed_videos = []

        for i, (input_file, output_file_prefix) in enumerate(video_files_data):
            try:
                if status_callback:
                    status_callback(f"Cutting video {i+1} of {total_videos}")

                if not Path(input_file).exists():
                    failed_videos.append(input_file)
                    continue

                with open(f"{output_file_prefix}.txt", "r") as f:
                    timestamps = [float(line.strip()) for line in f]
                timestamps = self.reduce_timestamps(timestamps)

                end_time = self.get_video_duration(input_file)
                self.cut_single_video(input_file, output_file_prefix, end_time, timestamps, destructive_mode)

                if progress_callback:
                    progress_callback(i + 1, total_videos)
            except Exception as e:
                if status_callback:
                    status_callback(f"Error cutting video: {e}")
                failed_videos.append(input_file)

        if failed_videos:
            # Write failed videos to a file in the output directory instead of input directory
            with open(Path(output_path, "failedtocut.txt"), "w") as f:
                for video in failed_videos:
                    f.write(str(video) + "\n")

        for output_dir in output_dirs:
            self.rename_files(output_dir)

    def gather_video_files_to_cut_enhanced(self, output_path):
        """
        Gather video files to cut using the enhanced input handler.
        Works with both files and folders.
        """
        video_files_data = []
        output_dirs = set()
        
        # Get all selected files from the input handler
        input_files = self.input_handler.get_consolidated_paths()
        
        # For each input file, find its corresponding timestamp file in the output directory
        for input_file in input_files:
            input_file_path = Path(input_file)
            filename = input_file_path.name
            
            # Determine the output directory for this file
            output_dir = self.input_handler.get_output_path_for_file(input_file, output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if a timestamp file exists for this video
            timestamp_file = output_dir / f"{filename}.txt"
            if timestamp_file.exists():
                output_file_prefix = str(output_dir / filename.replace('.txt', ''))
                video_files_data.append((str(input_file_path), output_file_prefix))
                output_dirs.add(str(output_dir))
        
        total_videos = len(video_files_data)
        return video_files_data, output_dirs, total_videos

    def gather_video_files_to_cut(self, input_path, output_path):
        video_files_data = []
        output_dirs = set()
        total_videos = 0

        for dirpath, dirnames, filenames in os.walk(output_path):
            for filename in filenames:
                if filename.endswith('.txt'):
                    total_videos += 1
                    output_file_prefix = Path(dirpath) / Path(filename).stem
                    relative_path = Path(dirpath).relative_to(output_path)
                    input_dir = Path(input_path) / relative_path
                    video_filename = filename.replace('.txt', '')
                    input_file = input_dir / video_filename
                    video_files_data.append((str(input_file), str(output_file_prefix)))
                    output_dirs.add(str(dirpath))

        return video_files_data, output_dirs, total_videos

    def cut_single_video(self, input_file, output_file_prefix, end_time, timestamps, destructive_mode):
        timestamps.append(end_time)
        times_str = ','.join(str(t) for t in timestamps)

        output_file_prefix_path = Path(output_file_prefix)
        output_file_name_without_ext = output_file_prefix_path.stem
        output_dir = output_file_prefix_path.parent

        command = [
            CommercialBreakerLogic.get_executable_path("ffmpeg", config.ffmpeg_path),
            "-i", str(input_file),
            "-f", "segment",
            "-nostats",
            "-loglevel", "quiet",  # Suppress FFmpeg output
            "-segment_times", times_str,
            "-reset_timestamps", "1",
            "-c:v", "copy",  # Copy the video codec
            "-c:a", "aac",   # Explicitly set the audio codec to AAC
            "-threads", "0",
            f"{str(output_dir / output_file_name_without_ext)} - Part %03d.mp4"
        ]

        # Start the FFmpeg process
        process = subprocess.Popen(command)
        # Wait for process to complete
        process.communicate()
        # Explicitly terminate the FFmpeg process
        process.terminate()

        if destructive_mode:
            Path(input_file).unlink()

    def get_video_duration(self, input_file):
        end_time = self.video_durations.get(input_file, None)
        if end_time is None:
            command = [
                CommercialBreakerLogic.get_executable_path("ffprobe", config.ffprobe_path),
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_file
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            end_time = float(result.stdout)
            self.video_durations[input_file] = end_time
        return end_time

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
                CommercialBreakerLogic.get_executable_path("ffprobe", config.ffprobe_path),
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

    # ------------------- Detect Black Frames (with Silence) Methods -------------------
    @staticmethod
    def downscale_video(input_file, output_file, i, total, status_callback=None, progress_callback=None):
        """Downscale the video while keeping aspect ratio using ffmpeg."""
        try:
            if status_callback:
                status_callback(f"Downscaling video {i+1} of {total}")

            command = [
                CommercialBreakerLogic.get_executable_path("ffmpeg", config.ffmpeg_path),
                "-i", input_file,
                "-vf", f"scale=-2:{config.DOWNSCALE_HEIGHT}:flags=fast_bilinear",
                "-preset", "ultrafast",
                "-vcodec", "libx264",
                "-crf", "23",
                "-an",
                output_file,
                "-y"
            ]

            # Start the FFmpeg process
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            process.terminate()

            # Check FFmpeg's STDERR for errors
            if b"Error" in stderr:
                raise Exception(f"FFmpeg encountered an error while downscaling video {i+1}: {stderr.decode('utf-8')}")

            # Call the progress callback after completing the downscaling of each video
            if progress_callback:
                progress_callback(i + 1, total)

        except Exception as e:
            if status_callback:
                status_callback(f"An error occurred while downscaling video {i+1} of {total}: {str(e)}")

    @staticmethod
    def sound_of_silence(input_file):
        """Returns a list of silences, each represented by a dictionary with start and end times."""
        if not Path(input_file).is_file():
            return []
        try:
            command = [
                CommercialBreakerLogic.get_executable_path("ffmpeg", config.ffmpeg_path),
                "-i", input_file,
                "-af",
                f"silencedetect=n={config.DECIBEL_THRESHOLD}dB:d={config.SILENCE_DURATION}",
                "-preset", "ultrafast",
                "-f", "null",
                "-y",
                "/dev/null"
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            process.terminate()

            # Check FFmpeg's STDERR for errors
            if b"Error" in stderr:
                raise Exception(f"FFmpeg encountered an error while detecting silence: {stderr.decode('utf-8')}")

            lines = [line.decode('utf-8') for line in stderr.splitlines() if 'silence_' in line.decode('utf-8')]

            silences = []
            for i in range(0, len(lines), 2):
                start_time = float(lines[i].split()[4])
                end_time = float(lines[i + 1].split()[4])
                silences.append({'start': start_time, 'end': end_time})

            return silences

        except Exception as e:
            print(f"An error occurred while detecting silence: {str(e)}")
            return []

    def detect_silent_black_frames(self, input_path, output_path, total_frames, video_files_data, total_videos,
                                   file_counter, unprocessed_files_manager, progress_callback, status_callback,
                                   reset_callback):
        if self.input_handler.has_input():
            # Enhanced mode with files and/or folders
            video_files_data, total_frames, total_videos, file_counter = self.gather_video_files_to_detect_enhanced(
                output_path, total_frames, total_videos, file_counter,
                unprocessed_files_manager, status_callback, progress_callback, reset_callback
            )
        else:
            # Legacy folder mode
            video_files_data, total_frames, total_videos, file_counter = self.gather_video_files_to_detect(
                input_path, output_path, total_frames, total_videos, file_counter,
                unprocessed_files_manager, status_callback, progress_callback, reset_callback
            )
            
        # Call the reset_callback after all videos have been downscaled
        if reset_callback:
            reset_callback()

        processed_frames = 0
        for i, (filename, video_loader, downscaled_file, output_dir, original_file) in enumerate(video_files_data):
            processed_frames = self.silent_black_frame_detector(
                i, filename, original_file, total_videos, downscaled_file,
                output_dir, video_loader, status_callback, progress_callback,
                processed_frames, total_frames
            )

    def gather_video_files_to_detect_enhanced(self, output_path, total_frames, total_videos, file_counter,
                                     unprocessed_files_manager, status_callback, progress_callback, reset_callback):
        """
        Gather video files to detect using the enhanced input handler.
        Works with both files and folders.
        """
        video_files_data = []
        
        # Get files from the unprocessed files manager
        files_to_process = unprocessed_files_manager.get_files()
        total_videos = len(files_to_process)
        
        # Add debug information
        if status_callback:
            status_callback(f"Processing {total_videos} files for black frame detection")
        
        for i, video_file in enumerate(files_to_process):
            try:
                original_file, dirpath, filename = video_file.values()
                if not filename.endswith('.txt'):
                    input_file_path = Path(original_file)
                    
                    # Log which file we're processing
                    if status_callback:
                        status_callback(f"Processing file {i+1}/{total_videos}: {filename}")
                    
                    # Determine the output directory for this file
                    output_dir = self.input_handler.get_output_path_for_file(original_file, output_path)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Check if a timestamp file already exists (from chapters)
                    timestamp_file = output_dir / f"{filename}.txt"
                    if timestamp_file.exists():
                        if status_callback:
                            status_callback(f"Skipping {filename} - timestamp file already exists")
                        continue
                    
                    # Create the downscaled file in the same output directory
                    downscaled_file = output_dir / f"downscaled_{filename}"
                    
                    if status_callback:
                        status_callback(f"Output directory: {output_dir}")
                        status_callback(f"Downscaled file will be: {downscaled_file}")
                    
                    # Downscale the video
                    self.downscale_video(
                        str(original_file), 
                        str(downscaled_file),
                        file_counter, 
                        total_videos, 
                        status_callback, 
                        progress_callback
                    )
                    
                    # Verify the downscaled file exists
                    if not Path(downscaled_file).exists() and status_callback:
                        status_callback(f"WARNING: Downscaled file not created: {downscaled_file}")
                    elif status_callback:
                        status_callback(f"Successfully created downscaled file: {downscaled_file}")

                    # Load the downscaled video
                    video_loader = VideoLoader(str(downscaled_file))
                    total_frames += video_loader.get_frame_count()

                    # Add to processing list
                    video_files_data.append((
                        filename,
                        video_loader,
                        str(downscaled_file),
                        str(output_dir),
                        str(original_file),
                    ))
                    file_counter += 1
            except Exception as e:
                if status_callback:
                    status_callback(f"An error occurred while processing {filename}: {str(e)}")
                file_counter -= 1
                continue

        if status_callback:
            status_callback(f"Successfully prepared {len(video_files_data)} videos for processing")
            
        return video_files_data, total_frames, total_videos, file_counter
        
    def gather_video_files_to_detect(self, input_path, output_path, total_frames, total_videos, file_counter,
                                     unprocessed_files_manager, status_callback, progress_callback, reset_callback):
        video_files_data = []
        for video_file in unprocessed_files_manager.get_files():
            try:
                original_file, dirpath, filename = video_file.values()
                if not filename.endswith('.txt'):
                    relative_path = Path(dirpath).relative_to(input_path)
                    output_dir = Path(output_path) / relative_path
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Check if a timestamp file already exists (from chapters)
                    timestamp_file = output_dir / f"{filename}.txt"
                    if timestamp_file.exists():
                        if status_callback:
                            status_callback(f"Skipping {filename} - timestamp file already exists")
                        continue
                        
                    downscaled_file = output_dir / f"downscaled_{filename}"

                    self.downscale_video(str(original_file), str(downscaled_file),
                                         file_counter, total_videos, status_callback, progress_callback)

                    video_loader = VideoLoader(str(downscaled_file))
                    total_frames += video_loader.get_frame_count()

                    video_files_data.append((
                        filename,
                        video_loader,
                        str(downscaled_file),
                        str(output_dir),
                        str(original_file),
                    ))
                    file_counter += 1
            except Exception as e:
                if status_callback:
                    status_callback(f"An error occurred while processing {filename}: {str(e)}")
                file_counter -= 1
                continue

        return video_files_data, total_frames, total_videos, file_counter

    def silent_black_frame_detector(self, i, filename, original_file, total_videos, downscaled_file, output_dir,
                                    video_loader, status_callback, progress_callback, processed_frames, total_frames):
        try:
            if status_callback:
                status_callback(f"Processing video {i+1}/{total_videos}: {filename}")
                status_callback(f"Output directory for timestamps: {output_dir}")
            
            # Generate the merged silence periods
            merged_silence_periods = self.get_merged_silence_periods(original_file, status_callback)
            
            # Find the black frames during silent periods
            black_frames, processed_frames = self.find_black_frames(
                video_loader, merged_silence_periods, status_callback,
                progress_callback, processed_frames, total_frames
            )

            # Ensure output directory exists
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Create the timestamp file with the exact original filename
            timestamp_file = Path(output_dir) / f"{filename}.txt"
            
            if status_callback:
                status_callback(f"Will write {len(black_frames)} timestamps to file: {timestamp_file}")
            
            if black_frames:
                # Write timestamps to file
                try:
                    with open(timestamp_file, "w") as f:
                        f.writelines(f"{timestamp}\n" for timestamp in black_frames)
                    
                    # Double-check that the file was created
                    if Path(timestamp_file).exists():
                        if status_callback:
                            status_callback(f"Successfully created timestamp file: {timestamp_file}")
                    else:
                        if status_callback:
                            status_callback(f"WARNING: Failed to create timestamp file: {timestamp_file}")
                except Exception as e:
                    if status_callback:
                        status_callback(f"ERROR writing timestamp file: {e}")
            else:
                if status_callback:
                    status_callback(f"No black frames found for: {filename}")

            # Release the video loader resources
            video_loader.release()

            # Clean up the downscaled file
            if status_callback:
                status_callback(f"Cleaning up downscaled file: {downscaled_file}")
                
            if Path(downscaled_file).exists():
                try:
                    Path(downscaled_file).unlink()
                    if status_callback:
                        status_callback(f"Successfully deleted downscaled file")
                except Exception as e:
                    if status_callback:
                        status_callback(f"Error deleting downscaled file: {e}")
                
            return processed_frames

        except Exception as e:
            if status_callback:
                status_callback(f"An error occurred while processing video {i+1} of {total_videos}: {str(e)}")
            return processed_frames

    def get_merged_silence_periods(self, original_file, status_callback):
        if status_callback:
            status_callback("Listening for the Sound of Silence in the video")

        sound_of_silence = self.sound_of_silence(original_file)
        sound_of_silence.sort(key=lambda x: x['start'])
        merged_silence_periods = [sound_of_silence[0]] if sound_of_silence else []

        for silence in sound_of_silence[1:]:
            if silence['start'] <= merged_silence_periods[-1]['end']:
                merged_silence_periods[-1]['end'] = max(silence['end'], merged_silence_periods[-1]['end'])
            else:
                merged_silence_periods.append(silence)

        return merged_silence_periods

    def find_black_frames(self, video_loader, merged_silence_periods, status_callback, progress_callback,
                          processed_frames, total_frames):
        black_frames = []
        if status_callback:
            status_callback("Detecting black frames in the video")

        silence_timestamps = [timestamp for period in merged_silence_periods for timestamp in period.values()]

        for frame in video_loader:
            frame_time = video_loader.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            index = bisect_left(silence_timestamps, frame_time)

            # Check if frame_time is within a silence period
            if index % 2 == 0 and np.mean(np.asarray(frame)) < config.BLACK_FRAME_THRESHOLD:
                black_frames.append(frame_time)

            processed_frames += 1
            if progress_callback:
                progress_callback(processed_frames, total_frames)

        return black_frames, processed_frames

    # ------------------- Read Timestamps Method -------------------
    def read_timestamps(self, input_path, output_path, total_frames, video_files_data, total_videos,
                        file_counter, unprocessed_files_manager, progress_callback, status_callback):
        # Check if we're using enhanced input handling or legacy folder mode
        if self.input_handler.has_input():
            # Enhanced mode - look for matching files in plex_timestamps.txt
            input_files = self.input_handler.get_consolidated_paths()
            
            for base_path in set(Path(f).parent for f in input_files):
                plex_file_path = Path(base_path) / "plex_timestamps.txt"
                
                # Skip if no plex_timestamps.txt found
                if not plex_file_path.exists():
                    continue
                
                with open(plex_file_path, "r", encoding='utf-8') as plex_file:
                    plex_data = {}
                    for line in plex_file:
                        if " = " in line:
                            plex_filename, timestamp = line.rsplit(" = ", 1)
                            plex_data[plex_filename.strip()] = timestamp.strip()
                
                # Check each file in the input handler against the plex data
                for video_file in unprocessed_files_manager.get_files():
                    original_file, dirpath, filename = video_file.values()
                    
                    if filename in plex_data:
                        output_dir = self.input_handler.get_output_path_for_file(original_file, output_path)
                        output_dir.mkdir(parents=True, exist_ok=True)
                        
                        with open(output_dir / f"{filename}.txt", "w") as output_file:
                            output_file.write(plex_data[filename] + "\n")
                        
                        unprocessed_files_manager.remove_file(str(original_file), str(dirpath), filename)
        else:
            # Legacy folder mode
            plex_file_path = Path(input_path) / "plex_timestamps.txt"

            # Check if plex_timestamps.txt exists, if not, skip this step
            if not plex_file_path.exists():
                return

            for video_file in unprocessed_files_manager.get_files():
                original_file, dirpath, filename = video_file.values()

                with open(plex_file_path, "r", encoding='utf-8') as plex_file:
                    found_in_plex_file = False
                    for line in plex_file:
                        plex_filename, timestamp = line.rsplit(" = ", 1)  # Split on the last occurrence of " = "
                        plex_filename = plex_filename.strip()
                        timestamp = timestamp.strip()

                        if filename == plex_filename:
                            output_dir = Path(output_path) / Path(dirpath).relative_to(input_path)
                            output_dir.mkdir(parents=True, exist_ok=True)

                            with open(output_dir / f"{filename}.txt", "w") as output_file:
                                output_file.write(timestamp + "\n")

                            found_in_plex_file = True
                            break

                    if found_in_plex_file:
                        unprocessed_files_manager.remove_file(str(original_file), str(dirpath), filename)

    # ------------------ Orchestrating All Timestamp Methods ------------------
    def detect_commercials(self, input_path, output_path, progress_callback=None, status_callback=None,
                           low_power_mode=False, fast_mode=False, reset_callback=None):
        total_frames = 0
        total_videos = 0
        file_counter = 0
        video_files_data = []

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
        self.extract_chapters(input_path, output_path, unprocessed_files_manager, status_callback, progress_callback, reset_callback)
        
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
            self.read_timestamps(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback
            )
        elif fast_mode:
            # Check for timestamps in plex_timestamps.txt first
            self.read_timestamps(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback
            )
            # Then detect silent black frames for files not found in plex_timestamps.txt
            self.detect_silent_black_frames(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback,
                reset_callback
            )
        else:
            # Detect silent black frames first
            self.detect_silent_black_frames(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback,
                reset_callback
            )
            # Then read timestamps for any remaining files
            self.read_timestamps(
                input_path, output_path, total_frames, video_files_data, total_videos,
                file_counter, unprocessed_files_manager, progress_callback, status_callback
            )
