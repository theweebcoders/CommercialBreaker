import pandas as pd
import os
import re
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
import config

class CutlessFinalizer:
    def __init__(self):
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        print("CutlessFinalizer initialized with DatabaseManager.")

    def _get_cutless_mapping(self):
        """Retrieve the mapping from virtual paths to original paths and timestamps."""
        mapping_table = 'commercial_injector_prep'
        try:
            if not self.db_manager.table_exists(mapping_table):
                self.error_manager.send_error_level(
                    source="CutlessFinalizer",
                    operation="_get_cutless_mapping",
                    message="Virtual cut mapping table not found",
                    details=f"Table '{mapping_table}' does not exist",
                    suggestion="This step requires Cutless Mode to have been used during commercial processing. Make sure Cutless Mode was enabled"
                )
                return None
                 
            # Select only necessary columns
            query = f"SELECT FULL_FILE_PATH, ORIGINAL_FILE_PATH, startTime, endTime FROM {mapping_table}"
            with self.db_manager.transaction() as conn:
                # First check if the table has ANY columns
                test_df = pd.read_sql_query(f"SELECT * FROM {mapping_table} LIMIT 1", conn)
                
                # Check if timestamp columns exist
                missing_columns = []
                if 'startTime' not in test_df.columns:
                    missing_columns.append('startTime')
                if 'endTime' not in test_df.columns:
                    missing_columns.append('endTime')
                    
                if missing_columns:
                    self.error_manager.send_critical(
                        source="CutlessFinalizer",
                        operation="_get_cutless_mapping",
                        message="CRITICAL: Timestamp columns missing from virtual cut table",
                        details=f"Missing columns: {', '.join(missing_columns)}. This indicates Cutless Mode may not have run correctly or the table structure is corrupted",
                        suggestion="This is a critical issue that should be reported. Please join our Discord and let us know about this error so we can investigate"
                    )
                    return None
                
                # Now read the actual data we need
                mapping_df = pd.read_sql_query(query, conn)
            
            # Check if we have any data
            if mapping_df.empty:
                self.error_manager.send_error_level(
                    source="CutlessFinalizer",
                    operation="_get_cutless_mapping",
                    message="No virtual cut data found",
                    details=f"The '{mapping_table}' table exists but is empty",
                    suggestion="No cut episodes were processed in Cutless Mode. Make sure you ran commercial processing with Cutless Mode enabled"
                )
                return None
                
            # Verify data integrity - check if timestamps are actually populated
            null_starts = mapping_df['startTime'].isna().sum()
            null_ends = mapping_df['endTime'].isna().sum()
            
            if null_starts > 0 and null_ends > 0:
                self.error_manager.send_critical(
                    source="CutlessFinalizer",
                    operation="_get_cutless_mapping",
                    message=f"Some entries missing timestamp data",
                    details=f"{null_starts} entries missing startTime, {null_ends} entries missing endTime",
                    suggestion="Some virtual cuts don't have proper timestamps. Please report this issue to us on Discord so we can investigate"
                )
                
            print(f"Successfully loaded {len(mapping_df)} mappings from {mapping_table}.")
            # Set index for faster lookup
            mapping_df.set_index('FULL_FILE_PATH', inplace=True)
            return mapping_df
            
        except Exception as e:
            self.error_manager.send_error_level(
                source="CutlessFinalizer",
                operation="_get_cutless_mapping",
                message="Failed to read virtual cut mapping data",
                details=str(e),
                suggestion="There was an error accessing the virtual cut data. Try running Prepare Content again"
            )
            return None

    def _get_lineup_tables(self):
        """Get a list of all lineup table names matching the expected patterns, excluding uncut tables."""
        try:
            tables = self.db_manager.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'lineup_v%'")
            table_names = [row["name"] for row in tables]
            # Filter to include only non-uncut tables that match lineup_vX or lineup_vX_cont patterns
            lineup_patterns = re.compile(r'^lineup_v\d+(_cont)?$')
            lineup_tables = [tbl for tbl in table_names if lineup_patterns.match(tbl) and '_uncut' not in tbl]
            
            if not lineup_tables:
                self.error_manager.send_warning(
                    source="CutlessFinalizer",
                    operation="_get_lineup_tables",
                    message="No lineup tables found to finalize",
                    details="No lineup_vX or lineup_vX_cont tables found in the database",
                    suggestion="This may be normal if you're only using uncut lineups. Cutless finalization is only needed for cut lineups"
                )
                
            print(f"Found lineup tables: {lineup_tables}")
            return lineup_tables
        except Exception as e:
            self.error_manager.send_error_level(
                source="CutlessFinalizer",
                operation="_get_lineup_tables",
                message="Failed to retrieve lineup tables",
                details=str(e),
                suggestion="There was an error accessing the database. Try running this step again"
            )
            return []

    def _create_backup_table(self, table_name):
        """Create a backup of a table before modifying it, always using the current table version."""
        backup_table_name = f"{table_name}_pre_finalization"
        try:
            # Always recreate the backup table to ensure we're using the latest version of the table
            # This solves the issue where the paths in the lineup tables change between runs
            self.db_manager.execute(f"DROP TABLE IF EXISTS {backup_table_name}")
            self.db_manager.execute(f"CREATE TABLE {backup_table_name} AS SELECT * FROM {table_name}")
            print(f"Created fresh backup table: {backup_table_name}")
            return backup_table_name
        except Exception as e:
            self.error_manager.send_warning(
                source="CutlessFinalizer",
                operation="_create_backup_table",
                message=f"Could not create backup for table {table_name}",
                details=str(e),
                suggestion="Proceeding without backup. The original table will be preserved"
            )
            return None
        
    def run(self):
        """Process all lineup tables to replace virtual paths with original paths and timestamps.
        Creates new tables with '_cutless' suffix instead of modifying original tables."""
        print("Starting Cutless Finalization process...")
        
        # Check if we're actually in cutless mode
        if not config.cutless_mode:
            self.error_manager.send_info(
                source="CutlessFinalizer",
                operation="run",
                message="Cutless Mode is not enabled",
                details="CutlessFinalizer only runs when Cutless Mode is active",
                suggestion="This step will be skipped as it's not needed for traditional cut mode"
            )
            return
            
        try:            
            mapping_df = self._get_cutless_mapping()
            if mapping_df is None:
                print("Aborting finalization due to missing or invalid mapping data.")
                return

            lineup_tables = self._get_lineup_tables()
            if not lineup_tables:
                print("No lineup tables found to process.")
                return

            successful_tables = 0
            for table_name in lineup_tables:
                print(f"Processing lineup table: {table_name}...")
                try:
                    # Define the cutless output table name
                    cutless_table_name = f"{table_name}_cutless"
                    
                    # Read data from original lineup table
                    with self.db_manager.transaction() as conn:
                        lineup_df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    
                    if 'FULL_FILE_PATH' not in lineup_df.columns:
                        self.error_manager.send_warning(
                            source="CutlessFinalizer",
                            operation="run",
                            message=f"Skipping table {table_name}",
                            details="Table missing required 'FULL_FILE_PATH' column",
                            suggestion="This table doesn't appear to be a valid lineup table"
                        )
                        continue
                        
                    # Remove any existing timestamp columns before merging to avoid conflicts
                    if 'startTime' in lineup_df.columns:
                        lineup_df.drop(columns=['startTime'], inplace=True, errors='ignore')
                    if 'endTime' in lineup_df.columns:
                        lineup_df.drop(columns=['endTime'], inplace=True, errors='ignore')
                    
                    # Merge lineup data with mapping data
                    # Use left merge to keep all lineup entries, even if mapping is missing
                    merged_df = lineup_df.merge(mapping_df, left_on='FULL_FILE_PATH', right_index=True, 
                                           how='left', suffixes=('', '_map'))

                    # Identify rows where mapping was successful (ORIGINAL_FILE_PATH is not NaN)
                    mapped_rows = merged_df['ORIGINAL_FILE_PATH'].notna()
                    print(f"Found {mapped_rows.sum()} out of {len(merged_df)} rows with mappings")

                    # Update FULL_FILE_PATH with ORIGINAL_FILE_PATH where mapping exists
                    merged_df.loc[mapped_rows, 'FULL_FILE_PATH'] = merged_df.loc[mapped_rows, 'ORIGINAL_FILE_PATH']
                    
                    # Add empty timestamp columns if they don't exist
                    if 'startTime' not in merged_df.columns: merged_df['startTime'] = None
                    if 'endTime' not in merged_df.columns: merged_df['endTime'] = None
                    
                    # We need to handle the case where mapping columns might have different names
                    if 'startTime_map' in merged_df.columns:
                        # Copy startTime from mapping where mapping exists
                        merged_df.loc[mapped_rows, 'startTime'] = merged_df.loc[mapped_rows, 'startTime_map']
                        merged_df.drop(columns=['startTime_map'], inplace=True, errors='ignore')
                        
                    if 'endTime_map' in merged_df.columns:
                        # Copy endTime from mapping where mapping exists
                        merged_df.loc[mapped_rows, 'endTime'] = merged_df.loc[mapped_rows, 'endTime_map']
                        merged_df.drop(columns=['endTime_map'], inplace=True, errors='ignore')
                    
                    # Drop the ORIGINAL_FILE_PATH column which we no longer need
                    if 'ORIGINAL_FILE_PATH' in merged_df.columns:
                        merged_df.drop(columns=['ORIGINAL_FILE_PATH'], inplace=True, errors='ignore')
                    
                    # Drop any other columns with the _map suffix that might have been created
                    map_columns = [col for col in merged_df.columns if col.endswith('_map')]
                    if map_columns:
                        print(f"Removing extra mapping columns: {map_columns}")
                        merged_df.drop(columns=map_columns, inplace=True, errors='ignore')

                    # Convert timestamp columns to appropriate type - CONVERTING TO INT
                    if 'startTime' in merged_df.columns:
                        # Convert timestamps to integers to avoid decimal issues
                        merged_df['startTime'] = merged_df['startTime'].apply(
                            lambda x: int(float(x)) if pd.notnull(x) else None
                        )
                    if 'endTime' in merged_df.columns:
                        # Convert timestamps to integers to avoid decimal issues
                        merged_df['endTime'] = merged_df['endTime'].apply(
                            lambda x: int(float(x)) if pd.notnull(x) else None
                        )

                    # Write the result to a new table with _cutless suffix
                    # Always replace if it exists
                    with self.db_manager.transaction() as conn:
                        merged_df.to_sql(cutless_table_name, conn, if_exists='replace', index=False)
                    print(f"Successfully created table: {cutless_table_name}")
                    successful_tables += 1

                except Exception as e:
                    self.error_manager.send_error_level(
                        source="CutlessFinalizer",
                        operation="run",
                        message=f"Failed to process table {table_name}",
                        details=str(e),
                        suggestion="This table will be skipped. Check if the table structure is valid"
                    )
                    # Continue to the next table

            if successful_tables == 0 and len(lineup_tables) > 0:
                self.error_manager.send_error_level(
                    source="CutlessFinalizer",
                    operation="run",
                    message="Failed to finalize any lineup tables",
                    details=f"Attempted to process {len(lineup_tables)} tables but all failed",
                    suggestion="Check that your lineup tables are properly formatted and try again"
                )
            else:
                print(f"Cutless Finalization completed. Processed {successful_tables} out of {len(lineup_tables)} tables.")

        except Exception as e:
            self.error_manager.send_critical(
                source="CutlessFinalizer",
                operation="run",
                message="Critical error during finalization",
                details=str(e),
                suggestion="The finalization process failed. Try running Prepare Content again from the beginning"
            )