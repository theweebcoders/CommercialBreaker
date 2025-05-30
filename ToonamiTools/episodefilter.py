import pandas as pd
import os
import shutil
import sqlite3
import config


class FilterAndMove:
    class DataFrameFilter:
        def __init__(self):
            db_path = config.DATABASE_PATH
            self.conn = sqlite3.connect(db_path)

        def filter_and_write(self):
            print("Data loaded successfully.")
            # Load the data
            df = pd.read_sql_query("SELECT * FROM lineup_v8_uncut", self.conn)
            # Filter out the rows
            df_filtered = df[~df['FULL_FILE_PATH'].str.lower().str.contains(config.network.lower(), na=False)]

            # Drop the 'Code' and 'BLOCK_ID' columns
            df_filtered = df_filtered.drop(columns=['Code', 'BLOCK_ID'])

            # Write the filtered data back to an database
            df_filtered.to_sql('lineup_v8_uncut_filtered', self.conn, index=False, if_exists='replace')
            print("Data filtered and saved.")

    class EpisodeMover:
        def __init__(self, target_directory):
            db_path = config.DATABASE_PATH
            self.conn = sqlite3.connect(db_path)
            self.target_directory = target_directory

        def move_files(self):
            # Load the DataFrame
            df = pd.read_sql_query("SELECT * FROM lineup_v8_uncut_filtered", self.conn)

            # Identify unique show directories
            print("Identifying unique show directories.")
            unique_show_dirs = set()
            for file_path in df['FULL_FILE_PATH']:
                if file_path is None:
                    print("Warning: Encountered a None value for file_path. Skipping this row.")
                    continue

                try:
                    # Normalize the path to handle inconsistencies in slash usage
                    file_path = os.path.normpath(file_path)
                    # Go up two levels from the file path to get the show directory
                    season_dir = os.path.dirname(file_path)
                    show_dir = os.path.dirname(season_dir)
                    unique_show_dirs.add(show_dir)
                except Exception as e:
                    print(f"An error occurred: {e}. Skipping this row.")
                    continue

            print("Unique show directories successfully identified.")

            # Move show directories
            print("Initiating process to move show directories.")
            for show_dir in unique_show_dirs:
                show_name = os.path.basename(show_dir)
                dest_dir = os.path.join(self.target_directory, show_name)
                suffix = 0
                while os.path.exists(dest_dir):
                    suffix += 1
                    dest_dir = os.path.join(self.target_directory, show_name + f"_copy{suffix}")
                try:
                    shutil.move(show_dir, dest_dir)
                    print(f"Moved show directory: {show_dir} to {dest_dir}")
                except Exception as e:
                    print(f"An error occurred while moving {show_dir}: {e}")

            print("Show directories moved successfully.")

    class FilteredFileCollector:
        def __init__(self):
            db_path = config.DATABASE_PATH
            self.conn = sqlite3.connect(db_path)

        def collect_file_paths(self):
            """
            Collects unique paths to filtered files without moving them.
            
            Returns:
                list: A list of unique paths to all files that passed the filter
            """
            # Load the filtered DataFrame
            df = pd.read_sql_query("SELECT * FROM lineup_v8_uncut_filtered", self.conn)
            
            # Extract file paths from the DataFrame
            filtered_paths = set()  # Use a set instead of list to ensure uniqueness
            duplicate_count = 0
            skipped_count = 0
            
            for file_path in df['FULL_FILE_PATH']:
                if file_path is None:
                    print("Warning: Encountered a None value for file_path. Skipping this row.")
                    skipped_count += 1
                    continue

                try:
                    # Normalize the path to handle inconsistencies in slash usage
                    file_path = os.path.normpath(file_path)
                    # Check if the file exists before adding it to the set
                    if os.path.exists(file_path):
                        # If file is already in our set, increment duplicate count
                        if file_path in filtered_paths:
                            duplicate_count += 1
                        else:
                            filtered_paths.add(file_path)
                    else:
                        print(f"Warning: File does not exist: {file_path}")
                        skipped_count += 1
                except Exception as e:
                    print(f"An error occurred: {e}. Skipping this row.")
                    skipped_count += 1
                    continue
            
            # Convert set back to list for return value
            unique_paths = list(filtered_paths)
            
            print(f"Found {len(df)} total entries in filtered data")
            print(f"Collected {len(unique_paths)} unique filtered file paths")
            if duplicate_count > 0:
                print(f"Removed {duplicate_count} duplicate file paths")
            if skipped_count > 0:
                print(f"Skipped {skipped_count} invalid or missing file paths")
                
            return unique_paths

    def run(self, target_directory=None, prepopulate=False):
        """
        Filter episodes and either move them to a target directory or return paths without moving.
        
        Args:
            target_directory (str, optional): Directory to move filtered files to. Required if prepopulate=False.
            prepopulate (bool, optional): If True, don't move files but return paths for selection. Default is False.
            
        Returns:
            list: If prepopulate=True, returns a list of filtered file paths. Otherwise returns None.
        """
        # Connect to the SQLite database
        self.conn = sqlite3.connect(config.DATABASE_PATH)
        
        # Validate parameters based on mode
        if not prepopulate and not target_directory:
            raise ValueError("target_directory must be specified when prepopulate is False")
        
        # Log the operation mode
        mode_msg = "filter and collect" if prepopulate else "filter and move"
        print(f"Starting {mode_msg} process.")
        
        # Create an instance of DataFrameFilter and run it (needed for both modes)
        df_filter = self.DataFrameFilter()
        df_filter.filter_and_write()
        
        # Process based on mode - either collect paths or move files
        if prepopulate:
            file_collector = self.FilteredFileCollector()
            filtered_paths = file_collector.collect_file_paths()
            print(f"{mode_msg.capitalize()} process completed with {len(filtered_paths)} files.")
            return filtered_paths
        else:
            episode_mover = self.EpisodeMover(target_directory)
            episode_mover.move_files()
            print(f"{mode_msg.capitalize()} process completed successfully.")
            return None