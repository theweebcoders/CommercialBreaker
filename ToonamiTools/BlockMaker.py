import pandas as pd
import os
import re
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
import config


class BlockIDCreator:
    def __init__(self):
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        self.last_block_id = None
        print("Initialized database connection.")

    def load_data(self):
        # Load data from SQLite database
        try:
            with self.db_manager.transaction() as conn:
                self.df = pd.read_sql('SELECT * FROM commercial_injector', conn)
        except Exception as e:
            self.error_manager.send_critical(
                source="BlockMaker",
                operation="load_data",
                message="Cannot read the commercial lineup data",
                details=str(e),
                suggestion="This is unexpected - the lineup was just created. Please report this issue on our Discord"
            )
            raise
            
        if self.df.empty:
            # This should never happen since CommercialInjector just ran
            self.error_manager.send_critical(
                source="BlockMaker",
                operation="load_data",
                message="Commercial lineup is empty",
                details="The commercial_injector table exists but has no data",
                suggestion="This shouldn't happen - CommercialInjector just ran. Please report this issue on our Discord"
            )
            raise Exception("No data to process")
            
        # Check if expected columns exist
        if 'FULL_FILE_PATH' not in self.df.columns:
            self.error_manager.send_critical(
                source="BlockMaker",
                operation="load_data",
                message="Commercial lineup data is corrupted",
                details="Missing required 'FULL_FILE_PATH' column",
                suggestion="The data structure is wrong. This is a bug - please report it on our Discord"
            )
            raise Exception(f"Invalid table structure")
            
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
        
        # Count how many rows got valid block IDs vs None
        valid_ids = self.df['BLOCK_ID'].notna().sum()
        total_rows = len(self.df)
        episode_files = self.df[self.df['FULL_FILE_PATH'].str.contains(r'Part \d+', na=False)].shape[0]
        
        print(f"Created block IDs for {valid_ids} out of {total_rows} files")
        
        if episode_files > 0 and valid_ids == 0:
            # This is the weird case - we have episode parts but can't create ANY block IDs
            sample_files = self.df[self.df['FULL_FILE_PATH'].str.contains(r'Part \d+', na=False)]['FULL_FILE_PATH'].head(3).tolist()
            self.error_manager.send_error_level(
                source="BlockMaker",
                operation="assign_block_ids",
                message="Cannot create episode groupings",
                details="Episode files don't have the expected 'SXXEXX' pattern in their names",
                suggestion="You need to run Commercial Breaker first. If you already did, check that CommercialBreaker didn't stop early",
            )
            print(f"Example files that couldn't be processed: {sample_files}")
            raise Exception("No valid block IDs could be created")
    
        # Use backward fill to propagate block IDs from the next valid value
        self.df['BLOCK_ID'] = self.df['BLOCK_ID'].bfill()
        
        # If there are still None values at the end, use the last valid block ID
        if self.df['BLOCK_ID'].isnull().any() and self.last_block_id is not None:
            self.df['BLOCK_ID'].fillna(self.last_block_id, inplace=True)
        
        # Update last_block_id
        last_non_null = self.df[self.df['BLOCK_ID'].notna()].tail(1)
        if not last_non_null.empty:
            self.last_block_id = last_non_null.iloc[0]['BLOCK_ID']
            
        # Final check - if we still have nulls, something unusual happened
        remaining_nulls = self.df['BLOCK_ID'].isnull().sum()
        if remaining_nulls == total_rows:
            # Everything is null - this means NO files could be assigned IDs
            self.error_manager.send_error_level(
                source="BlockMaker",
                operation="assign_block_ids", 
                message="Failed to organize any content into episode blocks",
                details="Could not determine which files belong together as episodes",
                suggestion="This may happen if your lineup contains only bumps and no actual episodes. Check that episode files were included"
            )
            raise Exception("No content could be organized into blocks")
        elif remaining_nulls > total_rows * 0.5:
            # More than half couldn't be assigned - something is wrong
            self.error_manager.send_critical(
                source="BlockMaker",
                operation="assign_block_ids",
                message=f"Many files ({remaining_nulls} out of {total_rows}) couldn't be grouped properly",
                details="Something has gone wrong with the file naming or structure",
                suggestion="Please check your file names and ensure they follow the expected 'SXXEXX' format. If not, report it on our Discord"
            )

    def save_data(self):
        # Drop 'SHOW_NAME_1', 'Season and Episode', and 'Part Number' columns
        columns_to_drop = ['SHOW_NAME_1', 'Season and Episode']
        existing_columns_to_drop = [col for col in columns_to_drop if col in self.df.columns]
        
        if existing_columns_to_drop:
            self.df.drop(columns=existing_columns_to_drop, inplace=True)
            
        print("Saving data to database...")
        try:
            with self.db_manager.transaction() as conn:
                self.df.to_sql('commercial_injector_final', conn, index=False, if_exists='replace')
        except Exception as e:
            self.error_manager.send_error_level(
                source="BlockMaker",
                operation="save_data",
                message="Failed to save organized lineup",
                details=str(e),
                suggestion="There was an issue saving the final lineup structure. Try running 'Prepare Cut Anime for Lineup' again"
            )
            raise
            
        print("Data saved successfully to the SQLite database.")

    def run(self):
        print("Running the BlockIDCreator...")
        
        # This should ALWAYS exist because CommercialInjector just created it
        if not self.db_manager.table_exists('commercial_injector'):
            self.error_manager.send_critical(
                source="BlockMaker",
                operation="run",
                message="Missing expected data from previous step",
                details="The commercial_injector table doesn't exist but should have just been created",
                suggestion="This indicates a serious issue with the pipeline. Please report this on our Discord"
            )
            raise Exception("Required table not found")
            
        self.load_data()
        self.assign_block_ids()
        self.save_data()
        print("BlockIDCreator completed successfully.")