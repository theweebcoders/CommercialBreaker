import pandas as pd
import os
import re
import sqlite3
import config


class BlockIDCreator:
    def __init__(self):
        db_path = f'{config.network}.db'
        self.conn = sqlite3.connect(db_path)
        self.last_block_id = None
        print("Initialized database connection.")

    def load_data(self):
        # Load data from SQLite database
        self.df = pd.read_sql('SELECT * FROM commercial_injector', self.conn)
        print("Data loaded successfully from the SQLite database.")

    @staticmethod
    def create_block_id(path):
        # Extract filename from path
        filename = os.path.basename(path)
        
        # Search for season and episode pattern in filename
        season_episode_match = re.search(r'S\d{2}E\d{2}', filename)
        if not season_episode_match:
            return None
            
        season_episode = season_episode_match.group(0)
        
        # Extract series name by taking everything before the season/episode pattern
        series_part = filename[:season_episode_match.start()].strip()
        
        # Remove trailing separators like " - "
        series_name = re.sub(r'\s*-\s*$', '', series_part).strip()
        
        # Create block ID
        block_id = f'{series_name}-{season_episode}'
        
        # Replace spaces and special characters with underscore and make all letters uppercase
        return re.sub(r'\W+', '_', block_id).upper()

    def assign_block_ids(self):
        # Create a new column 'BLOCK_ID'
        self.df['BLOCK_ID'] = self.df['FULL_FILE_PATH'].apply(self.create_block_id)
        print("Block IDs have been assigned.")

        # Iterate over rows to fill in None values
        for i in range(len(self.df)):
            # If block ID is None, look ahead for the next valid block ID
            if pd.isnull(self.df.at[i, 'BLOCK_ID']):
                # Look ahead for the next valid block ID
                for j in range(i + 1, len(self.df)):
                    if not pd.isnull(self.df.at[j, 'BLOCK_ID']):
                        self.df.at[i, 'BLOCK_ID'] = self.df.at[j, 'BLOCK_ID']
                        break
                # If no next block ID found, use the last valid one as fallback
                if pd.isnull(self.df.at[i, 'BLOCK_ID']) and self.last_block_id is not None:
                    self.df.at[i, 'BLOCK_ID'] = self.last_block_id
            else:
                # Update last valid block ID
                self.last_block_id = self.df.at[i, 'BLOCK_ID']

    def save_data(self):
        # Drop 'SHOW_NAME_1', 'Season and Episode', and 'Part Number' columns
        self.df.drop(columns=['SHOW_NAME_1', 'Season and Episode'], inplace=True)
        print("Saving data to database...")
        self.df.to_sql('commercial_injector_final', self.conn, index=False, if_exists='replace')
        print("Data saved successfully to the SQLite database.")

    def run(self):
        print("Running the BlockIDCreator...")
        self.load_data()
        self.assign_block_ids()
        self.save_data()
        print("BlockIDCreator completed successfully.")
