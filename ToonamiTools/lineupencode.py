import pandas as pd
import os
import re
import sqlite3

class BlockIDCreator:
    def __init__(self):
        db_path = 'toonami.db'
        self.conn = sqlite3.connect(db_path)
        self.last_block_id = None
        print("Initialized database connection.")

    def load_data(self):
        # Load data from SQLite database
        self.df = pd.read_sql('SELECT * FROM commercial_injector', self.conn)
        print("Data loaded successfully from the SQLite database.")

    @staticmethod
    def create_block_id(path):
        # Split path into parts
        parts = os.path.normpath(path).split(os.sep)
        # Extract series name, season, and episode from path
        series_name = parts[-3]
        if season_episode := re.search(r'S\d{2}E\d{2}', parts[-1]):
            block_id = f'{series_name}-{season_episode[0]}'
            # Replace spaces and special characters with underscore and make all letters uppercase
            return re.sub(r'\W+', '_', block_id).upper()
        else:
            return None

    def assign_block_ids(self):
        # Create a new column 'BLOCK_ID'
        self.df['BLOCK_ID'] = self.df['FULL_FILE_PATH'].apply(self.create_block_id)
        print("Block IDs have been assigned.")

        # Iterate over rows
        for i in range(len(self.df)):
            # If block ID is None, use block ID from the next row
            if pd.isnull(self.df.at[i, 'BLOCK_ID']):
                if (i == 0 and i + 1 < len(self.df) and not pd.isnull(self.df.at[i + 1, 'BLOCK_ID'])) or (i + 1 < len(self.df) and not pd.isnull(self.df.at[i + 1, 'BLOCK_ID'])):
                    self.df.at[i, 'BLOCK_ID'] = self.df.at[i + 1, 'BLOCK_ID']
                else:
                    self.df.at[i, 'BLOCK_ID'] = self.last_block_id
            else:
                # Update last block ID
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