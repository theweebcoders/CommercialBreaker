import os
import random
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
import config

class FileProcessor:
    def __init__(self, input_dir):
        self.input_dir = input_dir
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        
        # Check if input directory exists
        if not os.path.exists(input_dir):
            self.error_manager.send_error_level(
                source="ExtraBumps",
                operation="__init__",
                message=f"Input directory not found: {input_dir}",
                details="The specified directory does not exist",
                suggestion="Check that the path is correct and the directory exists"
            )
            raise FileNotFoundError(f"Directory not found: {input_dir}")
            
        # Check if we have read permissions
        if not os.access(input_dir, os.R_OK):
            self.error_manager.send_error_level(
                source="ExtraBumps",
                operation="__init__",
                message=f"Cannot read from directory: {input_dir}",
                details="Permission denied",
                suggestion="Check that you have read permissions for the selected folder"
            )
            raise PermissionError(f"No read access to: {input_dir}")
        
        # Get lineup tables
        try:
            lineup_tables = self.db_manager.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'lineup_v%'"
            )
            self.lineup_dataframes = [table["name"] for table in lineup_tables]
        except Exception as e:
            self.error_manager.send_error_level(
                source="ExtraBumps",
                operation="__init__",
                message="Cannot access database",
                details=str(e),
                suggestion="Something went wrong accessing your data. Try running Prepare Content again"
            )
            raise
            
        if not self.lineup_dataframes:
            self.error_manager.send_error_level(
                source="ExtraBumps",
                operation="__init__",
                message="No lineup tables found",
                details="No lineup_v* tables exist in the database",
                suggestion="You need to create lineups first before adding extra bumps"
            )
            raise Exception("No lineup tables found")
            
        print(f"Initialized FileProcessor with DataFrames: {self.lineup_dataframes}")

    def process_files(self):
        # Collect all files first
        full_paths = []
        for dirpath, dirnames, filenames in os.walk(self.input_dir):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                full_paths.append(full_path)
                
        if not full_paths:
            self.error_manager.send_error_level(
                source="ExtraBumps",
                operation="process_files",
                message="No files found in input directory",
                details=f"Directory '{self.input_dir}' contains no files",
                suggestion="Add bump files to the directory before running this operation"
            )
            raise Exception("No files to process")
            
        print(f"Found {len(full_paths)} files to insert as extra bumps")
        
        for lineup_name in self.lineup_dataframes:
            try:
                lineup_data = self.db_manager.fetchall_as_dicts(f"SELECT * FROM {lineup_name}")

                if len(lineup_data) == 0:
                    print(f"Skipping {lineup_name} - it's empty")
                    continue

                # Create list of bump entries with required columns
                bump_data = [
                    {"FULL_FILE_PATH": path, "Code": "", "BLOCK_ID": ""}
                    for path in full_paths
                ]

                # Shuffle the bump data
                random.shuffle(bump_data)

                print("Shuffled bump data: ")
                print(bump_data[:5])

                pos = 0
                for i in range(len(bump_data)):
                    pos += random.randint(3, 8)
                    if pos < len(lineup_data):
                        # Insert bump at position pos
                        lineup_data = lineup_data[:pos] + [bump_data[i]] + lineup_data[pos:]
                    else:
                        break

                # Create output table name with '_bonus' suffix
                output_name = lineup_name + '_bonus'

                # Write data back to the database with the new name
                self.db_manager.replace_table_data(output_name, lineup_data)

                print(f"Processed {lineup_name} and saved as {output_name}")
                
            except Exception as e:
                self.error_manager.send_warning(
                    source="ExtraBumps",
                    operation="process_files",
                    message=f"Failed to process lineup table: {lineup_name}",
                    details=str(e),
                    suggestion="This lineup will be skipped"
                )
                continue