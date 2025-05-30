import pandas as pd
import os
import re
import sqlite3
import config


class BlockIDCreator:
    def __init__(self):
        db_path = config.DATABASE_PATH
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
    
        # Use backward fill to propagate block IDs from the next valid value
        self.df['BLOCK_ID'] = self.df['BLOCK_ID'].bfill()
        
        # If there are still None values at the end, use the last valid block ID
        if self.df['BLOCK_ID'].isnull().any() and self.last_block_id is not None:
            self.df['BLOCK_ID'].fillna(self.last_block_id, inplace=True)
        
        # Update last_block_id
        last_non_null = self.df[self.df['BLOCK_ID'].notna()].tail(1)
        if not last_non_null.empty:
            self.last_block_id = last_non_null.iloc[0]['BLOCK_ID']

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
