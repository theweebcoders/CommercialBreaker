import os
import re
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
                        match = re.search(pattern, filename)
                        if match:
                            show_name = match[1]
                            season_episode = match[2]
                            part_number = match[3]
                            path = os.path.join(dirpath, filename)
                            data.append({
                                'SHOW_NAME_1': show_name,
                                'Season and Episode': season_episode,
                                'Part Number': part_number,
                                'FULL_FILE_PATH': path
                            })
        except Exception as e:
            self.error_manager.send_error_level(
                source="CommercialInjectorPrep",
                operation="organize_files",
                message="Error scanning output directory",
                details=str(e),
                suggestion="Check that the output folder is accessible and try again"
            )
            raise

        print("Data has been organized.")

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

        # Count unique episodes (combinations of show name and season/episode)
        unique_episodes = set()
        for row in data:
            unique_episodes.add((row['SHOW_NAME_1'], row['Season and Episode']))

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
            table_exists = self.db_manager.table_exists('commercial_injector_prep')

            if table_exists:
                # Load existing data
                existing_data = self.db_manager.fetchall_as_dicts('SELECT * FROM commercial_injector_prep')

                # Combine with new data
                combined_data = existing_data + data

                # Remove duplicates based on FULL_FILE_PATH, keeping the last occurrence
                seen_paths = {}
                for row in combined_data:
                    seen_paths[row['FULL_FILE_PATH']] = row

                combined_data = list(seen_paths.values())

                # Save combined data
                self.db_manager.replace_table_data('commercial_injector_prep', combined_data)
            else:
                # Create new table
                if data:
                    self.db_manager.create_table_from_dicts('commercial_injector_prep', data)

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
        print(f"Found {len(data)} cut episode parts from {len(unique_episodes)} unique episodes")
