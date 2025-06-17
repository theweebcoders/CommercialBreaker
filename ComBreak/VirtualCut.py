import pandas as pd
import re 
from pathlib import Path
import config
from API.utils import get_db_manager



class VirtualCut:
    def __init__(self):
        """Initialize VirtualCut without needing a duration getter function."""
        # No need for duration_getter anymore since we don't access original files
        pass

    def generate_virtual_prep_data(self, video_files_data, total_videos, progress_callback=None, status_callback=None):
            """Generates data for commercial_injector_prep table without physical cutting."""
            prep_data = []
            db_manager = get_db_manager()
            
            # Create required tables if they don't exist
            try:
                # Check if app_data table exists and has data
                result = db_manager.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='app_data'")
                if not result:
                    db_manager.execute('''
                    CREATE TABLE IF NOT EXISTS app_data (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                    ''')
                
                # Check if commercial_injector_prep table exists
                result = db_manager.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='commercial_injector_prep'")
                if not result:
                    db_manager.execute('''
                    CREATE TABLE IF NOT EXISTS commercial_injector_prep (
                        SHOW_NAME_1 TEXT,
                        "Season and Episode" TEXT,
                        "Part Number" INTEGER,
                        FULL_FILE_PATH TEXT,
                        ORIGINAL_FILE_PATH TEXT,
                        startTime INTEGER,
                        endTime INTEGER
                    )
                    ''')
                
            except Exception as e:
                if status_callback:
                    status_callback(f"Error setting up database tables: {e}")
                
            # Process each video file to generate virtual cut data
            for i, (input_file, output_file_prefix) in enumerate(video_files_data):
                try:
                    if status_callback:
                        status_callback(f"Generating virtual data for video {i+1} of {total_videos}")

                    timestamp_file_path = f"{output_file_prefix}.txt"
                    if not Path(timestamp_file_path).exists():
                        continue
                        
                    # Read the timestamps from the file
                    with open(timestamp_file_path, "r") as f:
                        timestamps = [float(line.strip()) for line in f]
                    
                    # All we need to know is how many segments we'll have:
                    # It's the number of timestamps plus 1
                    # Define a generic duration for each segment - not used for actual cutting
                    segment_count = len(timestamps) + 1
                    
                    output_file_prefix_path = Path(output_file_prefix)
                    output_file_name_without_ext = output_file_prefix_path.stem
                    output_dir = output_file_prefix_path.parent

                    # Extract show info from the original filename
                    original_filename = Path(input_file).name
                    show_name = "Unknown Show"
                    season_episode = "S00E00"
                    pattern = r'^(.+?) - (S\d{2}E\d{2})'
                    if match := re.search(pattern, original_filename):
                        show_name = match.group(1).strip()
                        season_episode = match.group(2)

                    # Create a virtual entry for each segment
                    for part_number in range(1, segment_count + 1):
                        # Generate the virtual filename for this part
                        virtual_filename_base = f"{output_file_name_without_ext} - Part {part_number}"
                        virtual_full_path = str(output_dir / f"{virtual_filename_base}.mp4")
                        
                        # For timestamps, we don't need actual values, just NULL for first/last
                        # Start time is NULL for part 1, otherwise it's the timestamp of the previous break
                        start_time_ms = None if part_number == 1 else int(timestamps[part_number - 2] * 1000)
                        
                        # End time is NULL for last part, otherwise it's the timestamp of this break
                        end_time_ms = None if part_number == segment_count else int(timestamps[part_number - 1] * 1000)

                        prep_data.append([
                            show_name,
                            season_episode,
                            part_number,
                            virtual_full_path,  # Virtual path
                            input_file,         # Original path
                            start_time_ms,
                            end_time_ms
                        ])

                    if progress_callback:
                        progress_callback(i + 1, total_videos)

                except Exception as e:
                    if status_callback:
                        status_callback(f"Error generating virtual data for {input_file}: {e}")

            if not prep_data:
                if status_callback:
                    status_callback("No virtual data generated.")
                return

            # Create DataFrame
            df = pd.DataFrame(prep_data, columns=[
                'SHOW_NAME_1', 'Season and Episode', 'Part Number', 
                'FULL_FILE_PATH', 'ORIGINAL_FILE_PATH', 'startTime', 'endTime'
            ])

            # Save to commercial_injector_prep table
            try:
                table_name = 'commercial_injector_prep'
                result = db_manager.fetchone(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                table_exists = bool(result)

                with db_manager.transaction() as conn:
                    if table_exists:
                        existing_df = pd.read_sql(f'SELECT * FROM {table_name}', conn)
                        # Ensure columns match before concatenating
                        for col in df.columns:
                            if col not in existing_df.columns:
                                existing_df[col] = None
                        for col in existing_df.columns:
                            if col not in df.columns:
                                df[col] = None
                        
                        combined_df = pd.concat([existing_df, df], ignore_index=True)
                        # Use FULL_FILE_PATH for deduplication
                        duplicates = combined_df.duplicated(subset=['FULL_FILE_PATH'], keep='last')
                        combined_df = combined_df[~duplicates]
                        combined_df.to_sql(table_name, conn, index=False, if_exists='replace')
                        if status_callback:
                            status_callback(f"Updated {table_name} table with {len(combined_df)} entries.")
                    else:
                        df.to_sql(table_name, conn, index=False, if_exists='replace')
                        if status_callback:
                            status_callback(f"Created {table_name} table with {len(df)} entries.")
                
                # Set the cutless mode flag in app_data
                db_manager.execute("INSERT OR REPLACE INTO app_data (key, value) VALUES (?, ?)", ('cutless_mode_used', 'True'))
                if status_callback:
                    status_callback("Set Cutless Mode Used flag to True.")
                    
            except Exception as e:
                 if status_callback:
                    status_callback(f"Error saving virtual data or setting flag: {e}")
