import sqlite3
import pandas as pd
import config
import os
import re

class CutlessFinalizer:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self.conn = None
        self.cursor = None
        print(f"CutlessFinalizer initialized with DB path: {self.db_path}")

    def _connect_db(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            print("Database connection established.")
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise

    def _close_db(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def _get_cutless_mapping(self):
        """Retrieve the mapping from virtual paths to original paths and timestamps."""
        mapping_table = 'commercial_injector_prep'
        try:
            if not self._check_table_exists(mapping_table):
                 print(f"Error: Mapping table '{mapping_table}' does not exist.")
                 return None
                 
            # Select only necessary columns
            query = f"SELECT FULL_FILE_PATH, ORIGINAL_FILE_PATH, startTime, endTime FROM {mapping_table}"
            mapping_df = pd.read_sql_query(query, self.conn)
            
            # Check if required columns exist
            required_cols = ['FULL_FILE_PATH', 'ORIGINAL_FILE_PATH', 'startTime', 'endTime']
            if not all(col in mapping_df.columns for col in required_cols):
                print(f"Error: Mapping table '{mapping_table}' is missing required columns (need {required_cols}).")
                return None
                
            print(f"Successfully loaded {len(mapping_df)} mappings from {mapping_table}.")
            # Set index for faster lookup
            mapping_df.set_index('FULL_FILE_PATH', inplace=True)
            return mapping_df
            
        except pd.io.sql.DatabaseError as e:
            print(f"Error reading mapping table '{mapping_table}': {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while getting cutless mapping: {e}")
            return None

    def _check_table_exists(self, table_name):
        """Check if a table exists in the database."""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return bool(self.cursor.fetchone())

    def _get_lineup_tables(self):
        """Get a list of all lineup table names matching the expected patterns, excluding uncut tables."""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'lineup_v%'")
        tables = [row[0] for row in self.cursor.fetchall()]
        # Filter to include only non-uncut tables that match lineup_vX or lineup_vX_cont patterns
        lineup_patterns = re.compile(r'^lineup_v\d+(_cont)?$')
        lineup_tables = [tbl for tbl in tables if lineup_patterns.match(tbl) and '_uncut' not in tbl]
        print(f"Found lineup tables: {lineup_tables}")
        return lineup_tables

    def _create_backup_table(self, table_name):
        """Create a backup of a table before modifying it, always using the current table version."""
        backup_table_name = f"{table_name}_pre_finalization"
        try:
            # Always recreate the backup table to ensure we're using the latest version of the table
            # This solves the issue where the paths in the lineup tables change between runs
            self.cursor.execute(f"DROP TABLE IF EXISTS {backup_table_name}")
            self.cursor.execute(f"CREATE TABLE {backup_table_name} AS SELECT * FROM {table_name}")
            self.conn.commit()
            print(f"Created fresh backup table: {backup_table_name}")
            return backup_table_name
        except Exception as e:
            print(f"Error creating backup table for {table_name}: {e}")
            return None
        
    def run(self):
        """Process all lineup tables to replace virtual paths with original paths and timestamps.
        Creates new tables with '_cutless' suffix instead of modifying original tables."""
        print("Starting Cutless Finalization process...")
        try:
            self._connect_db()
            
            mapping_df = self._get_cutless_mapping()
            if mapping_df is None:
                print("Aborting finalization due to missing or invalid mapping data.")
                return

            lineup_tables = self._get_lineup_tables()
            if not lineup_tables:
                print("No lineup tables found to process.")
                return

            for table_name in lineup_tables:
                print(f"Processing lineup table: {table_name}...")
                try:
                    # Define the cutless output table name
                    cutless_table_name = f"{table_name}_cutless"
                    
                    # Read data from original lineup table
                    lineup_df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
                    
                    if 'FULL_FILE_PATH' not in lineup_df.columns:
                        print(f"Skipping table {table_name}: Missing 'FULL_FILE_PATH' column.")
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
                    merged_df.to_sql(cutless_table_name, self.conn, if_exists='replace', index=False)
                    print(f"Successfully created table: {cutless_table_name}")

                except Exception as e:
                    print(f"Error processing table {table_name}: {e}")
                    # Continue to the next table

            print("Cutless Finalization process completed.")

        except Exception as e:
            print(f"An error occurred during the finalization process: {e}")
        finally:
            self._close_db()
