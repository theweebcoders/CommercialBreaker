import pandas as pd
import os
import shutil
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
import config


class FilterAndMove:
    class DataFrameFilter:
        def __init__(self):
            self.db_manager = get_db_manager()
            self.error_manager = get_error_manager()

        def filter_and_write(self):
            print("Data loaded successfully.")
            # Load the data
            try:
                with self.db_manager.transaction() as conn:
                    df = pd.read_sql_query("SELECT * FROM lineup_v8_uncut", conn)
            except Exception as e:
                self.error_manager.send_critical(
                    source="EpisodeFilter",
                    operation="filter_and_write",
                    message="Cannot access lineup data",
                    details=str(e),
                    suggestion="Something went wrong accessing your lineup. Try running Prepare Content again"
                )
                raise
                
            if df.empty:
                self.error_manager.send_error_level(
                    source="EpisodeFilter",
                    operation="filter_and_write",
                    message="No lineup data found",
                    details="The lineup table is empty - no episodes to filter",
                    suggestion="Your lineup appears to be empty. Check that your episode and bump processing completed successfully"
                )
                raise Exception("No lineup data to filter")
                
            # Filter out the rows
            df_filtered = df[~df['FULL_FILE_PATH'].str.lower().str.contains(config.network.lower(), na=False)]
            
            if df_filtered.empty:
                self.error_manager.send_error_level(
                    source="EpisodeFilter",
                    operation="filter_and_write",
                    message="No episodes found after filtering",
                    details=f"All files in the lineup contain '{config.network}' in their path",
                    suggestion="Your lineup may only contain bump files. Check that episodes were properly included in the lineup"
                )
                raise Exception("No episodes found after filtering")

            # Drop the 'Code' and 'BLOCK_ID' columns
            df_filtered = df_filtered.drop(columns=['Code', 'BLOCK_ID'])

            # Write the filtered data back to an database
            try:
                with self.db_manager.transaction() as conn:
                    df_filtered.to_sql('lineup_v8_uncut_filtered', conn, index=False, if_exists='replace')
                print("Data filtered and saved.")
            except Exception as e:
                self.error_manager.send_error_level(
                    source="EpisodeFilter",
                    operation="filter_and_write",
                    message="Failed to save filtered data",
                    details=str(e),
                    suggestion="There was an issue saving the filtered episode list. Try running this step again"
                )
                raise

    class EpisodeMover:
        def __init__(self, target_directory):
            self.db_manager = get_db_manager()
            self.error_manager = get_error_manager()
            self.target_directory = target_directory

        def move_files(self):
            # Check if target directory exists and is writable
            if not os.path.exists(self.target_directory):
                try:
                    os.makedirs(self.target_directory)
                except Exception as e:
                    self.error_manager.send_error_level(
                        source="EpisodeFilter",
                        operation="move_files",
                        message=f"Cannot create target directory: {self.target_directory}",
                        details=str(e),
                        suggestion="Check that you have permission to create folders in the selected location"
                    )
                    raise
                    
            if not os.access(self.target_directory, os.W_OK):
                self.error_manager.send_error_level(
                    source="EpisodeFilter",
                    operation="move_files",
                    message=f"Cannot write to target directory: {self.target_directory}",
                    details="Permission denied",
                    suggestion="Check that you have write permissions for the selected folder"
                )
                raise PermissionError(f"No write access to: {self.target_directory}")
            
            # Load the DataFrame
            try:
                with self.db_manager.transaction() as conn:
                    df = pd.read_sql_query("SELECT * FROM lineup_v8_uncut_filtered", conn)
            except Exception as e:
                self.error_manager.send_critical(
                    source="EpisodeFilter",
                    operation="move_files",
                    message="Cannot read filtered episode data",
                    details=str(e),
                    suggestion="Something went wrong accessing the filtered data. Try running Prepare Content again"
                )
                raise

            # Identify unique show directories
            print("Identifying unique show directories.")
            unique_show_dirs = set()
            missing_files = []
            
            for file_path in df['FULL_FILE_PATH']:
                if file_path is None:
                    print("Warning: Encountered a None value for file_path. Skipping this row.")
                    continue

                try:
                    # Normalize the path to handle inconsistencies in slash usage
                    file_path = os.path.normpath(file_path)
                    
                    # Check if the file actually exists
                    if not os.path.exists(file_path):
                        missing_files.append(file_path)
                        continue
                        
                    # Go up two levels from the file path to get the show directory
                    season_dir = os.path.dirname(file_path)
                    show_dir = os.path.dirname(season_dir)
                    unique_show_dirs.add(show_dir)
                except Exception as e:
                    print(f"An error occurred: {e}. Skipping this row.")
                    continue

            if missing_files:
                self.error_manager.send_warning(
                    source="EpisodeFilter",
                    operation="move_files",
                    message=f"{len(missing_files)} episode files not found",
                    details=f"Some files in the lineup no longer exist at their original locations",
                    suggestion="These files may have been moved or deleted. The available files will still be processed"
                )

            print("Unique show directories successfully identified.")
            
            if not unique_show_dirs:
                self.error_manager.send_error_level(
                    source="EpisodeFilter",
                    operation="move_files",
                    message="No show directories found to move",
                    details="Could not identify any valid show directories from the episode paths",
                    suggestion="Check that your episode files still exist at their original locations"
                )
                raise Exception("No show directories to move")

            # Move show directories
            print("Initiating process to move show directories.")
            moved_count = 0
            failed_moves = []
            
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
                    moved_count += 1
                except Exception as e:
                    print(f"An error occurred while moving {show_dir}: {e}")
                    failed_moves.append((show_dir, str(e)))

            if failed_moves:
                self.error_manager.send_warning(
                    source="EpisodeFilter",
                    operation="move_files",
                    message=f"Failed to move {len(failed_moves)} show directories",
                    details=f"Successfully moved {moved_count} out of {len(unique_show_dirs)} directories",
                    suggestion="Check that the source files aren't in use or that you have proper permissions"
                )
                
            if moved_count == 0:
                self.error_manager.send_error_level(
                    source="EpisodeFilter",
                    operation="move_files",
                    message="No show directories could be moved",
                    details="All move operations failed",
                    suggestion="Check that the source files aren't locked or in use by another program"
                )
                raise Exception("Failed to move any show directories")

            print("Show directories moved successfully.")

    class FilteredFileCollector:
        def __init__(self):
            self.db_manager = get_db_manager()
            self.error_manager = get_error_manager()

        def collect_file_paths(self):
            """
            Collects unique paths to filtered files without moving them.
            
            Returns:
                list: A list of unique paths to all files that passed the filter
            """
            # Load the filtered DataFrame
            try:
                with self.db_manager.transaction() as conn:
                    df = pd.read_sql_query("SELECT * FROM lineup_v8_uncut_filtered", conn)
            except Exception as e:
                self.error_manager.send_critical(
                    source="EpisodeFilter",
                    operation="collect_file_paths",
                    message="Cannot read filtered episode data",
                    details=str(e),
                    suggestion="Something went wrong accessing the filtered data. Try running Prepare Content again"
                )
                raise
            
            if df.empty:
                self.error_manager.send_error_level(
                    source="EpisodeFilter",
                    operation="collect_file_paths",
                    message="No filtered episodes found",
                    details="The filtered episode table is empty",
                    suggestion="No episodes were identified for processing. Check your lineup generation"
                )
                raise Exception("No filtered episodes to collect")
            
            # Extract file paths from the DataFrame
            filtered_paths = set()  # Use a set instead of list to ensure uniqueness
            duplicate_count = 0
            skipped_count = 0
            missing_count = 0
            
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
                        missing_count += 1
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
                
            if missing_count > 0:
                self.error_manager.send_warning(
                    source="EpisodeFilter",
                    operation="collect_file_paths",
                    message=f"{missing_count} episode files not found",
                    details="Some episodes in the lineup no longer exist at their original locations",
                    suggestion="These files may have been moved or deleted. Available files will still be processed"
                )
                
            if not unique_paths:
                self.error_manager.send_error_level(
                    source="EpisodeFilter",
                    operation="collect_file_paths",
                    message="No valid episode files found",
                    details="All episode paths were either invalid or the files don't exist",
                    suggestion="Check that your episode files haven't been moved or deleted since the lineup was created"
                )
                raise Exception("No valid episode files to process")
                
            return unique_paths

    def __init__(self):
        self.error_manager = get_error_manager()

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
        self.db_manager = get_db_manager()
        
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