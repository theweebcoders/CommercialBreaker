import pandas as pd
import os
import shutil
import sqlite3


class FilterAndMove:
    class DataFrameFilter:
        def __init__(self):
            db_path = 'toonami.db'
            self.conn = sqlite3.connect(db_path)

        def filter_and_write(self):
            print("Data loaded successfully.")
            # Load the data
            df = pd.read_sql_query("SELECT * FROM lineup_v8_uncut", self.conn)
            # Filter out the rows
            df_filtered = df[~df['FULL_FILE_PATH'].str.contains('/nice_bumps', na=False)]

            # Drop the 'Code' and 'BLOCK_ID' columns
            df_filtered = df_filtered.drop(columns=['Code', 'BLOCK_ID'])

            # Write the filtered data back to an database
            df_filtered.to_sql('lineup_v8_uncut_filtered', self.conn, index=False, if_exists='replace')
            print("Data filtered and saved.")

    class EpisodeMover:
        def __init__(self, target_directory):
            db_path = 'toonami.db'
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

    def _fake_run(self, target_directory):
        print("Faking filter and move process.")

        # Load the DataFrame from the input file
        df = pd.read_sql_query("SELECT * FROM lineup_v8_uncut_filtered", self.conn)

        # Identify unique show directories
        unique_show_dirs = set()
        for file_path in df['FULL_FILE_PATH']:
            # Normalize the path to handle inconsistencies in slash usage
            file_path = os.path.normpath(file_path)
            # Go up two levels from the file path to get the show directory
            season_dir = os.path.dirname(file_path)
            show_dir = os.path.dirname(season_dir)
            unique_show_dirs.add(show_dir)

        # Create show directories but leave them empty
        for show_dir in unique_show_dirs:
            show_name = os.path.basename(show_dir)
            dest_dir = os.path.join(target_directory, "ToonamiPlaylistShows", show_name)
            suffix = 0
            while os.path.exists(dest_dir):
                suffix += 1
                dest_dir = os.path.join(target_directory, "ToonamiPlaylistShows", show_name + f"_copy{suffix}")
            os.makedirs(dest_dir)
        print("Empty show directories created successfully.")

    def run(self, target_directory, skip=False):
        # Connect to the SQLite database
        self.conn = sqlite3.connect('toonami.db')
        print("Starting filter and move process.")

        # Create an instance of DataFrameFilter
        df_filter = self.DataFrameFilter()
        # Call the method to filter and write the DataFrame
        df_filter.filter_and_write()
        if skip:
            self._fake_run(target_directory)
        else:
            # Create an instance of EpisodeMover with the filtered data file
            episode_mover = self.EpisodeMover(target_directory)
            # Call the method to move files
            episode_mover.move_files()
        print("Filter and move process completed successfully.")
