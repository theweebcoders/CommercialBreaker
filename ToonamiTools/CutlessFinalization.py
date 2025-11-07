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
                 
            # Check if duration column exists and select appropriate columns
            with self.db_manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({mapping_table})")
                columns_info = cursor.fetchall()
                column_names = [col[1] for col in columns_info]

                # Base columns we always need
                select_columns = "FULL_FILE_PATH, ORIGINAL_FILE_PATH, startTime, endTime"

                # Add duration if it exists (cutless mode)
                if 'duration' in column_names:
                    select_columns += ", duration"
                    print("Duration column found in commercial_injector_prep - including in cutless finalization")
                else:
                    print("Duration column not found in commercial_injector_prep - proceeding without duration")

            query = f"SELECT {select_columns} FROM {mapping_table}"
            with self.db_manager.transaction() as conn:
                # First check if the table has ANY columns
                cursor = conn.execute(f"SELECT * FROM {mapping_table} LIMIT 1")
                test_columns = [desc[0] for desc in cursor.description]

                # Check if timestamp columns exist
                missing_columns = []
                if 'startTime' not in test_columns:
                    missing_columns.append('startTime')
                if 'endTime' not in test_columns:
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
                cursor = conn.execute(query)
                columns = [desc[0] for desc in cursor.description]
                mapping_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # Check if we have any data
            if len(mapping_data) == 0:
                self.error_manager.send_error_level(
                    source="CutlessFinalizer",
                    operation="_get_cutless_mapping",
                    message="No virtual cut data found",
                    details=f"The '{mapping_table}' table exists but is empty",
                    suggestion="No cut episodes were processed in Cutless Mode. Make sure you ran commercial processing with Cutless Mode enabled"
                )
                return None
                
            # Verify data integrity - check if timestamps are populated for anime files only
            # Bumps are identified by containing network name or keywords from config
            network_name = config.network.lower()
            keywords = [kw.lower() for kw in config.keywords]
            
            def is_bump_file(file_path):
                """Check if a file path represents a bump (contains network name or keywords)"""
                file_path_lower = str(file_path).lower()
                
                # Check for network name
                if network_name in file_path_lower:
                    return True
                
                # Check for any keywords
                for keyword in keywords:
                    if keyword in file_path_lower:
                        return True
                
                return False
            
            # Separate anime files from bump files
            anime_files = [row for row in mapping_data if not is_bump_file(row['FULL_FILE_PATH'])]
            bump_files = [row for row in mapping_data if is_bump_file(row['FULL_FILE_PATH'])]

            if len(anime_files) > 0:
                # Only flag critical error if anime files have BOTH startTime AND endTime null
                anime_missing_both = [
                    row for row in anime_files
                    if row.get('startTime') is None and row.get('endTime') is None
                ]

                if len(anime_missing_both) > 0:
                    self.error_manager.send_critical(
                        source="CutlessFinalizer",
                        operation="_get_cutless_mapping",
                        message=f"Anime files missing timestamp data",
                        details=f"{len(anime_missing_both)} anime files have no timestamp data (both startTime and endTime are null) out of {len(anime_files)} total anime files",
                        suggestion="Anime files need timestamps for cutless mode. This indicates commercial detection may have failed"
                    )

            # Log summary of what was found
            print(f"Successfully loaded {len(mapping_data)} mappings from {mapping_table} ({len(anime_files)} anime files, {len(bump_files)} bump files).")
            # Convert to dict indexed by FULL_FILE_PATH for faster lookup
            mapping_dict = {row['FULL_FILE_PATH']: row for row in mapping_data}
            return mapping_dict
            
        except Exception as e:
            self.error_manager.send_error_level(
                source="CutlessFinalizer",
                operation="_get_cutless_mapping",
                message="Failed to read virtual cut mapping data",
                details=str(e),
                suggestion="There was an error accessing the virtual cut data. Try running Prepare Content again"
            )
            return None

    def _get_bump_durations(self):
        """Load pre-calculated bump durations for merging into lineup tables."""
        table_name = 'bump_durations'

        if not self.db_manager.table_exists(table_name):
            self.error_manager.send_info(
                source="CutlessFinalizer",
                operation="_get_bump_durations",
                message="Bump duration table not found",
                details="Table 'bump_durations' does not exist",
                suggestion="Run Prepare Toonami Channel to calculate bump durations before finalizing"
            )
            return {}

        try:
            with self.db_manager.transaction() as conn:
                cursor = conn.execute(f"SELECT FULL_FILE_PATH, duration FROM {table_name}")
                columns = [desc[0] for desc in cursor.description]
                bump_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            self.error_manager.send_warning(
                source="CutlessFinalizer",
                operation="_get_bump_durations",
                message="Failed to load bump durations",
                details=str(e),
                suggestion="Check database integrity and rerun bump calculation if necessary"
            )
            return {}

        if len(bump_data) == 0:
            self.error_manager.send_info(
                source="CutlessFinalizer",
                operation="_get_bump_durations",
                message="Bump duration table is empty",
                details="No rows found in 'bump_durations'",
                suggestion="Recalculate bump durations if lineup entries still need timing information"
            )
            return {}

        # Clean and filter data
        cleaned_data = []
        for row in bump_data:
            # Strip and validate FULL_FILE_PATH
            file_path = str(row.get('FULL_FILE_PATH', '')).strip()
            if not file_path:
                continue

            # Convert duration to numeric
            try:
                duration = float(row.get('duration'))
            except (ValueError, TypeError):
                continue

            cleaned_data.append({'FULL_FILE_PATH': file_path, 'duration': duration})

        if len(cleaned_data) == 0:
            return {}

        # Remove duplicates (keep last occurrence)
        seen = {}
        for row in cleaned_data:
            seen[row['FULL_FILE_PATH']] = row['duration']

        # Return as dict indexed by FULL_FILE_PATH
        return seen

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

    def _validate_durations(self, data, table_name):
        """Ensure all lineup rows contain duration data before writing output."""
        # Check if duration column exists in any row
        has_duration_column = any('duration' in row for row in data)
        if not has_duration_column:
            self.error_manager.send_error_level(
                source="CutlessFinalizer",
                operation="run",
                message="Finalized table missing duration column",
                details=f"Table '{table_name}' does not contain a duration column after merging",
                suggestion="Verify mapping data includes durations for anime files and rerun Prepare Cut Anime"
            )
            return False

        # Find rows with missing duration
        rows_with_missing_duration = [
            row for row in data
            if row.get('duration') is None or str(row.get('duration', '')).strip() == ''
        ]

        if len(rows_with_missing_duration) == 0:
            return True

        network_token = str(getattr(config, 'network', '')).strip().lower()

        # Separate bump and anime files
        bump_missing = []
        anime_missing = []
        for row in rows_with_missing_duration:
            file_path_lower = str(row.get('FULL_FILE_PATH', '')).lower()
            if network_token and network_token in file_path_lower:
                bump_missing.append(row)
            else:
                anime_missing.append(row)

        if len(bump_missing) > 0:
            sample = ', '.join([row['FULL_FILE_PATH'] for row in bump_missing[:5]])
            details = f"Example bump rows missing duration: {sample}" if sample else ""
            self.error_manager.send_error_level(
                source="CutlessFinalizer",
                operation="run",
                message="Bump durations missing after finalization",
                details=details,
                suggestion="Run Prepare Cut Anime again after ensuring the Bump Calculator completed successfully"
            )

        if len(anime_missing) > 0:
            sample = ', '.join([row['FULL_FILE_PATH'] for row in anime_missing[:5]])
            details = f"Example anime rows missing duration: {sample}" if sample else ""
            self.error_manager.send_error_level(
                source="CutlessFinalizer",
                operation="run",
                message="Anime durations missing after finalization",
                details=details,
                suggestion="Verify commercial mapping includes duration values and rerun Prepare Cut Anime"
            )

        return False

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
            mapping_dict = self._get_cutless_mapping()
            if mapping_dict is None:
                print("Aborting finalization due to missing or invalid mapping data.")
                return

            bump_duration_dict = self._get_bump_durations()
            if len(bump_duration_dict) == 0:
                self.error_manager.send_error_level(
                    source="CutlessFinalizer",
                    operation="run",
                    message="Bump durations unavailable",
                    details="The bump_durations table is missing or empty",
                    suggestion="Run Prepare Cut Anime to populate bump durations before finalizing"
                )
                print("Aborting finalization because bump durations were not found.")
                return

            # bump_duration_dict is already keyed by FULL_FILE_PATH with duration values

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
                        cursor = conn.execute(f"SELECT * FROM {table_name}")
                        columns = [desc[0] for desc in cursor.description]
                        lineup_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

                    # Check if FULL_FILE_PATH column exists
                    if len(lineup_data) > 0 and 'FULL_FILE_PATH' not in lineup_data[0]:
                        self.error_manager.send_warning(
                            source="CutlessFinalizer",
                            operation="run",
                            message=f"Skipping table {table_name}",
                            details="Table missing required 'FULL_FILE_PATH' column",
                            suggestion="This table doesn't appear to be a valid lineup table"
                        )
                        continue

                    # Remove any existing timestamp and duration columns before merging to avoid conflicts
                    for row in lineup_data:
                        row.pop('startTime', None)
                        row.pop('endTime', None)
                        row.pop('duration', None)

                    # Manual left join: merge lineup data with mapping data
                    # Keep all lineup entries, even if mapping is missing
                    mapped_count = 0
                    has_duration_in_mapping = any('duration' in mapping_dict.get(k, {}) for k in mapping_dict)

                    for row in lineup_data:
                        file_path = row.get('FULL_FILE_PATH')

                        # Look up mapping data
                        mapping_row = mapping_dict.get(file_path)
                        if mapping_row:
                            mapped_count += 1
                            # Add mapping data (ORIGINAL_FILE_PATH, startTime, endTime, duration if present)
                            row['ORIGINAL_FILE_PATH'] = mapping_row.get('ORIGINAL_FILE_PATH')
                            row['startTime'] = mapping_row.get('startTime')
                            row['endTime'] = mapping_row.get('endTime')
                            if 'duration' in mapping_row:
                                row['duration'] = mapping_row.get('duration')
                        else:
                            row['ORIGINAL_FILE_PATH'] = None
                            row['startTime'] = None
                            row['endTime'] = None
                            if has_duration_in_mapping:
                                row['duration'] = None

                        # Look up bump duration
                        bump_duration = bump_duration_dict.get(file_path)
                        if bump_duration is not None:
                            # Fill duration if not already set
                            if row.get('duration') is None:
                                row['duration'] = bump_duration

                    print(f"Found {mapped_count} out of {len(lineup_data)} rows with mappings")

                    # Update FULL_FILE_PATH with ORIGINAL_FILE_PATH where mapping exists
                    for row in lineup_data:
                        if row.get('ORIGINAL_FILE_PATH') is not None:
                            row['FULL_FILE_PATH'] = row['ORIGINAL_FILE_PATH']

                    # Drop the ORIGINAL_FILE_PATH column which we no longer need
                    for row in lineup_data:
                        row.pop('ORIGINAL_FILE_PATH', None)

                    # Validate durations
                    if not self._validate_durations(lineup_data, cutless_table_name):
                        print(f"Skipping table {table_name} due to missing durations.")
                        continue

                    # Convert timestamp columns to integers
                    for row in lineup_data:
                        for col in ['startTime', 'endTime', 'duration']:
                            if col in row and row[col] is not None:
                                try:
                                    row[col] = int(float(row[col]))
                                except (ValueError, TypeError):
                                    row[col] = None

                    # Warn if any lineup entries still lack duration after processing
                    missing_duration_count = sum(1 for row in lineup_data if row.get('duration') is None)
                    if missing_duration_count > 0:
                        self.error_manager.send_warning(
                            source="CutlessFinalizer",
                            operation="run",
                            message=f"{missing_duration_count} lineup entries missing duration after finalization",
                            details=f"Table '{cutless_table_name}' still has rows without duration",
                            suggestion="Confirm mapping data includes durations or update assets manually"
                        )

                    # Write the result to a new table with _cutless suffix
                    with self.db_manager.transaction() as conn:
                        conn.execute(f"DROP TABLE IF EXISTS {cutless_table_name}")

                        if lineup_data:
                            # Preserve original column order, append new columns at the end
                            all_columns = list(columns)  # Start with original order from SELECT
                            for row in lineup_data:
                                for col in row.keys():
                                    if col not in all_columns:
                                        all_columns.append(col)  # Add new columns at end

                            column_names = ','.join([f'"{col}"' for col in all_columns])
                            placeholders = ','.join(['?' for _ in all_columns])
                            conn.execute(f"CREATE TABLE {cutless_table_name} ({column_names})")
                            conn.executemany(
                                f"INSERT INTO {cutless_table_name} VALUES ({placeholders})",
                                [tuple(row.get(col) for col in all_columns) for row in lineup_data]
                            )

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
