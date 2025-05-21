import os
from pathlib import Path
import subprocess
from bisect import bisect_left
import config
import cv2
import numpy as np
from ComBreak.VideoLoader import VideoLoader
from ComBreak.utils import get_executable_path


class SilentBlackFrameDetector:
    def __init__(self, input_handler):
        self.input_handler = input_handler
        self.orchestrator = SilentBlackFrameOrchestrator(input_handler)

    def detect_silent_black_frames(
        self, input_path, output_path, total_frames, video_files_data,
        total_videos, file_counter, unprocessed_files_manager,
        progress_callback, status_callback, reset_callback
    ):
        # Reset UI before starting, since we'll be using a unified progress bar
        if reset_callback:
            reset_callback()
        # Run orchestrator and return processed frame count
        return self.orchestrator.run(
            input_path, output_path, total_frames, video_files_data,
            total_videos, file_counter, unprocessed_files_manager,
            progress_callback, status_callback
        )


class ProgressManager:
    def __init__(self, downscale_count, silence_count, frame_count, progress_cb):
        # Apply weight factor to downscaling for more immediate feedback
        # This ensures downscaling (which happens first) shows visible progress right away
        downscale_weight = 5  # Weight factor to make downscaling progress more visible
        
        self.downscale_total = downscale_count * downscale_weight
        self.silence_total = silence_count
        self.frame_total = frame_count
        # Ensure total is at least 1 to avoid division by zero if all counts are 0
        self.total = max(1, self.downscale_total + silence_count + frame_count)
        
        self.downscale_done = 0
        self.silence_done = 0
        self.frame_done = 0
        self.done = 0
        
        # Store weight factor for step_downscale to use
        self.downscale_weight = downscale_weight
        
        self.cb = progress_cb
        # Initial call to set progress to 0
        if self.cb:
            self.cb(self.done, self.total)

    def _update_progress(self):
        self.done = self.downscale_done + self.silence_done + self.frame_done
        # Ensure we don't exceed total due to estimations or errors
        # Cap at 99% unless force_complete is called, to prevent visual "jumping back"
        self.done = min(self.done, self.total - 1) 
        if self.cb:
            self.cb(self.done, self.total)

    def step_downscale(self):
        # Only step if we haven't reached the total for this category
        if self.downscale_done < self.downscale_total:
            # Increment by weight factor to reflect the weighted total
            self.downscale_done += self.downscale_weight
            self._update_progress()
        # Optional: Log or warn if trying to step beyond total
        # elif self.downscale_done == self.downscale_total:
        #     print("Warning: Tried to step downscale beyond total")

    def step_silence(self):
        # Only step if we haven't reached the total for this category
        if self.silence_done < self.silence_total:
            self.silence_done += 1
            self._update_progress()
        # Optional: Log or warn if trying to step beyond total
        # elif self.silence_done == self.silence_total:
        #     print("Warning: Tried to step silence beyond total")

    def step_frame(self):
        # Only step if we're not nearing the total to avoid overshooting
        # Leave room for at least 1% of progress for force_complete
        if self.done < self.total - 1:
            self.frame_done += 1 
            self._update_progress()
        # Otherwise, just increment counter but don't update visible progress
        else:
            self.frame_done += 1
        
    def force_complete(self):
        """Forces the progress bar to 100%."""
        self.done = self.total
        self.downscale_done = self.downscale_total
        self.silence_done = self.silence_total
        self.frame_done = self.frame_total # Set frame done to total estimated
        if self.cb:
            self.cb(self.done, self.total)


class SilentBlackFrameOrchestrator:
    def __init__(self, input_handler):
        self.input_handler = input_handler
        self.gatherer = VideoFileGatherer(input_handler)
        self.preprocessor = VideoPreprocessor()
        self.silence_detector = SilenceDetector()
        self.blackframe_analyzer = BlackFrameAnalyzer()
        self.reducer = TimestampReducer()
        self.cleaner = ResourceCleaner()

    def run(
        self, input_path, output_path, total_frames, video_files_data,
        total_videos, file_counter, unprocessed_files_manager,
        progress_callback, status_callback
    ):
        # Phase 1: gather files
        gathered, _, total_videos, _ = self.gatherer.gather(
            input_path, output_path, total_frames, total_videos,
            file_counter, unprocessed_files_manager,
            status_callback, None # Don't use main progress_callback for gathering
        )

        if not gathered:
            if status_callback:
                status_callback("No files to process. Skipping silent black frame detection.")
            return 0

        # --- Accurate Progress Pre-calculation ---
        
        # 1. Silence Steps (1 per video)
        silence_steps_total = len(gathered)
        
        # 2. Pre-scan all videos for silence periods
        if status_callback:
            status_callback(f"Pre-scanning {len(gathered)} videos to identify silence periods and optimize processing...")
        all_silence_periods_data = []
        downscale_steps_total = 0
        frame_steps_total = 0
        
        for idx, (filename, original_file, out_dir) in enumerate(gathered):
            silence_periods = []
            try:
                # Use a minimal status callback during pre-scan if desired
                # silence_periods = self.silence_detector.detect(original_file, lambda msg: None) 
                silence_periods = self.silence_detector.detect(original_file, status_callback) 
                
                # Count downscale steps (1 per segment)
                downscale_steps_total += len(silence_periods)
                
                # Estimate frame steps (using original video frame rate)
                if silence_periods:
                    try:
                        # Use VideoLoader's get_frame_count to estimate frames in periods
                        temp_loader = VideoLoader(str(original_file))
                        # Calculate how many frames per second after FRAME_RATE sampling
                        fps = temp_loader.cap.get(cv2.CAP_PROP_FPS) / config.FRAME_RATE
                        temp_loader.release()
                        
                        for period in silence_periods:
                            duration = period['end'] - period['start']
                            if duration > 0:
                                # Calculate frames in this period using FPS after sampling
                                estimated_frames = int(duration * fps)
                                frame_steps_total += estimated_frames
                    except Exception as e:
                        if status_callback:
                            status_callback(f"Error estimating frames for {filename}, progress might be less accurate: {str(e)}")
                            
            except Exception as e:
                if status_callback:
                    status_callback(f"Error pre-scanning silence in {filename}: {str(e)}")
            
            all_silence_periods_data.append({
                'file_idx': idx,
                'filename': filename,
                'original_file': original_file,
                'out_dir': out_dir,
                'silence_periods': silence_periods
            })

        if status_callback:
            status_callback(f"Processing plan: {silence_steps_total} silence detections + " +
                           f"{downscale_steps_total} segment downscales + " +
                           f"{frame_steps_total} frame analyses = {silence_steps_total + downscale_steps_total + frame_steps_total} total steps")

        # Initialize ProgressManager with accurate counts
        prog = ProgressManager(downscale_steps_total, silence_steps_total, frame_steps_total, progress_callback)
        processed_frames_total_counter = 0 # Keep track of actual frames processed across all files

        # --- Phase 2: Process each file ---
        for file_data in all_silence_periods_data:
            idx = file_data['file_idx']
            filename = file_data['filename']
            original_file = file_data['original_file']
            out_dir = file_data['out_dir']
            silence_periods = file_data['silence_periods']
            segment_files = []
            # Estimate frames for *this file* to handle errors in analysis phase
            estimated_frames_for_this_file = 0
            if silence_periods:
                try:
                    # Use the same FPS calculation as above for consistency
                    temp_loader = VideoLoader(str(original_file))
                    fps = temp_loader.cap.get(cv2.CAP_PROP_FPS) / config.FRAME_RATE
                    temp_loader.release()
                    
                    for period in silence_periods:
                        duration = period['end'] - period['start']
                        if duration > 0: 
                            estimated_frames_for_this_file += int(duration * fps)
                except Exception as e:
                    if status_callback:
                        status_callback(f"Error estimating frames for {filename}, using approximation: {str(e)}")
            
            try:
                if status_callback:
                    status_callback(f"Processing video {idx+1}/{len(gathered)}: {filename}")

                # 2.1 Silence detection step (already done, just update progress)
                prog.step_silence() 

                # 2.2 Targeted downscaling
                if silence_periods:
                    try:
                        segment_files = self.preprocessor.preprocess_segments(
                            original_file, out_dir, silence_periods, idx, len(gathered),
                            status_callback, 
                            prog.step_downscale # Pass the specific downscale step function
                        )
                    except Exception as e:
                        if status_callback:
                            status_callback(f"Error during segmented downscaling for {filename}: {str(e)}")
                        # Ensure progress steps for downscaling are accounted for even on error
                        # Calculate how many downscale steps were expected for this file
                        expected_downscales_for_file = len(silence_periods)
                        # Calculate how many were done *before* this file started
                        downscales_before_this_file = sum(len(p_data['silence_periods']) for p_data in all_silence_periods_data[:idx])
                        # Calculate how many were done *for* this file so far (might be 0 if error was immediate)
                        downscales_done_for_this_file = prog.downscale_done - downscales_before_this_file
                        # Step the remaining ones
                        remaining_downscale_steps = max(0, expected_downscales_for_file - downscales_done_for_this_file)
                        for _ in range(remaining_downscale_steps):
                             prog.step_downscale()
                        raise # Re-raise to skip analysis for this file
                else:
                    # No downscale steps expected or taken
                    if status_callback:
                        status_callback(f"No silence periods found for {filename}, skipping downscale/analysis.")
                    

                # 2.3 Black frame analysis
                raw_ts = []
                processed_frames_in_file = 0
                if segment_files: # Only analyze if segments were successfully created
                    try:
                        # Pass 0 as offset, function returns count for this call
                        raw_ts, processed_frames_in_file = self.blackframe_analyzer.analyze_segments(
                            segment_files,
                            status_callback, 
                            prog.step_frame, # Pass the specific frame step function
                            0, 
                            estimated_frames_for_this_file # Pass estimate for context
                        )
                        processed_frames_total_counter += processed_frames_in_file
                    except Exception as e:
                        if status_callback:
                            status_callback(f"Error during frame analysis for {filename}: {str(e)}")
                        # Ensure progress steps for frames are accounted for
                        remaining_frame_steps = max(0, estimated_frames_for_this_file - processed_frames_in_file)
                        if status_callback:
                            status_callback(f"Accounting for {remaining_frame_steps} estimated remaining frames in progress.")
                        for _ in range(remaining_frame_steps):
                            prog.step_frame()
                        processed_frames_total_counter += remaining_frame_steps # Add to total count
                        
                else:
                    # No frame analysis steps expected or taken if no segments
                    pass 

                # 2.4 Reduction & write
                final_ts = self.reducer.reduce(raw_ts)
                self._write_timestamps(filename, out_dir, final_ts, status_callback)

            except Exception as e:
                # General error handling for the file
                if status_callback:
                    status_callback(f"An error occurred processing {filename}, skipping remaining steps for this file: {str(e)}")
                # Ensure progress steps are advanced if not already done
                # Silence step was done at the start of the loop
                # Downscale steps should have been handled in the downscale try/except
                # Frame steps should have been handled in the analysis try/except
                # If error happened before analysis, need to account for frame steps here? Let's assume analysis handles it.
                pass

            finally:
                # 2.5 Cleanup
                if segment_files:
                    self.cleaner.clean_segments(segment_files, status_callback)

        # Final progress update to ensure it reaches 100%
        prog.force_complete() # Use the new method to guarantee 100%

        if status_callback:
            status_callback("Silent black frame detection complete!")
            
        return processed_frames_total_counter # Return actual frames processed
        
    def _write_timestamps(self, filename, output_dir, timestamps, status_callback):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts_file = Path(output_dir) / f"{filename}.txt"
        if status_callback:
            status_callback(f"Will write {len(timestamps)} timestamps to file: {ts_file}")
        if timestamps:
            try:
                with open(ts_file, "w") as f:
                    f.writelines(f"{t}\n" for t in timestamps)
                if ts_file.exists() and status_callback:
                    status_callback(f"Successfully created timestamp file: {ts_file}")
                else:
                    if status_callback:
                        status_callback(f"WARNING: Failed to create timestamp file: {ts_file}")
            except Exception as e:
                if status_callback:
                    status_callback(f"ERROR writing timestamp file: {e}")
        else:
            if status_callback:
                status_callback(f"No black frames found for: {filename}")


class VideoFileGatherer:
    def __init__(self, input_handler):
        self.input_handler = input_handler

    def gather(
        self, input_path, output_path, total_frames, total_videos,
        file_counter, unprocessed_files_manager,
        status_callback, progress_callback
    ):
        files = unprocessed_files_manager.get_files()
        total_videos = len(files)
        if status_callback:
            status_callback(f"Processing {total_videos} files for black frame detection")
        gathered = []
        for video_file in files:
            original, dirpath, filename = video_file.values()
            if filename.endswith('.txt'):
                continue
            if self.input_handler.has_input():
                out_dir = Path(self.input_handler.get_output_path_for_file(original, output_path))
            else:
                rel = Path(dirpath).relative_to(input_path)
                out_dir = Path(output_path) / rel
            out_dir.mkdir(parents=True, exist_ok=True)
            if (out_dir / f"{filename}.txt").exists():
                if status_callback:
                    status_callback(f"Skipping {filename} - timestamp file already exists")
                continue
            gathered.append((filename, original, str(out_dir)))
        if status_callback:
            status_callback(f"Successfully prepared {len(gathered)} videos for processing")
        return gathered, total_frames, total_videos, file_counter


class VideoPreprocessor:
    def preprocess(
        self, original_file, output_dir, index, total,
        status_callback, progress_step
    ):
        downscaled = Path(output_dir) / f"downscaled_{Path(original_file).name}"
        cmd = [
            get_executable_path("ffmpeg", config.ffmpeg_path),
            "-threads", "0",
            "-i", original_file,
            "-vf", f"scale=-2:{config.DOWNSCALE_HEIGHT}:flags=neighbor",
            "-preset", "ultrafast",
            "-vcodec", "libx264", "-crf", "23", "-an",
            str(downscaled),
            "-y"
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        process.terminate()
        if b"Error" in stderr and status_callback:
            status_callback(f"An error occurred while downscaling video {index+1} of {total}: {stderr.decode('utf-8')}")
        progress_step()
        loader = VideoLoader(str(downscaled))
        frame_count = loader.get_frame_count()
        return str(downscaled), loader, frame_count

    def preprocess_segments(
        self, original_file, output_dir, silence_periods, index, total,
        status_callback, progress_step_downscale=None # Changed argument name
    ):
        """Downscale only silent periods from the original video file."""
        segment_files = []
        output_dir_path = Path(output_dir)
        original_filename_base = Path(original_file).stem
        
        if not silence_periods:
            # No segments, but we need to account for the steps if pre-calculation included them
            # However, pre-calculation counts based on found periods, so 0 periods means 0 steps expected.
            if status_callback:
                status_callback(f"No silence periods found for video {index+1} of {total}, skipping downscale.")
            return segment_files
            
        if status_callback:
            status_callback(f"Downscaling {len(silence_periods)} silent segments using individual calls")
        
        for i, period in enumerate(silence_periods):
            # Define paths and times
            start_time = period['start']
            end_time = period['end']
            duration = end_time - start_time
            segment_filename = f"downscaled_{original_filename_base}_seg{i}.mp4"
            segment_path = output_dir_path / segment_filename

            if duration <= 0:
                if status_callback:
                    status_callback(f"Skipping invalid segment {i+1}/{len(silence_periods)} with duration {duration}s")
                # Advance progress for the skipped segment attempt
                if progress_step_downscale:
                    progress_step_downscale()
                continue
            
            # Build command
            cmd = [
                get_executable_path("ffmpeg", config.ffmpeg_path), "-threads", "0",
                "-ss", str(start_time), "-i", original_file, "-t", str(duration),
                "-vf", f"scale=-2:{config.DOWNSCALE_HEIGHT}:flags=neighbor",
                "-preset", "ultrafast", "-vcodec", "libx264", "-crf", "23", "-an",
                str(segment_path), "-y", "-hide_banner", "-loglevel", "error"
            ]
            
            # Run command
            try:
                if status_callback:
                    status_callback(f"Downscaling segment {i+1}/{len(silence_periods)} ({start_time:.2f}s-{end_time:.2f}s)")
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _, stderr = process.communicate()
                process.terminate() # Ensure process is terminated
                
                stderr_str = stderr.decode('utf-8', errors='ignore')
                if "Error" in stderr_str and status_callback:
                    status_callback(f"Error downscaling segment {i+1}: {stderr_str}")
                    # Don't add file, but DO step progress
                elif segment_path.exists() and segment_path.stat().st_size > 0:
                    segment_files.append({
                        'path': str(segment_path), 'start_time': start_time,
                        'end_time': end_time, 'segment_index': i
                    })
                else:
                    if status_callback:
                        status_callback(f"Warning: Segment file {i+1} wasn't created successfully.")
                    # Don't add file, but DO step progress
                        
            except Exception as e:
                if status_callback:
                    status_callback(f"Unexpected error downscaling segment {i+1}: {str(e)}")
                # Don't add file, but DO step progress
            
            finally:
                 # Always advance progress for this segment attempt
                if progress_step_downscale:
                    progress_step_downscale()

        # Final status
        if status_callback:
            success_rate = len(segment_files) / len(silence_periods) * 100 if silence_periods else 0
            status_callback(f"Successfully downscaled {len(segment_files)}/{len(silence_periods)} segments ({success_rate:.1f}%)")
        
        return segment_files


class SilenceDetector:
    def detect(self, input_file, status_callback):
        sections = FFMpegSilence.detect(input_file, status_callback)
        return self._merge(sections)

    def _merge(self, sections):
        if not sections:
            return []
        sections.sort(key=lambda s: s['start'])
        merged = [sections[0].copy()]
        for s in sections[1:]:
            if s['start'] <= merged[-1]['end']:
                merged[-1]['end'] = max(s['end'], merged[-1]['end'])
            else:
                merged.append(s.copy())
        return merged


class FFMpegSilence:
    @staticmethod
    def detect(input_file, status_callback=None):
        if not Path(input_file).is_file():
            return []
        try:
            cmd = [
                get_executable_path("ffmpeg", config.ffmpeg_path),
                "-threads", "0",
                "-i", input_file,
                "-vn",
                "-ar", "8000",
                "-ac", "1",
                "-af", f"silencedetect=n={config.DECIBEL_THRESHOLD}dB:d={config.SILENCE_DURATION}",
                "-preset", "ultrafast",
                "-f", "null",
                "-"
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, stderr = proc.communicate()
            proc.terminate()
            if b"Error" in stderr and status_callback:
                raise Exception(f"FFmpeg encountered an error while detecting silence: {stderr.decode('utf-8')}")
            lines = [line.decode('utf-8') for line in stderr.splitlines() if 'silence_' in line.decode('utf-8')]
            silences = []
            for i in range(0, len(lines), 2):
                start = float(lines[i].split()[4])
                end = None
                if i+1 < len(lines):
                    end = float(lines[i+1].split()[4])
                if end is not None:
                    silences.append({'start': start, 'end': end})
                elif status_callback:
                    status_callback(f"Warning: Missing silence end time for start time {start} in file {input_file}")
            return silences
        except Exception as e:
            if status_callback:
                status_callback(f"An error occurred while detecting silence in {input_file}: {str(e)}")
            return []


class BlackFrameAnalyzer:
    def analyze(
        self, video_loader, silence_periods,
        status_callback, progress_step,
        processed_frames, total_frames
    ):
        timestamps = []
        flat_ts = sorted([t for p in silence_periods for t in (p['start'], p['end'])])
        if not flat_ts:
            frame_count = video_loader.get_frame_count()
            for _ in range(frame_count):
                processed_frames += 1
                progress_step()
            return [], processed_frames
        for frame in video_loader:
            frame_time = video_loader.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            processed_frames += 1
            progress_step()
            idx = bisect_left(flat_ts, frame_time)
            if idx > 0 and idx % 2 != 0:
                if np.mean(np.asarray(frame)) < config.BLACK_FRAME_THRESHOLD:
                    timestamps.append(frame_time)
        return timestamps, processed_frames
    
    def analyze_segments(
        self, segment_files, 
        status_callback, progress_step,
        processed_frames, total_frames
    ):
        """
        Analyze multiple downscaled video segments for black frames.
        
        Args:
            segment_files: List of dicts containing segment file information
            status_callback: Function to report status messages
            progress_step: Function to increment progress bar
            processed_frames: Counter of frames processed so far
            total_frames: Total frames to process (for progress calculation)
            
        Returns:
            tuple: (list of detected black frame timestamps, count of processed frames)
        """
        timestamps = []
        
        if not segment_files:
            if status_callback:
                status_callback("No segments to analyze.")
            return timestamps, processed_frames
            
        # Pre-count frames in all segments to ensure accurate progress
        total_segment_frames = 0
        segments_with_frames = []
        
        if status_callback:
            status_callback(f"Counting frames in {len(segment_files)} segments for accurate progress tracking...")
            
        for segment in segment_files:
            try:
                temp_loader = VideoLoader(segment['path'])
                segment_frame_count = temp_loader.get_frame_count()
                temp_loader.release()
                
                if segment_frame_count > 0:
                    # Add frame count to segment data
                    segment_with_frames = segment.copy()
                    segment_with_frames['frame_count'] = segment_frame_count
                    segments_with_frames.append(segment_with_frames)
                    total_segment_frames += segment_frame_count
                else:
                    if status_callback:
                        status_callback(f"Warning: Segment {segment['segment_index']} has no frames, skipping.")
            except Exception as e:
                if status_callback:
                    status_callback(f"Error counting frames in segment {segment['segment_index']}: {str(e)}")
        
        if status_callback:
            status_callback(f"Found {total_segment_frames} frames to analyze across {len(segments_with_frames)} segments.")

        # Check for possible progress inconsistency
        if total_segment_frames == 0:
            if status_callback:
                status_callback("No valid frames found in segments, skipping analysis.")
            return timestamps, processed_frames
        
        # Process each segment
        for i, segment in enumerate(segments_with_frames):
            segment_path = segment['path']
            segment_start_time = segment['start_time']
            segment_end_time = segment['end_time']
            segment_frame_count = segment['frame_count']
            
            if status_callback:
                status_callback(f"Analyzing segment {i+1}/{len(segments_with_frames)}: " +
                               f"{segment_frame_count} frames from {segment_start_time:.2f}s to {segment_end_time:.2f}s")
            
            loader = None
            try:
                loader = VideoLoader(segment_path)
                
                for frame in loader:
                    # Get time within the segment
                    frame_time_in_segment = loader.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                    
                    # Calculate actual time in original video
                    actual_frame_time = segment_start_time + frame_time_in_segment
                    
                    # Verify the timestamp is within expected bounds
                    if actual_frame_time < segment_start_time or actual_frame_time > segment_end_time:
                        if status_callback:
                            status_callback(f"Warning: Frame timestamp {actual_frame_time:.3f}s outside segment " +
                                          f"bounds ({segment_start_time:.3f}s-{segment_end_time:.3f}s). Adjusting.")
                        # Clamp to ensure we're in range
                        actual_frame_time = max(segment_start_time, min(actual_frame_time, segment_end_time))
                    
                    # Check if this is a black frame
                    if np.mean(np.asarray(frame)) < config.BLACK_FRAME_THRESHOLD:
                        timestamps.append(actual_frame_time)
                    
                    # Update progress
                    processed_frames += 1
                    progress_step()
                    
            except Exception as e:
                if status_callback:
                    status_callback(f"Error analyzing segment {i+1}: {str(e)}")
                
                # Account for frames we couldn't process for progress bar accuracy
                remaining_frames = segment_frame_count - (processed_frames - (processed_frames % segment_frame_count))
                if remaining_frames > 0:
                    if status_callback:
                        status_callback(f"Accounting for {remaining_frames} unprocessed frames in progress bar")
                    for _ in range(remaining_frames):
                        processed_frames += 1
                        progress_step()
            finally:
                if loader:
                    loader.release()
        
        # Sort timestamps as they come from multiple segments that might overlap
        timestamps.sort()
        
        return timestamps, processed_frames


class TimestampReducer:
    @staticmethod
    def reduce(timestamps):
        if not timestamps:
            return []
        filtered = [t for t in timestamps if t >= config.START_BUFFER]
        if not filtered:
            return []
        reduced = [filtered[0]]
        for t in filtered[1:]:
            if t - reduced[-1] > config.TIMESTAMP_THRESHOLD:
                reduced.append(t)
        return reduced


class ResourceCleaner:
    def clean(self, video_loader, downscaled_file, status_callback=None):
        try:
            if video_loader and hasattr(video_loader, 'cap') and video_loader.cap.isOpened():
                video_loader.release()
        except Exception as e:
            if status_callback:
                status_callback(f"Error releasing video loader: {e}")
        if downscaled_file:
            df = Path(downscaled_file)
            if df.exists():
                try:
                    df.unlink()
                    if status_callback:
                        status_callback("Successfully deleted downscaled file")
                except Exception as e:
                    if status_callback:
                        status_callback(f"Error deleting downscaled file: {e}")
    
    def clean_segments(self, segment_files, status_callback=None):
        """
        Delete all segment files after processing.
        
        Args:
            segment_files: List of dictionaries containing segment file information
            status_callback: Function to report status messages
        """
        if not segment_files:
            return
            
        if status_callback:
            status_callback(f"Cleaning up {len(segment_files)} temporary segment files...")
            
        for segment in segment_files:
            segment_path = Path(segment['path'])
            if segment_path.exists():
                try:
                    segment_path.unlink()
                except Exception as e:
                    if status_callback:
                        status_callback(f"Error deleting segment file {segment['segment_index']}: {str(e)}")
                        
        if status_callback:
            status_callback("Successfully cleaned up all segment files.")
