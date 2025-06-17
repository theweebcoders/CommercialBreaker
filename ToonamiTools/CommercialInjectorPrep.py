import os
import re
import pandas as pd
import config
from API.utils import get_db_manager
from API.utils.ErrorManager import get_error_manager


class AnimeFileOrganizer:
    def __init__(self, anime_dir):
        self.anime_dir = anime_dir
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()

    def organize_files(self):
        print(f"Starting to organize files in {self.anime_dir}...")
        
        # Check if directory exists
        if not os.path.exists(self.anime_dir):
            self.error_manager.send_error_level(
                source="CommercialInjectorPrep",
                operation="organize_files",
                message=f"Output directory not found: {self.anime_dir}",
                details="The directory where cut episodes should be doesn't exist",
                suggestion="Make sure you've run CommercialBreaker to cut your episodes first"
            )
            raise FileNotFoundError(f"Directory not found: {self.anime_dir}")
        
        # Check if we have read permissions
        if not os.access(self.anime_dir, os.R_OK):
            self.error_manager.send_error_level(
                source="CommercialInjectorPrep",
                operation="organize_files",
                message=f"Cannot access directory: {self.anime_dir}",
                details="Permission denied when trying to read the output directory",
                suggestion="Check that you have permission to read the output folder"
            )
            raise PermissionError(f"No read access to: {self.anime_dir}")

        # Regex pattern to match anime name, season, episode, and part
        pattern = r'^(.+) - (S\d{2}E\d{2}) - .+ - Part (\d+)'

        # Create a list to hold the data
        data = []

        print("Starting to search for .mp4 files...")

        # Iterate over the files in the directory and all its subdirectories
        try:
            for dirpath, dirnames, filenames in os.walk(self.anime_dir):
                for filename in filenames:
                    if filename.endswith(".mp4"):
                        if match := re.search(pattern, filename):
                            show_name = match[1]
                            season_episode = match[2]
                            part_number = match[3]
                            path = os.path.join(dirpath, filename)
                            data.append([show_name, season_episode, part_number, path])
        except Exception as e:
            self.error_manager.send_error_level(
                source="CommercialInjectorPrep",
                operation="organize_files",
                message="Error scanning output directory",
                details=str(e),
                suggestion="Check that the output folder is accessible and try again"
            )
            raise

        print("Data has been organized into a DataFrame.")
        
        # Check if we found any cut files
        if not data:
            self.error_manager.send_error_level(
                source="CommercialInjectorPrep",
                operation="organize_files",
                message="No cut episode files found",
                details="No .mp4 files with 'Part' in the name were found in the output directory",
                suggestion="Run CommercialBreaker first to cut your episodes into parts. The cut files should have 'Part 1', 'Part 2', etc. in their names"
            )
            raise Exception("No cut episode files found")

        # Create DataFrame
        df = pd.DataFrame(data, columns=['SHOW_NAME_1', 'Season and Episode', 'Part Number', 'FULL_FILE_PATH'])
        
        # Check how many unique episodes were cut
        unique_episodes = df.groupby(['SHOW_NAME_1', 'Season and Episode']).size()
        if len(unique_episodes) < 3:
            self.error_manager.send_warning(
                source="CommercialInjectorPrep",
                operation="organize_files",
                message=f"Only {len(unique_episodes)} episodes have been cut",
                details=f"Found cut files for {len(unique_episodes)} episodes",
                suggestion="You may want to run CommercialBreaker on more episodes for a better lineup experience"
            )

        try:
            # Check if table exists
            result = self.db_manager.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='commercial_injector_prep'"
            )
            table_exists = bool(result)

            with self.db_manager.transaction() as conn:
                if table_exists:
                    existing_df = pd.read_sql('SELECT * FROM commercial_injector_prep', conn)
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    duplicates = combined_df.duplicated(subset=['FULL_FILE_PATH'], keep='last')
                    combined_df = combined_df[~duplicates]
                    combined_df.to_sql('commercial_injector_prep', conn, index=False, if_exists='replace')
                else:
                    df.to_sql('commercial_injector_prep', conn, index=False, if_exists='replace')
                    
        except Exception as e:
            self.error_manager.send_error_level(
                source="CommercialInjectorPrep",
                operation="organize_files",
                message="Failed to save cut episode data",
                details=str(e),
                suggestion="There was an issue saving your data. Try running this step again"
            )
            raise

        print(f"Completed organizing files in {self.anime_dir}.")
        print(f"Found {len(df)} cut episode parts from {len(unique_episodes)} unique episodes")