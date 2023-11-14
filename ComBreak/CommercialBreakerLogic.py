import os
import cv2
import numpy as np
import subprocess
import json
from ComBreak.VideoLoader import VideoLoader
from ComBreak.VideoFileManager import VideoFilesManager
from bisect import bisect_left
import config
# from config import *


class CommercialBreakerLogic:
    """A class that represents the main logic of the Commercial Breaker program."""

    def __init__(self):
        self.video_durations = {}

    # ------------------ Begining for cut videos methods ------------------
    @staticmethod
    def reduce_timestamps(timestamps):
        """Eliminate timestamp points that are closer to the previous ones than a certain threshold and less than starting buffer."""
        return [x for i, x in enumerate(timestamps) if (i == 0 or x - timestamps[i - 1] > config.TIMESTAMP_THRESHOLD) and x >= config.START_BUFFER]

    @staticmethod
    def delete_files(output_path):
        """Delete .txt files in the specified directory and its subdirectories."""
        for dirpath, dirnames, filenames in os.walk(output_path):
            for filename in filenames:
                if filename.endswith('.txt'):
                    os.remove(os.path.join(dirpath, filename))

    def rename_files(self, output_dir):
        """Rename .mp4 files in the specified directory."""
        files = os.listdir(output_dir)
        mp4_files = [file for file in files if file.endswith('.mp4')]
        mp4_files.sort(key=lambda x: int(x.split(' ')[-1].split('.')[0]))  # Sort the files by their numerical index

        for file in mp4_files:
            old_name = os.path.join(output_dir, file)
            new_name = os.path.join(output_dir, file.replace(' 000', ' 1').replace(' 001', ' 2').replace(' 002', ' 3').replace(' 003', ' 4').replace(' 004', ' 5').replace(' 005', ' 6').replace(' 006', ' 7').replace(' 007', ' 8').replace(' 008', ' 9').replace(' 009', ' 10').replace(' 010', ' 11').replace(' 011', ' 12').replace(' 012', ' 13').replace(' 013', ' 14').replace(' 014', ' 15').replace(' 015', ' 16').replace(' 016', ' 17').replace(' 017', ' 18').replace(' 018', ' 19').replace(' 019', ' 20'))
            os.rename(old_name, new_name)

    # ------------------ The method that runs the cut videos methods ------------------
    def cut_videos(self, input_path, output_path, progress_callback=None, status_callback=None, destructive_mode=False):
        video_files_data, output_dirs, total_videos = self.gather_video_files_to_cut(input_path, output_path)
        failed_videos = []

        for i, (input_file, output_file_prefix) in enumerate(video_files_data):
            try:
                if status_callback:
                    status_callback(f"Cutting video {i+1} of {total_videos}")

                if not os.path.exists(input_file):
                    failed_videos.append(input_file)
                    continue

                with open(f"{output_file_prefix}.txt", "r") as f:
                    timestamps = [float(line.strip()) for line in f]
                timestamps = self.reduce_timestamps(timestamps)

                end_time = self.get_video_duration(input_file)
                self.cut_single_video(input_file, output_file_prefix, end_time, timestamps, destructive_mode)

                if progress_callback:
                    progress_callback(i + 1, total_videos)
            except Exception:
                failed_videos.append(input_file)

        if failed_videos:
            with open(os.path.join(input_path, "failedtocut.txt"), "w") as f:
                for video in failed_videos:
                    f.write(video + "\n")

        for output_dir in output_dirs:
            self.rename_files(output_dir)

    def gather_video_files_to_cut(self, input_path, output_path):
        video_files_data = []
        output_dirs = set()
        total_videos = 0

        for dirpath, dirnames, filenames in os.walk(output_path):
            for filename in filenames:
                if filename.endswith('.txt'):
                    total_videos += 1
                    output_file_prefix = os.path.join(dirpath, os.path.splitext(filename)[0])
                    relative_path = os.path.relpath(dirpath, output_path)
                    input_dir = os.path.join(input_path, relative_path)  # Fixed here
                    video_filename = filename.replace('.txt', '')
                    input_file = os.path.join(input_dir, video_filename)
                    video_files_data.append((input_file, output_file_prefix))
                    output_dirs.add(dirpath)

        return video_files_data, output_dirs, total_videos

    def cut_single_video(self, input_file, output_file_prefix, end_time, timestamps, destructive_mode):
        timestamps.append(end_time)
        times_str = ','.join(str(t) for t in timestamps)

        output_file_name = os.path.basename(output_file_prefix)
        output_file_name_without_ext = os.path.splitext(output_file_name)[0]
        output_dir = os.path.dirname(output_file_prefix)

        command = [
            config.ffmpeg_path, "-i", input_file,
            "-f", "segment",
            "-segment_times", times_str,
            "-reset_timestamps", "1",
            "-c:v", "copy",  # Copy the video codec
            "-c:a", "aac",  # Explicitly set the audio codec to AAC
            "-threads", "0",
            f"{os.path.join(output_dir, output_file_name_without_ext)} - Part %03d.mp4"
        ]

        # Start the FFmpeg process
        process = subprocess.Popen(command)
        # Wait for process to complete
        process.communicate()
        # Explicitly terminate the FFmpeg process
        process.terminate()

        if destructive_mode:
            os.remove(input_file)

    def get_video_duration(self, input_file):
        end_time = self.video_durations.get(input_file, None)
        if end_time is None:
            command = [config.ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_file]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            end_time = float(result.stdout)
            self.video_durations[input_file] = end_time
        return end_time

    # ------------------- Begining of timestamps finder methods -------------------

    # ------------------- Extract Chapters Methods -------------------
    def extract_chapters(self, input_path, output_path, status_callback=None, progress_callback=None, reset_callback=None):
        total_videos = 0  # Initialize count of total videos
        processed_videos = 0  # Initialize count of processed videos
        video_files_manager = VideoFilesManager()  # Instantiate VideoFilesManager object
        video_files_manager.clear_files()  # Clear the list of video files

        # Loop to count total videos
        for dirpath, _, filenames in os.walk(input_path):
            for filename in filenames:
                if not filename.endswith('.txt'):  # Count only video files
                    total_videos += 1

        # Loop over all subdirectories and files in the input directory
        for dirpath, _, filenames in os.walk(input_path):
            for filename in filenames:
                if filename.endswith('.txt'):  # Ignore txt files
                    continue

                processed_videos += 1  # Increment count for each video processed
                original_file = os.path.join(dirpath, filename)  # Full path to the video file

                # Call status callback if provided
                if status_callback:
                    status_callback(f"Looking for chapters in {processed_videos} of {total_videos} videos")
                    # set the status bar to processed_videos/total_videos
                if progress_callback:
                    progress_callback(processed_videos, total_videos)

                if chapters := self.get_chapters(original_file):
                    relative_path = os.path.relpath(dirpath, input_path)  # Relative path to the video file
                    output_dir = os.path.join(output_path, relative_path)  # Output directory
                    os.makedirs(output_dir, exist_ok=True)  # Create output directory if it doesn't exist

                    # Create and write chapters to a new text file in the output directory
                    with open(os.path.join(output_dir, f"{filename}.txt"), "w") as f:
                        for chapter in chapters:
                            f.write(f"{chapter['start']}\n")
                else:
                    # If no chapters are found, add the video file to the VideoFilesManager object
                    video_files_manager.add_file(original_file, dirpath, filename)
                    if reset_callback:
                        reset_callback()

    @staticmethod
    def get_chapters(video_file):
        chapters = []
        try:
            command = [
                config.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_chapters',
                video_file
            ]
            output = subprocess.check_output(command).decode()
            chapters_data = json.loads(output)

            # Extract start and end times of each chapter in seconds
            for chapter in chapters_data.get('chapters', []):
                start_time = float(chapter['start_time'])
                end_time = float(chapter['end_time'])
                chapters.append({'start': start_time, 'end': end_time})
        except Exception as e:
            print(f"Failed to extract chapters for {video_file}. Error: {e}")
        return chapters

        # ------------------- Detect Black Frames Methods -------------------
    @staticmethod
    def downscale_video(input_file, output_file, i, total, status_callback=None, progress_callback=None):
        """Downscale the video while keeping aspect ratio using ffmpeg."""
        try:
            if status_callback:
                status_callback(f"Downscaling video {i+1} of {total}")

            command = [
                config.ffmpeg_path, "-i", input_file, "-vf",
                f'scale=-2:{config.DOWNSCALE_HEIGHT}:flags=fast_bilinear',
                "-preset", "ultrafast", "-vcodec", "libx264",
                "-crf", "23", "-an", output_file, "-y"
            ]

            # Start the FFmpeg process
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            # Explicitly terminate the FFmpeg process
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
        if not os.path.isfile(input_file):
            return []
        try:
            command = [config.ffmpeg_path, "-i", input_file, "-af", f"silencedetect=n={config.DECIBEL_THRESHOLD}dB:d={config.SILENCE_DURATION}", "-preset", "ultrafast", "-f", "null", "-y", "/dev/null"]
            # Capture FFmpeg's STDERR
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            # Check FFmpeg's STDERR for errors
            if b"Error" in stderr:
                raise Exception(f"FFmpeg encountered an error while detecting silence: {stderr.decode('utf-8')}")
            lines = [line.decode('utf-8') for line in stderr.splitlines() if 'silence_' in line.decode('utf-8')]

            silences = []
            for i in range(0, len(lines), 2):
                start_time = float(lines[i].split()[4])
                end_time = float(lines[i + 1].split()[4])
                silences.append({'start': start_time, 'end': end_time})

            print(silences)
            return silences

        except Exception as e:
            print(f"An error occurred while detecting silence: {str(e)}")
            return []

    # ------------------- The primary that runs all the detect black frames methods -------------------

    def detect_silent_black_frames(self, input_path, output_path, total_frames, video_files_data, total_videos, file_counter, unprocessed_files_manager, progress_callback, status_callback, reset_callback):
        video_files_data, total_frames, total_videos, file_counter = self.gather_video_files_to_detect(input_path, output_path, total_frames, total_videos, file_counter, unprocessed_files_manager, status_callback, progress_callback, reset_callback)
        # Call the reset_callback after all videos have been downscaled
        if reset_callback:
            reset_callback()
        processed_frames = 0
        for i, (filename, video_loader, downscaled_file, output_dir, original_file) in enumerate(video_files_data):
            processed_frames = self.silent_black_frame_detector(i, filename, original_file, total_videos, downscaled_file, output_dir, video_loader, status_callback, progress_callback, processed_frames, total_frames)

    def gather_video_files_to_detect(self, input_path, output_path, total_frames, total_videos, file_counter, unprocessed_files_manager, status_callback, progress_callback, reset_callback):
        video_files_data = []
        for video_file in unprocessed_files_manager.get_files():
            try:
                original_file, dirpath, filename = video_file.values()
                if not filename.endswith('.txt'):
                    total_videos = len(unprocessed_files_manager.get_files())
                    relative_path = os.path.relpath(dirpath, input_path)
                    output_dir = os.path.join(output_path, relative_path)
                    os.makedirs(output_dir, exist_ok=True)
                    downscaled_file = os.path.join(output_dir, f"downscaled_{filename}")
                    self.downscale_video(original_file, downscaled_file, file_counter, total_videos, status_callback, progress_callback)
                    video_loader = VideoLoader(downscaled_file)
                    total_frames += video_loader.get_frame_count()
                    video_files_data.append((filename, video_loader, downscaled_file, output_dir, original_file))
                    file_counter += 1
            except Exception as e:
                if status_callback:
                    status_callback(f"An error occurred while processing {filename}: {str(e)}")
                file_counter -= 1
                continue
        return video_files_data, total_frames, total_videos, file_counter

    def silent_black_frame_detector(self, i, filename, original_file, total_videos, downscaled_file, output_dir, video_loader, status_callback, progress_callback, processed_frames, total_frames):
        try:
            merged_silence_periods = self.get_merged_silence_periods(original_file, status_callback)
            black_frames, processed_frames = self.find_black_frames(video_loader, merged_silence_periods, status_callback, progress_callback, processed_frames, total_frames)

            if black_frames:
                with open(os.path.join(output_dir, f"{filename}.txt"), "w") as f:
                    f.writelines(f"{timestamp}\n" for timestamp in black_frames)

            video_loader.release()

            if status_callback:
                status_callback(f"Cleaning up downscaled video files {i+1} of {total_videos}")

            os.remove(downscaled_file)
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
        merged_silence_periods = [sound_of_silence[0]]
        for silence in sound_of_silence[1:]:
            if silence['start'] <= merged_silence_periods[-1]['end']:
                merged_silence_periods[-1]['end'] = max(silence['end'], merged_silence_periods[-1]['end'])
            else:
                merged_silence_periods.append(silence)

        return merged_silence_periods

    def find_black_frames(self, video_loader, merged_silence_periods, status_callback, progress_callback, processed_frames, total_frames):
        black_frames = []
        if status_callback:
            status_callback("Detecting black frames in the video")

        silence_timestamps = [timestamp for period in merged_silence_periods for timestamp in period.values()]

        for frame in video_loader:
            frame_time = video_loader.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            index = bisect_left(silence_timestamps, frame_time)

            if index % 2 == 0 and np.mean(np.asarray(frame)) < config.BLACK_FRAME_THRESHOLD:
                black_frames.append(frame_time)

            processed_frames += 1
            if progress_callback:
                progress_callback(processed_frames, total_frames)

        return black_frames, processed_frames

    # ------------------- Read Timestamps Method -------------------
    def read_timestamps(self, input_path, output_path, total_frames, video_files_data, total_videos, file_counter, unprocessed_files_manager, progress_callback, status_callback):
        plex_file_path = os.path.join(input_path, "plex_timestamps.txt")

        # Check if plex_timestamps.txt exists, if not, skip this step
        if not os.path.exists(plex_file_path):
            return

        for video_file in unprocessed_files_manager.get_files():
            original_file, dirpath, filename = video_file.values()
            with open(plex_file_path, "r", encoding='utf-8') as plex_file:
                found_in_plex_file = False
                for line in plex_file:
                    plex_filename, timestamp = line.rsplit(" = ", 1)  # Split on the last occurrence of " = "
                    plex_filename = plex_filename.strip()  # Remove any leading or trailing whitespace
                    timestamp = timestamp.strip()
                    if filename == plex_filename:
                        output_dir = os.path.join(output_path, os.path.relpath(dirpath, input_path))
                        os.makedirs(output_dir, exist_ok=True)
                        with open(os.path.join(output_dir, f"{filename}.txt"), "w") as output_file:
                            output_file.write(timestamp + "\n")
                        found_in_plex_file = True
                        break
                if found_in_plex_file:
                    unprocessed_files_manager.remove_file(original_file, dirpath, filename)

    # ------------------ The method that runs the timestamps methods ------------------
    def detect_commercials(self, input_path, output_path, progress_callback=None, status_callback=None, low_power_mode=False, fast_mode=False, reset_callback=None):
        total_frames = 0
        total_videos = 0  # Initialize count of total videos
        file_counter = 0  # Initialize a separate file counter
        video_files_data = []
        self.extract_chapters(input_path, output_path, status_callback, progress_callback, reset_callback)
        if reset_callback:
            reset_callback()
        unprocessed_files_manager = VideoFilesManager()

        if low_power_mode:
            status_callback("Low Power Mode Enabled: Skipping black frame detection")
            self.read_timestamps(input_path, output_path, total_frames, video_files_data, total_videos, file_counter, unprocessed_files_manager, progress_callback, status_callback)
        elif fast_mode:
            #check for timestamps in plex_timestamps.txt first
            self.read_timestamps(input_path, output_path, total_frames, video_files_data, total_videos, file_counter, unprocessed_files_manager, progress_callback, status_callback)
            #give files not found to detect_silent_black_frames
            self.detect_silent_black_frames(input_path, output_path, total_frames, video_files_data, total_videos, file_counter, unprocessed_files_manager, progress_callback, status_callback, reset_callback)
        else:
            #detect silent black frames first
            self.detect_silent_black_frames(input_path, output_path, total_frames, video_files_data, total_videos, file_counter, unprocessed_files_manager, progress_callback, status_callback, reset_callback)
            #give files no silent black frames detected for to read_timestamps
            self.read_timestamps(input_path, output_path, total_frames, video_files_data, total_videos, file_counter, unprocessed_files_manager, progress_callback, status_callback)
