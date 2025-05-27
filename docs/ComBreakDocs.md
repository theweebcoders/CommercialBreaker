# Complete ComBreak Application Structure Analysis

## System Overview

ComBreak is an application designed to identify commercial break points in videos that don't actually contain commercials (like DVD rips). It analyzes videos to find the transition markers (silent black frames) that typically indicate where commercial breaks would start or end, then optionally cuts the videos at these points or records these locations without modifying the files.

## Core Components and Data Flow

### Input Phase
1. **User Input Collection**
   - The GUI (CommercialBreakerGUI.py) offers two input modes:
     - **Folder Mode (Legacy)**: Processes all videos in a specified directory structure
     - **File Selection Mode**: Allows users to select specific video files
   - The GUI also collects:
     - Output directory location
     - Processing mode selections (Destructive, Fast, Low Power, Cutless)

2. **Input Processing**
   - The EnhancedInputHandler consolidates all inputs into a unified list, handling:
     - Individual files
     - Complete folders with subfolders
     - Mixed selection of files and folders
   - Creates a canonical list of files to process using `get_consolidated_paths()`
   - Maintains separation of concerns between UI and file handling logic

### Detection Phase

1. **Initialization**
   - CommercialBreakerLogic initializes the detection process by:
     - Creating a fresh VideoFilesManager instance to track which files need processing
     - Adding all candidate video files to this manager
     - Setting up progress tracking and callback mechanisms

2. **Detection Methods (in priority order)**
   - **Chapter Extraction (first priority)**
     - ChapterExtractor processes each video to find embedded chapter markers
     - Uses FFprobe to examine video metadata for chapter information
     - If chapters are found:
       - Creates timestamp files (.txt) with chapter start times
       - Removes these files from the VideoFilesManager (no further processing needed)
   
   - **Mode-Based Detection (second and third priority)**
     - Based on user-selected mode:
       
       **Low Power Mode:**
       - Skips black frame detection entirely
       - Only attempts to read existing timestamps from plex_timestamps.txt files
       
       **Fast Mode:**
       - First tries to find timestamps in plex_timestamps.txt
       - Then performs silent black frame detection on remaining files
       
       **Normal Mode:**
       - First performs silent black frame detection on all files
       - Then tries timestamp files for any remaining files

3. **Silent Black Frame Detection**
   - **Architecture:**
     - Uses a composition of specialized classes with single responsibilities
     - SilentBlackFrameDetector delegates to SilentBlackFrameOrchestrator
     - Process is broken down into discrete, focused components
   
   - **Optimized Process Flow:**
     - VideoFileGatherer: Identifies files needing processing
     - For each video file:
       - SilenceDetector: First identifies silent sections using FFmpeg
       - VideoPreprocessor: Creates downscaled copies of ONLY the silent segments (not the entire video)
       - BlackFrameAnalyzer: Examines frames in the downscaled segments for darkness
       - TimestampReducer: Filters timestamps to remove false positives
       - ResourceCleaner: Releases resources and removes temporary segment files
   
   - **Precision Progress Tracking:**
     - ProgressManager tracks three distinct phases:
       - Silence detection (one step per file)
       - Downscaling (one step per silent segment)
       - Frame analysis (one step per frame analyzed)
     - Pre-calculates total steps by scanning all files for silence periods before processing
     - Ensures progress bar is 100% accurate throughout the entire process
   
   - **Error Handling:**
     - Each component has dedicated error handling
     - Process continues even if individual file or segment processing fails
     - Progress bar advances correctly even when errors occur
     - Detailed status reporting at each stage

4. **Final Timestamp Cleanup**
   - TimestampManager's `cleanup_timestamps` method:
     - Processes all timestamp files in the output directory
     - Re-applies the two-stage filtering to ensure consistency
     - Particularly important since timestamps might come from different sources (chapters, manual files, detection)

### Cutting Phase

1. **Preparation**
   - VideoCutter's `cut_videos` method:
     - Uses `gather_video_files_to_cut` to identify files with corresponding timestamp files
     - Creates a list of (input_file, output_file_prefix) pairs for processing
  
2. **Mode Selection**
   - **Cutless Mode:**
     - Doesn't physically cut files
     - VirtualCut's `generate_virtual_prep_data` creates database entries with:
       - Show information (extracted from filenames)
       - Part numbers
       - Start and end timestamps
     - Stores this information in an SQLite database for external applications
     - Sets flags in the database to indicate cutless mode was used
   
   - **Standard Cutting Mode:**
     - For each video with timestamps:
       - Reads timestamp file
       - Determines video duration using FFprobe
       - Uses FFmpeg's segment feature to cut at each timestamp
       - Creates output files named with part numbers
   
   - **Destructive Mode:**
     - Same as standard mode, but additionally:
       - Deletes original files after successful cutting

3. **Post-Processing**
   - Renames output files to use cleaner numbering (from "Part 001" to "Part 1", etc.)
   - Tracks and reports any failed videos
   - Creates a failedtocut.txt file if any videos couldn't be processed

### Cleanup Phase
- When user requests deletion (Delete button):
  - Removes all .txt files in the output directory structure
  - Maintains the cut video files

## Component-by-Component Detailed Analysis

### 1. ChapterExtractor.py
- **Purpose:** Identifies pre-existing chapter markers in videos as potential commercial break points
- **Key Methods:**
  - `extract_chapters(input_path, output_path, unprocessed_files_manager, ...)`
    - Processes all videos from the input handler or directory
    - For each video, calls `get_chapters` to find embedded chapters
    - If chapters are found:
      - Creates output directory preserving structure
      - Writes timestamps to .txt files
      - Removes file from unprocessed_files_manager
    - Updates progress and status via callbacks
  
  - `get_chapters(video_file)`
    - Uses FFprobe to extract chapter metadata in JSON format
    - Parses the JSON to extract start and end times
    - Returns a list of chapter objects with start/end timestamps
    - Handles exceptions and reports errors

### 2. CommercialBreakerGUI.py
- **Purpose:** Provides the graphical interface for the application
- **Key Components:**
  - Input mode selection (folder vs. file)
  - File/folder input controls with browse buttons
  - File list display with add/remove capabilities
  - Output directory selection
  - Mode checkboxes with mutual exclusion logic:
    - Fast Mode and Low Power Mode are mutually exclusive
    - Destructive Mode and Cutless Mode are mutually exclusive
  - Progress bar and status display
  - Action buttons (Detect, Cut, Delete, Exit)
  
- **Processing Flow:**
  - Collects user input and configuration
  - Validates directories and selections
  - Hands off processing to CommercialBreakerLogic
  - Updates UI based on progress/status callbacks
  - Displays completion messages and errors

### 3. CommercialBreakerLogic.py
- **Purpose:** Acts as the orchestration layer between UI and processing components
- **Key Methods:**
  - `detect_commercials(input_path, output_path, ...)`
    - Creates and manages VideoFilesManager
    - Coordinates the detection workflows:
      1. ChapterExtractor for embedded chapters
      2. Mode-based detection sequence (SilentBlackFrameDetector and/or TimestampManager)
      3. Final timestamp cleanup
    - Provides progress updates via callbacks
  
  - `cut_videos(input_path, output_path, ...)`
    - Delegates to VideoCutter for actual cutting
    - Passes through mode settings (destructive_mode, cutless_mode)
  
  - `delete_files(output_path)`
    - Delegates to VideoCutter.delete_files for cleanup

### 4. EnhancedInputHandler.py
- **Purpose:** Flexible input handling for various selection types
- **Key Methods:**
  - `add_files(file_paths)`
    - Adds individual files to processing list
    - Verifies they are valid video files (by extension)
    - Stores absolute paths for consistency
  
  - `add_folders(folder_paths)`
    - Adds entire folders for processing
    - Will recursively find all video files within
  
  - `get_consolidated_paths()`
    - Returns a deduplicated list of all video files from all sources
    - Uses caching for performance
  
  - `get_output_path_for_file(input_file, output_base_dir)`
    - Determines appropriate output location preserving structure
    - For folder inputs: maintains full directory structure
    - For individual files: attempts to preserve show/season structure
    - Creates intelligent paths even for individual selections

### 5. SilentBlackFrameDetector.py
- **Purpose:** Core detection logic using audio silence + black frames
- **Architecture:** Decomposed into specialized classes for better separation of concerns

- **Class Hierarchy and Detailed Method Descriptions:**

  - **SilentBlackFrameDetector**
    - Acts as entry point and facade to the detection system
    - Methods:
      - `__init__(input_handler)`: Initializes with input handler and creates orchestrator
      - `detect_silent_black_frames(input_path, output_path, ...)`: Main entry point that resets the UI and delegates to the orchestrator
  
  - **ProgressManager**
    - Tracks progress across three distinct processing phases with separate counters
    - Methods:
      - `__init__(downscale_count, silence_count, frame_count, progress_cb)`: Initializes with separate counts for each phase
      - `_update_progress()`: Internal method to calculate total progress and call the callback
      - `step_silence()`: Increments the silence detection counter and updates progress
      - `step_downscale()`: Increments the downscaling counter and updates progress
      - `step_frame()`: Increments the frame analysis counter and updates progress
      - `force_complete()`: Forces progress to 100% at the end of processing
  
  - **SilentBlackFrameOrchestrator**
    - Coordinates the entire detection workflow from gathering to final timestamp writing
    - Methods:
      - `__init__(input_handler)`: Initializes all component classes
      - `run(input_path, output_path, ...)`: Main workflow method that:
        1. Gathers files to process
        2. Pre-scans videos to identify silence periods
        3. Calculates accurate work units for progress tracking
        4. Processes each file through all stages
        5. Handles errors and ensures progress bar accuracy
      - `_write_timestamps(filename, output_dir, timestamps, status_callback)`: Writes detected timestamps to file
  
  - **VideoFileGatherer**
    - Identifies files needing processing by checking existing timestamp files
    - Methods:
      - `__init__(input_handler)`: Initializes with the input handler
      - `gather(input_path, output_path, ...)`: Processes all files from the unprocessed_files_manager:
        - Skips files that already have timestamp files
        - Prepares output directories maintaining original structure
        - Returns list of (filename, original_file, output_directory) tuples for processing
  
  - **VideoPreprocessor**
    - Creates downscaled versions of videos for faster processing
    - Methods:
      - `preprocess(original_file, output_dir, ...)`: Creates a downscaled copy of the entire video (legacy method)
      - `preprocess_segments(original_file, output_dir, silence_periods, ...)`: Targeted approach that:
        - Takes a list of silence periods (start/end times)
        - Creates a separate downscaled video file for each silence period
        - Uses optimized FFmpeg parameters with "-ss" before "-i" for efficient seeking
        - Returns a list of segment metadata including paths and timestamps
        - Advances progress bar for each segment processed
  
  - **SilenceDetector**
    - Identifies silent sections in videos where commercial transitions typically occur
    - Methods:
      - `detect(input_file, status_callback)`: Detects silence in a video file:
        - Delegates to FFMpegSilence for raw detection
        - Calls _merge to combine adjacent/overlapping silence periods
        - Returns list of silence period objects with start/end times
      - `_merge(sections)`: Combines overlapping silence periods:
        - Takes raw silence periods that might overlap
        - Sorts by start time
        - Merges any periods where one starts before another ends
        - Returns optimized list with fewer, larger silence periods
  
  - **FFMpegSilence**
    - Handles the direct interaction with FFmpeg for silence detection
    - Methods:
      - `detect(input_file, status_callback)`: Static method that:
        - Uses FFmpeg with silencedetect filter
        - Configures detection based on config.DECIBEL_THRESHOLD and config.SILENCE_DURATION
        - Parses FFmpeg output to extract silence_start and silence_end markers
        - Returns raw list of silence periods with start/end times
  
  - **BlackFrameAnalyzer**
    - Analyzes video frames to identify those below the brightness threshold
    - Methods:
      - `analyze(video_loader, silence_periods, ...)`: Analyzes full video (legacy method):
        - Processes each frame in the downscaled video
        - Checks if frame falls within a silence period
        - Tests brightness against config.BLACK_FRAME_THRESHOLD
        - Returns list of timestamps where black frames occur in silence periods
      - `analyze_segments(segment_files, ...)`: Optimized segment-based approach:
        - Pre-counts frames in all segments for accurate progress tracking
        - Processes each segment individually
        - Translates segment-relative frame times to original video timeline
        - Validates and adjusts timestamps that fall outside expected bounds
        - Updates progress for each frame analyzed
        - Returns consolidated, sorted list of black frame timestamps
  
  - **TimestampReducer**
    - Filters timestamps to remove false positives and duplicates
    - Methods:
      - `reduce(timestamps)`: Static method that applies two-stage filtering:
        1. Remove timestamps < config.START_BUFFER from video start
        2. Remove timestamps < config.TIMESTAMP_THRESHOLD from previous timestamp
        - Returns filtered list of significant black frame timestamps
  
  - **ResourceCleaner**
    - Ensures proper cleanup of temporary files and resources
    - Methods:
      - `clean(video_loader, downscaled_file, status_callback)`: Cleans up after full-video processing:
        - Releases VideoLoader resources
        - Deletes temporary downscaled video file
      - `clean_segments(segment_files, status_callback)`: Cleans up after segment-based processing:
        - Takes list of segment files created during processing
        - Deletes each temporary segment file
        - Reports cleanup status through callback

- **Processing Workflow in Detail:**

  1. **Initialization**:
     - SilentBlackFrameDetector's detect_silent_black_frames method is called
     - UI is reset and control is passed to SilentBlackFrameOrchestrator.run
  
  2. **Gathering Phase**:
     - VideoFileGatherer processes all files from unprocessed_files_manager
     - Skips files that already have timestamp files
     - Prepares output directories preserving original structure
     - Returns list of (filename, original_file, output_directory) tuples
  
  3. **Pre-calculation Phase**:
     - Sets silence_steps_total = number of videos
     - Iterates through each file to:
       - Detect silence periods using SilenceDetector
       - Count downscale_steps_total = total number of silence periods across all files
       - Estimate frame_steps_total using video FPS and silence period durations
     - Creates accurate ProgressManager with all three counts
  
  4. **Processing Phase**: For each file:
     - Step silence progress (silence detection already done in pre-scan)
     - If silence periods exist:
       - Downscale each silent segment individually using VideoPreprocessor.preprocess_segments
       - Step progress for each segment downscaled
     - If segment files were created:
       - Analyze each segment with BlackFrameAnalyzer.analyze_segments
       - Translate segment timestamps to original video timeline
       - Step progress for each frame analyzed
     - Filter timestamps using TimestampReducer.reduce
     - Write timestamp file with _write_timestamps
     - Clean up segment files with ResourceCleaner.clean_segments
  
  5. **Progress Finalization**:
     - Call ProgressManager.force_complete() to ensure progress reaches exactly 100%
     - Return total count of processed frames

- **Key Technical Aspects:**

  1. **Targeted Downscaling Strategy**:
     - Only processes silent segments of videos where commercial breaks likely occur
     - Each segment is extracted with "-ss {start} -i {file} -t {duration}" for efficient seeking
     - Creates small MP4 files for each segment rather than one large downscaled file
     - Uses specific FFmpeg parameters optimized for detection rather than quality

  2. **Three-Phase Progress Tracking**:
     - Silence detection: One step per video file
     - Downscaling: One step per silence segment
     - Frame analysis: One step per frame analyzed
     - Pre-calculation ensures progress bar accuracy throughout process
     - Step-specific methods ensure progress is tracked correctly for each phase

  3. **Timestamp Calculation and Validation**:
     - Segment-based timestamps must be translated back to original video timeline
     - frame_time_in_segment + segment_start_time = actual_frame_time
     - Boundary validation ensures timestamps don't fall outside expected segment range
     - Final timestamps are sorted to handle potential segment overlap

  4. **Error Handling and Recovery**:
     - Each phase has dedicated error handling to ensure process continues
     - When errors occur, progress steps are still accounted for
     - Temporary files are cleaned up even after errors
     - Status messages provide detailed error information

  5. **Configuration Parameters**:
     - config.DOWNSCALE_HEIGHT: Height for downscaled video (width maintains aspect ratio)
     - config.DECIBEL_THRESHOLD: Audio level threshold for silence detection (e.g., -40dB)
     - config.SILENCE_DURATION: Minimum duration for silence detection (e.g., 0.5 seconds)
     - config.BLACK_FRAME_THRESHOLD: Brightness threshold for black frame detection
     - config.FRAME_RATE: Frame sampling rate reduction factor
     - config.START_BUFFER: Minimum time from start for valid timestamps
     - config.TIMESTAMP_THRESHOLD: Minimum separation between timestamps

### 6. TimestampManager.py
- **Purpose:** Handles pre-existing timestamps and cleanup
- **Key Methods:**
  - `cleanup_timestamps(output_path, ...)`
    - Finds all timestamp files in output directory
    - For each file:
      - Reads timestamps
      - Applies reduce_timestamps to filter values
      - Writes back cleaned timestamps
  
  - `read_timestamps(input_path, output_path, ...)`
    - Looks for plex_timestamps.txt files
    - Parses file for timestamp mappings (filename = timestamp)
    - For matching files in unprocessed_files_manager:
      - Creates output directory
      - Writes timestamp to .txt file
      - Removes file from unprocessed manager
  
  - `reduce_timestamps(timestamps)`
    - Two-stage filtering:
      1. Remove timestamps < config.START_BUFFER
      2. Remove timestamps < config.TIMESTAMP_THRESHOLD from previous

### 7. VideoCutter.py
- **Purpose:** Cuts videos at identified break points
- **Key Methods:**
  - `cut_videos(input_path, output_path, ...)`
    - Calls appropriate gather method for input mode
    - For cutless mode, calls VirtualCut.generate_virtual_prep_data
    - For standard mode, processes each video with cut_single_video
    - Tracks and records failures
    - Calls rename_files for cleanup
  
  - `gather_video_files_to_cut_enhanced(output_path)` / `gather_video_files_to_cut(...)`
    - Identifies files with corresponding timestamp files
    - Prepares (input_file, output_file_prefix) pairs
    - Tracks output directories for later renaming
  
  - `cut_single_video(input_file, output_file_prefix, ...)`
    - Appends video end time to timestamps
    - Uses FFmpeg's segment feature to cut at each timestamp
    - Creates output files with incrementing part numbers
    - Handles destructive mode deletion if enabled
  
  - `rename_files(output_dir)`
    - Cleans up part numbering (from "Part 001" to "Part 1", etc.)
    - Makes output files more user-friendly

### 8. VideoFileManager.py
- **Purpose:** Singleton tracking which files still need processing
- **Key Features:**
  - Uses a namedtuple 'VideoFile' to track original_file, dirpath, and filename
  - Maintains a single instance across the application
  - Provides methods to add, remove, query, and clear files
  - Crucial for tracking progress through multiple detection methods

### 9. VideoLoader.py
- **Purpose:** Simplified interface for OpenCV video processing
- **Key Features:**
  - Implements Python iterator protocol for easy frame-by-frame access
  - Applies frame rate reduction (only processes every Nth frame)
  - Provides utility methods for frame count and resource cleanup

### 10. VirtualCut.py
- **Purpose:** Implements "cutless mode" database recording
- **Key Method:**
  - `generate_virtual_prep_data(video_files_data, ...)`
    - Creates SQLite database tables if needed
    - For each video with timestamps:
      - Extracts show name and season/episode from filename
      - Creates virtual entries for each segment
      - Records original path, virtual path, and start/end times
    - Handles table creation, deduplication, and updates
    - Sets a flag in app_data to indicate cutless mode was used

## Special Modes and Their Effects

### Fast Mode
- Prioritizes using existing timestamp information before detection
- Processing sequence:
  1. Chapter extraction
  2. Read timestamps from plex_timestamps.txt
  3. Only perform silent black frame detection on remaining files
- Benefits: Faster processing when existing timestamps are available

### Low Power Mode
- Completely skips the resource-intensive detection process
- Processing sequence:
  1. Chapter extraction
  2. Read timestamps from plex_timestamps.txt
  3. Stop (no black frame detection)
- Benefits: Minimal resource usage, good for systems with limited power

### Cutless Mode
- Records cut points without modifying original files
- Operation:
  1. Still performs full detection process
  2. Instead of cutting, records information in SQLite database
  3. External applications can use this data to perform "virtual cuts"
- Benefits: Non-destructive, compatible with external media systems

### Destructive Mode
- Deletes original files after successful cutting
- Operation:
  1. Performs normal cutting process
  2. After verifying successful cut, deletes original file
- Benefits: Saves disk space by removing redundant originals

## Configuration Parameters

The application uses a `config.py` file (not provided) that contains important parameters:
- `video_file_types`: List of supported video extensions
- `DOWNSCALE_HEIGHT`: Resolution for downscaled processing copies
- `DECIBEL_THRESHOLD`: Audio level threshold for silence detection
- `SILENCE_DURATION`: Minimum duration for silence detection
- `BLACK_FRAME_THRESHOLD`: Brightness threshold for black frame detection
- `FRAME_RATE`: Frame sampling rate reduction factor
- `START_BUFFER`: Minimum time from start for valid timestamps
- `TIMESTAMP_THRESHOLD`: Minimum separation between timestamps
- `ffmpeg_path` and `ffprobe_path`: Paths to external tools

## Typical Application Workflow

1. **User Interaction:**
   - User selects input (files or folder)
   - User selects output directory
   - User selects processing modes (Fast/Low Power, Cutless/Destructive)
   - User clicks "Detect" button

2. **Detection Process:**
   - Files are gathered based on input selection
   - ChapterExtractor attempts to find embedded chapters
   - Based on mode, TimestampManager and/or SilentBlackFrameDetector process remaining files
   - Timestamps are cleaned up and finalized
   - Status updates appear in the UI

3. **Cutting Process:**
   - User clicks "Cut" button
   - Based on mode (standard or cutless), files are either:
     - Cut into separate files at timestamp points or
     - Recorded in database for virtual cutting
   - Output files are renamed for consistency
   - Status updates appear in the UI

4. **Optional Cleanup:**
   - User clicks "Delete" button to remove timestamp files
   - Original files are preserved unless Destructive Mode was used
