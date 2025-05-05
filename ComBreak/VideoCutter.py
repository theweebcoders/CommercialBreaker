import os
from pathlib import Path
import subprocess
import config
from ComBreak.utils import get_executable_path

class VideoCutter:
    def __init__(self, input_handler, virtual_cut):
        self.input_handler = input_handler
        self.virtual_cut = virtual_cut
        self.video_durations = {}

    # ------------------ Cutting Videos Methods ------------------
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

    def cut_videos(self, input_path, output_path, progress_callback=None, status_callback=None, destructive_mode=False, cutless_mode=False):
        # Handle both legacy folder mode and enhanced input mode
        if self.input_handler.has_input():
            # Enhanced mode with files and/or folders
            video_files_data, output_dirs, total_videos = self.gather_video_files_to_cut_enhanced(output_path)
        else:
            # Legacy folder-only mode
            video_files_data, output_dirs, total_videos = self.gather_video_files_to_cut(input_path, output_path)

        if cutless_mode:
            if status_callback:
                status_callback("Cutless Mode Enabled: Generating virtual cut data...")
            self.virtual_cut.generate_virtual_prep_data(video_files_data, total_videos, progress_callback, status_callback)
            if status_callback:
                status_callback("Virtual cut data generation complete.")
            # No renaming needed in cutless mode as files aren't created
            return # Exit early as no physical cutting or renaming is done

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
                # Timestamps are already reduced during detection, no need to reduce again

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
            get_executable_path("ffmpeg", config.ffmpeg_path),
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
                get_executable_path("ffprobe", config.ffprobe_path),
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_file
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            end_time = float(result.stdout)
            self.video_durations[input_file] = end_time
        return end_time
