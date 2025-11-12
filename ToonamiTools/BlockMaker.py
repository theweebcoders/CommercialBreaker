import os
import re
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
from ToonamiTools.utils.FilenameParser import FilenameParser
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
            self.data = self.db_manager.fetchall_as_dicts('SELECT * FROM commercial_injector')
        except Exception as e:
            self.error_manager.send_critical(
                source="BlockMaker",
                operation="load_data",
                message="Cannot read the commercial lineup data",
                details=str(e),
                suggestion="This is unexpected - the lineup was just created. Please report this issue on our Discord"
            )
            raise

        if len(self.data) == 0:
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
        if self.data and 'FULL_FILE_PATH' not in self.data[0]:
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
        """
        Create BLOCK_ID from file path using centralized filename parser.

        Extracts show name and season/episode, then formats as uppercase with underscores.
        Automatically handles release years in parentheses (e.g., "Show (2002)").

        Returns:
            str: BLOCK_ID in format "SHOW_NAME-S##E##" or None if parsing fails
        """
        # Extract filename from path
        filename = os.path.basename(path)

        # Parse filename using centralized parser (handles years automatically)
        parsed = FilenameParser.parse_episode_filename(filename)
        if not parsed:
            return None

        series_name = parsed['show_name']
        season_episode = parsed['season_episode']

        # Create block ID
        block_id = f'{series_name}-{season_episode}'

        # Replace spaces and special characters with underscore and make all letters uppercase
        return re.sub(r'\W+', '_', block_id).upper()

    def assign_block_ids(self):
        # Create BLOCK_ID for each row
        for row in self.data:
            row['BLOCK_ID'] = self.create_block_id(row['FULL_FILE_PATH'])

        print("Block IDs have been assigned.")

        # Count how many rows got valid block IDs vs None
        valid_ids = sum(1 for row in self.data if row.get('BLOCK_ID') is not None)
        total_rows = len(self.data)
        episode_files = sum(1 for row in self.data
                           if row.get('FULL_FILE_PATH') and
                           re.search(r'Part \d+', row['FULL_FILE_PATH']))

        print(f"Created block IDs for {valid_ids} out of {total_rows} files")

        if episode_files > 0 and valid_ids == 0:
            # This is the weird case - we have episode parts but can't create ANY block IDs
            sample_files = [row['FULL_FILE_PATH'] for row in self.data
                          if row.get('FULL_FILE_PATH') and
                          re.search(r'Part \d+', row['FULL_FILE_PATH'])][:3]
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
        # Start from the end and propagate values backward
        next_valid_id = None
        for row in reversed(self.data):
            if row.get('BLOCK_ID') is not None:
                next_valid_id = row['BLOCK_ID']
            elif next_valid_id is not None:
                row['BLOCK_ID'] = next_valid_id

        # If there are still None values at the end, use the last valid block ID
        remaining_nulls = sum(1 for row in self.data if row.get('BLOCK_ID') is None)
        if remaining_nulls > 0 and self.last_block_id is not None:
            for row in self.data:
                if row.get('BLOCK_ID') is None:
                    row['BLOCK_ID'] = self.last_block_id

        # Update last_block_id
        for row in reversed(self.data):
            if row.get('BLOCK_ID') is not None:
                self.last_block_id = row['BLOCK_ID']
                break

        # Final check - if we still have nulls, something unusual happened
        remaining_nulls = sum(1 for row in self.data if row.get('BLOCK_ID') is None)
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

        # Remove specified columns from all rows
        for row in self.data:
            for col in columns_to_drop:
                row.pop(col, None)

        print("Saving data to database...")
        try:
            self.db_manager.replace_table_data('commercial_injector_final', self.data)
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
