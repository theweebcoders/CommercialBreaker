import os
import re
import pandas as pd
import sqlite3
import config


class AnimeFileOrganizer:
    def __init__(self, anime_dir):
        self.anime_dir = anime_dir
        db_path = config.DATABASE_PATH
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def organize_files(self):
        print(f"Starting to organize files in {self.anime_dir}...")

        # Regex pattern to match anime name, season, episode, and part
        pattern = r'^(.+) - (S\d{2}E\d{2}) - .+ - Part (\d+)'

        # Create a list to hold the data
        data = []

        print("Starting to search for .mp4 files...")

        # Iterate over the files in the directory and all its subdirectories
        for dirpath, dirnames, filenames in os.walk(self.anime_dir):
            for filename in filenames:
                if filename.endswith(".mp4"):
                    if match := re.search(pattern, filename):
                        show_name = match[1]
                        season_episode = match[2]
                        part_number = match[3]
                        path = os.path.join(dirpath, filename)
                        data.append([show_name, season_episode, part_number, path])

        print("Data has been organized into a DataFrame.")

        # Create DataFrame
        df = pd.DataFrame(data, columns=['SHOW_NAME_1', 'Season and Episode', 'Part Number', 'FULL_FILE_PATH'])

        # Check if table exists
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commercial_injector_prep'")
        table_exists = bool(self.cursor.fetchone())

        if table_exists:
            existing_df = pd.read_sql('SELECT * FROM commercial_injector_prep', self.conn)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            duplicates = combined_df.duplicated(subset=['FULL_FILE_PATH'], keep='last')
            combined_df = combined_df[~duplicates]
            combined_df.to_sql('commercial_injector_prep', self.conn, index=False, if_exists='replace')
        else:
            df.to_sql('commercial_injector_prep', self.conn, index=False, if_exists='replace')

        print(f"Completed organizing files in {self.anime_dir}.")
