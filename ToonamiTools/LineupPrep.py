import os
import pandas as pd
import re
import shutil
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager

import config
from .utils import show_name_mapper


class MediaProcessor:
    def __init__(self, bump_folder):
        self.keywords = config.keywords
        self.generic = config.generic_bumps
        self.bump_folder = bump_folder
        self.columns = ['ORIGINAL_FILE_PATH', 'FULL_FILE_PATH', 'TOONAMI_VERSION', 'PLACEMENT_1', 'SHOW_NAME_1', 'PLACEMENT_2', 'SHOW_NAME_2', 'PLACEMENT_3', 'SHOW_NAME_3', 'PLACEMENT_4', 'AD_VERSION', 'COLOR', 'Status']
        self.colors = config.colors
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()

    def generate_dynamic_regex(self, count, shows=None):
        # Create a dynamic part of the regex pattern that matches the show names
        if shows is None:
            # Match ANY word characters for show names (structure check only)
            dynamic_show_names = r"[\w\s!':&\-]+"
        else:
            # Match specific shows (full validation)
            dynamic_show_names = "|".join(shows)

        # Use the sorted but unescaped keywords and colors directly
        sorted_unescaped_keywords = "|".join(sorted(self.keywords, key=len, reverse=True))
        sorted_unescaped_colors = "|".join(sorted(self.colors, key=len, reverse=True))

        if count == 1:
            self.regex = rf"(?i)^{config.network}\s?(?P<TOONAMI_VERSION>\d\s\d)?\s?(?P<SHOW_NAME_1>{dynamic_show_names})\s(?P<PLACEMENT_2>{sorted_unescaped_keywords})(?:\s(?P<AD_VERSION>\d{{1,2}}))?(?:\s(?P<COLOR>{sorted_unescaped_colors}))?$"
        elif count == 2:
            self.regex = rf"(?i)^{config.network}\s?(?P<TOONAMI_VERSION>\d\s\d)?\s?(?P<SHOW_NAME_1>{dynamic_show_names})\s(?P<PLACEMENT_2>{sorted_unescaped_keywords})\s(?P<SHOW_NAME_2>{dynamic_show_names})(?:\s(?P<AD_VERSION>\d{{1,2}}))?(?:\s(?P<COLOR>{sorted_unescaped_colors}))?$"
        elif count >= 3:
            self.regex = rf"(?i)^{config.network}\s?(?P<TOONAMI_VERSION>\d\s\d)?\s?(?P<PLACEMENT_1>{sorted_unescaped_keywords})?\s?(?P<SHOW_NAME_1>{dynamic_show_names})\s(?P<PLACEMENT_2>{sorted_unescaped_keywords})\s(?P<SHOW_NAME_2>{dynamic_show_names})\s(?P<PLACEMENT_3>{sorted_unescaped_keywords})\s(?P<SHOW_NAME_3>{dynamic_show_names})(?:\s(?P<AD_VERSION>\d{{1,2}}))?(?:\s(?P<COLOR>{sorted_unescaped_colors}))?$"
        elif count == 0:
            generic_bump_names = "|".join(re.escape(name) for name in self.generic)
            self.regex = rf"(?i)^{config.network}\s?(?P<TOONAMI_VERSION>\d\s\d)?\s?(?P<SPECIAL_SHOW_NAME>{generic_bump_names})(?:\s(?P<AD_VERSION>\d{{1,2}}))?$"
        return self.regex

    def _retrieve_media_files(self, directory):
        media_files = []
        try:
            for root, dirs, files in os.walk(directory):
                media_files.extend(
                    (os.path.basename(file), os.path.join(root, file))
                    for file in files
                    if file.endswith(".mkv") or file.endswith(".mp4")
                )
        except Exception as e:
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="_retrieve_media_files",
                message="Error scanning bump folder",
                details=str(e),
                suggestion="Make sure the bump folder is accessible and try again"
            )
            raise
        return media_files

    def _save_to_sql(self, df, table_name):
        print(f"Saving data to {table_name} table...")
        
        try:
            if self.db_manager.table_exists(table_name):
                # Read existing data using pandas with the connection
                with self.db_manager.transaction() as conn:
                    existing_df = pd.read_sql(f'SELECT * FROM {table_name}', conn)
                    # Append new data and drop duplicates
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    duplicates = combined_df.duplicated(keep='last')
                    combined_df = combined_df[~duplicates]
                    # Replace the table with updated data
                    combined_df.to_sql(table_name, conn, if_exists='replace', index=False)
            else:
                # Create a new table and insert the data
                with self.db_manager.transaction() as conn:
                    df.to_sql(table_name, conn, if_exists='replace', index=False)

            print(f"Data saved to {table_name} table.")
            
        except Exception as e:
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="_save_to_sql", 
                message=f"Could not save processed bump data to {table_name}",
                details=str(e),
                suggestion="Try running this step again. If the problem persists, you may need to restart from the beginning"
            )
            raise

    def count_keywords(self, bump):
        # Convert bump to lowercase for easier matching
        lower_bump = bump.lower()

        # Define the sets of keywords
        singles = ["back", "to ads", "generic", "intro", "next"]
        from_keyword = "from"
        later_keyword = "later"

        # Define a list of keywords to exclude for 'singles'
        exclude_for_singles = ["from", "later"]

        # Check for 'singles' without 'triples', 'doubles', 'from', or 'later'
        if any(keyword in lower_bump for keyword in singles) and all(keyword not in lower_bump for keyword in exclude_for_singles):
            return 1

        # Check for 'from' without 'later'
        elif from_keyword in lower_bump and later_keyword not in lower_bump:
            return 2

        # Check for 'Later'
        elif later_keyword in lower_bump:
            return 3

        # If none of the above conditions are met, return 0
        else:
            return 0

    def _apply_show_name_mapping(self, bump):
        # Use the show_name_mapper utility
        mapped_bump = show_name_mapper.apply_via_replacement(bump)
        return mapped_bump

    def _validate_bump_structure(self, bump):
        """
        Check if bump matches the Toonami naming structure, regardless of show names.
        
        Returns:
            tuple: (matches_structure: bool, is_multi_bump: bool, keyword_count: int)
        """
        transformed_bump = self._apply_show_name_mapping(bump)
        count = self.count_keywords(transformed_bump)
        
        # Generate regex without show constraints (structure only)
        self.generate_dynamic_regex(count, shows=None)
        
        if re.match(self.regex, transformed_bump):
            # Check if it's a multi-bump based on the count
            is_multi = count >= 2  # count 2 = "from" bumps, count 3 = "later" bumps
            return True, is_multi, count
        return False, False, count

    def _extract_data_from_pattern(self, bump, shows):
        # Step 1: Apply the show_name_mapping to the bump
        transformed_bump = self._apply_show_name_mapping(bump)

        # Step 2: Count the keywords and generate the appropriate regex
        count = self.count_keywords(transformed_bump)
        self.regex = self.generate_dynamic_regex(count, shows)

        if match := re.match(self.regex, transformed_bump):
            return match.groupdict()
        else:
            return None

    def _clean_show_name(self, show_name):
        cleaned_show = show_name_mapper.clean(show_name, mode='matching')
        return cleaned_show

    def _deduplicate_missing_shows(self, missing_shows_set: set) -> set:
        if not missing_shows_set:
            return missing_shows_set

        base_to_variants: dict[str, set[str]] = {}

        for show_name_original_case in missing_shows_set:
            # Process with lowercase for consistent key generation
            show_lower = show_name_original_case.lower()
            
            # --- Key Generation (base_key) ---
            # 1. Strip colors
            current_processing_name = show_lower
            if self.colors:
                # Ensure colors are processed as whole words at the end, surrounded by optional spaces
                color_pattern = r'\s*\b(?:' + '|'.join(re.escape(c) for c in self.colors) + r')\b\s*$'
                current_processing_name = re.sub(color_pattern, '', current_processing_name, flags=re.I).strip()

            # 2. Strip trailing number (more robustly)
            #    Loop to remove multiple trailing numbers if separated by spaces, e.g., "Show 01 02"
            temp_name_for_num_strip = current_processing_name
            while True:
                parts = temp_name_for_num_strip.split(' ')
                if len(parts) > 1 and parts[-1].isdigit():
                    stripped_once = " ".join(parts[:-1]).strip()
                    if stripped_once == temp_name_for_num_strip : # No change, break
                        break
                    temp_name_for_num_strip = stripped_once
                else:
                    break # Last part is not a number or only one part left
            current_processing_name = temp_name_for_num_strip
            
            base_key = current_processing_name
            # --- End of Key Generation ---

            # Fallback for very short names (mimicking original logic's intent)
            if len(base_key) < 3 and base_key != show_lower : # if cleaning made it too short AND it actually changed
                base_key = show_lower # Revert to the original (lowercase) name if cleaning was too destructive

            if base_key not in base_to_variants:
                base_to_variants[base_key] = set()
            # Store the original casing version
            base_to_variants[base_key].add(show_name_original_case)

        # Build the final deduplicated set
        deduplicated_result = set()
        for base_name_key, variants_in_original_case in base_to_variants.items():
            if len(variants_in_original_case) == 1:
                # Only one original variant mapped to this base key, so add it.
                deduplicated_result.update(variants_in_original_case)
            else:
                # Multiple original variants mapped to this base_name_key.
                # Re-clean each variant consistently to find their "ultimate common base".
                ultimate_common_bases_for_this_bucket = set()
                for variant_original_case_item in variants_in_original_case:
                    variant_lower_item = variant_original_case_item.lower()
                    
                    # Consistent secondary cleaning:
                    # 1. Strip colors
                    cleaned_secondary = variant_lower_item
                    if self.colors:
                        color_pattern = r'\s*\b(?:' + '|'.join(re.escape(c) for c in self.colors) + r')\b\s*$'
                        cleaned_secondary = re.sub(color_pattern, '', cleaned_secondary, flags=re.I).strip()
                    
                    # 2. Strip trailing numbers (iteratively)
                    temp_secondary_num_strip = cleaned_secondary
                    while True:
                        parts_secondary = temp_secondary_num_strip.split(' ')
                        if len(parts_secondary) > 1 and parts_secondary[-1].isdigit():
                            stripped_secondary_once = " ".join(parts_secondary[:-1]).strip()
                            if stripped_secondary_once == temp_secondary_num_strip:
                                break
                            temp_secondary_num_strip = stripped_secondary_once
                        else:
                            break
                    cleaned_secondary = temp_secondary_num_strip

                    # Add the non-empty cleaned name, or the original (lowercase) if cleaning resulted in empty.
                    ultimate_common_bases_for_this_bucket.add(cleaned_secondary if cleaned_secondary else variant_lower_item)

                if len(ultimate_common_bases_for_this_bucket) == 1:
                    # All original variants in this bucket clean to the *same single ultimate base*.
                    # They are true duplicates. Pick the shortest original string among them.
                    shortest_original_variant = min(variants_in_original_case, key=len)
                    deduplicated_result.add(shortest_original_variant)
                else:
                    deduplicated_result.update(variants_in_original_case)
        
        return deduplicated_result

    
    def _analyze_all_multibumps(self, media_files, shows):
        """Analyze ALL multi-bumps to determine show coverage."""
        analysis = {
            'shows_with_complete_multibumps': set(),
            'shows_with_incomplete_multibumps': set(),
            'shows_without_multibumps': set(shows),  # Start with all shows
            'shows_referenced_not_in_library': set(),
            'multibump_details': []
        }
        
        # First pass: identify all multi-bumps and what shows they reference
        for base_name, full_path in media_files:
            cleaned_bump = os.path.splitext(base_name)[0].replace('_', ' ')
            
            # Check if it's a multi-bump
            matches_structure, is_multi_bump, keyword_count = self._validate_bump_structure(cleaned_bump)
            
            if is_multi_bump and matches_structure:
                # Apply show name mapping to the entire bump name
                transformed_bump = self._apply_show_name_mapping(cleaned_bump)
                
                # Generate regex to extract show names
                self.generate_dynamic_regex(keyword_count, shows=None)
                
                if match := re.match(self.regex, transformed_bump):
                    matched_dict = match.groupdict()
                    shows_in_bump = []
                    shows_missing = []
                    
                    # Extract each show name and normalize it
                    for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
                        if col in matched_dict and matched_dict[col]:
                            # Get the raw show name
                            raw_show = matched_dict[col].strip()
                            
                            # Skip if it looks like an episode number
                            if re.match(r'^\d+$', raw_show):
                                continue
                                
                            # Apply full normalization
                            normalized_show = show_name_mapper.map(raw_show, strategy='all')
                            # Clean the show name for matching
                            normalized_show = show_name_mapper.clean(normalized_show, mode='matching')
                            
                            # Check if show exists in library
                            if normalized_show in shows:
                                shows_in_bump.append(normalized_show)
                            else:
                                # Check if it's a partial match (e.g., "soul eater next" -> "soul eater")
                                found = False
                                for show in shows:
                                    if show in normalized_show or normalized_show in show:
                                        shows_in_bump.append(show)
                                        found = True
                                        break
                                
                                if not found:
                                    shows_missing.append(normalized_show)
                                    analysis['shows_referenced_not_in_library'].add(normalized_show)
                    
                    # Store details
                    if shows_in_bump:
                        analysis['multibump_details'].append({
                            'filename': base_name,
                            'shows_in_bump': shows_in_bump,
                            'shows_missing': shows_missing,
                            'is_complete': len(shows_missing) == 0
                        })
                        
                        # Update show categories
                        for show in shows_in_bump:
                            analysis['shows_without_multibumps'].discard(show)
                            if len(shows_missing) == 0:
                                analysis['shows_with_complete_multibumps'].add(show)
                            else:
                                analysis['shows_with_incomplete_multibumps'].add(show)
        
        # Clean up incomplete shows that also have complete bumps
        analysis['shows_with_incomplete_multibumps'] -= analysis['shows_with_complete_multibumps']

        # Deduplicate missing shows before returning
        analysis['shows_referenced_not_in_library'] = self._deduplicate_missing_shows(
            analysis['shows_referenced_not_in_library']
        )

        return analysis

    def _process_data_patterns(self, media_files, shows):
        """Process bump files and extract structured data."""
        new_df = []
        no_match_df = []
        structure_match_but_no_show = []
        
        # Tracking counters
        total_multi_bump_files = 0
        multi_bumps_matched_structure = 0
        multi_bumps_matched_shows = 0
        multi_bumps_with_keywords = 0
        
        for base_name, full_path in media_files:
            cleaned_bump = os.path.splitext(base_name)[0].replace('_', ' ')
            
            # Quick keyword check to identify potential multi-bumps
            has_multi_keywords = any(keyword in cleaned_bump.lower() for keyword in ['from', 'later', 'up next'])
            if has_multi_keywords:
                multi_bumps_with_keywords += 1
            
            # Phase 1: Check if it matches Toonami structure
            matches_structure, is_multi_bump, keyword_count = self._validate_bump_structure(cleaned_bump)
            
            if is_multi_bump:
                total_multi_bump_files += 1
                if matches_structure:
                    multi_bumps_matched_structure += 1
            
            if not matches_structure:
                # Doesn't match Toonami naming structure at all
                no_match_df.append((base_name, cleaned_bump))
                continue
            
            # Phase 2: Check if it matches with actual shows
            if matched_data := self._extract_data_from_pattern(cleaned_bump, shows):
                matched_data['ORIGINAL_FILE_PATH'] = base_name
                matched_data['FULL_FILE_PATH'] = full_path
                
                # Count multi-bumps that matched shows
                if is_multi_bump:
                    multi_bumps_matched_shows += 1

                for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
                    if col in matched_data and pd.notna(matched_data[col]):
                        # Map the show name
                        mapped_name = show_name_mapper.map(matched_data[col], strategy='all')
                        # Clean it for consistency with database shows
                        matched_data[col] = show_name_mapper.clean(mapped_name, mode='matching')

                self._set_status(matched_data, shows)

                # Explicitly set SHOW_NAME_1 for generic bumps
                if matched_data['Status'] == 'nice' and matched_data.get('SHOW_NAME_1') is None:
                    for bump in config.generic_bumps:
                        if re.search(bump, matched_data['ORIGINAL_FILE_PATH'], re.IGNORECASE):
                            matched_data['SHOW_NAME_1'] = bump
                            break

                new_df.append(matched_data)
            else:
                # Matches structure but not shows
                if is_multi_bump:
                    structure_match_but_no_show.append((base_name, cleaned_bump))

        # Store detection results for error messaging
        self.total_multi_bump_files = total_multi_bump_files
        self.multi_bumps_matched_structure = multi_bumps_matched_structure
        self.multi_bumps_matched_shows = multi_bumps_matched_shows
        self.multi_bumps_with_keywords = multi_bumps_with_keywords
        self.structure_match_but_no_show_count = len(structure_match_but_no_show)
        
        # Determine if we have multi-bumps based on successful matches
        self.has_multi_bumps = multi_bumps_matched_shows > 0
        self.has_multi_bump_files = multi_bumps_with_keywords > 0

        print(f"Multi-bump detection summary:")
        print(f"  Files with multi-bump keywords: {multi_bumps_with_keywords}")
        print(f"  Multi-bumps matching structure: {multi_bumps_matched_structure}")
        print(f"  Multi-bumps matching your shows: {multi_bumps_matched_shows}")

        return pd.DataFrame(new_df, columns=self.columns), no_match_df
    
    def _analyze_show_multibump_coverage(self, processed_df, shows):
        """
        Analyze which shows have usable multi-bumps and which don't.
        All shows are already lowercase for consistency.
        
        Returns:
            tuple: (shows_with_complete_multibumps, shows_with_incomplete_multibumps, shows_without_multibumps)
        """
        # Shows are already lowercase, no conversion needed
        shows_set = set(shows)
        
        # Track shows that appear in multi-bumps
        shows_with_complete_multibumps = set()
        shows_with_incomplete_multibumps = set()
        shows_in_any_multibump = set()
        
        # Get all multi-bumps (has SHOW_NAME_2 or SHOW_NAME_3 populated)
        multibump_df = processed_df[
            (processed_df['SHOW_NAME_2'].notna()) | 
            (processed_df['SHOW_NAME_3'].notna())
        ]
        
        print(f"\nDebug: Found {len(multibump_df)} multi-bumps in processed data")
        
        for _, row in multibump_df.iterrows():
            # Check if this multi-bump is complete (Status == 'nice')
            is_complete = row['Status'] == 'nice'
            
            # Collect all shows mentioned in this bump
            shows_in_this_bump = []
            for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
                if col in row and pd.notna(row[col]):
                    show_name = str(row[col]).lower()
                    shows_in_this_bump.append(show_name)
                    shows_in_any_multibump.add(show_name)
            
            # If complete, all shows in this bump have at least one complete multi-bump
            if is_complete:
                for show in shows_in_this_bump:
                    if show in shows_set:
                        shows_with_complete_multibumps.add(show)
            else:
                # If incomplete, mark shows that only appear in incomplete bumps
                for show in shows_in_this_bump:
                    if show in shows_set and show not in shows_with_complete_multibumps:
                        shows_with_incomplete_multibumps.add(show)
        
        # Shows not referenced in any multi-bump
        shows_without_multibumps = shows_set - shows_in_any_multibump
        
        # Remove shows from incomplete list if they also have complete bumps
        shows_with_incomplete_multibumps -= shows_with_complete_multibumps
        
        print(f"Debug: Shows in any multi-bump: {shows_in_any_multibump}")
        print(f"Debug: Shows with complete multi-bumps: {shows_with_complete_multibumps}")
        
        return shows_with_complete_multibumps, shows_with_incomplete_multibumps, shows_without_multibumps
    
    def _set_status(self, matched_data, shows):
        # Initialize status as 'nice' by default
        status = 'nice'
        
        # Shows are already lowercase, no need to convert
        shows_set = set(shows)

        # First, handle the case for generic_bumps using the old straightforward approach
        for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
            if col in matched_data and matched_data[col] in config.generic_bumps:
                matched_data['Status'] = 'nice'
                matched_data['SHOW_NAME_1'] = matched_data[col]
                return matched_data  # Explicitly return

        # Then, handle other cases using the new method
        for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
            if col in matched_data and pd.notna(matched_data[col]):
                cleaned_value = str(matched_data[col]).strip()
                if not cleaned_value:
                    continue

                # Map and convert to lowercase (show_name_mapper now returns lowercase)
                show_name = show_name_mapper.map(cleaned_value, strategy='all')
                # Clean for matching (this ensures consistency)
                show_name = show_name_mapper.clean(show_name, mode='matching')

                # Direct comparison since both are lowercase and cleaned
                if show_name not in shows_set:
                    status = 'naughty'
                    break

        # Assign the final status
        matched_data['Status'] = status
        return matched_data  # Explicitly return

    def run(self):
        # Check if bump folder exists
        if not os.path.exists(self.bump_folder):
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="run",
                message=f"Bump folder not found: {self.bump_folder}",
                details="The specified bump directory does not exist",
                suggestion="Check your bump folder path in the settings"
            )
            raise FileNotFoundError(f"Bump directory not found: {self.bump_folder}")
        
        # Check if we have read permissions
        if not os.access(self.bump_folder, os.R_OK):
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="run",
                message=f"Cannot access bump folder: {self.bump_folder}",
                details="Permission denied when trying to read the bump directory",
                suggestion="Check that the folder exists and you have permission to read it"
            )
            raise PermissionError(f"No read access to: {self.bump_folder}")

        try:
            # Check if database file still exists
            if not os.path.exists(config.DATABASE_PATH):
                self.error_manager.send_critical(
                    source="LineupPrep",
                    operation="run",
                    message="Database file is missing",
                    details=f"Cannot find database at {config.DATABASE_PATH}",
                    suggestion="The database may have been deleted or moved. You'll need to start over from the beginning"
                )
                raise Exception("Database file missing")
                
            print("Initiating database connection...")
            print("Database connection established.")
                
        except Exception as e:
            if "Database file is missing" in str(e):
                raise  # Re-raise the specific database missing error
            self.error_manager.send_critical(
                source="LineupPrep",
                operation="run",
                message="Cannot connect to database",
                details=str(e),
                suggestion="Something went wrong with the database connection. You may need to restart the application and try again"
            )
            raise

        try:
            print("Retrieving Toonami Shows from the database...")
            with self.db_manager.transaction() as conn:
                # In the run method, after retrieving shows from database:
                shows_df = pd.read_sql_query("SELECT * FROM Toonami_Shows", conn)
                
                if shows_df.empty:
                    self.error_manager.send_warning(
                        source="LineupPrep",
                        operation="run",
                        message="No Toonami shows were found in your library",
                        details="The previous step didn't find any shows that aired on Toonami",
                        suggestion="Make sure your anime files are named correctly (e.g., 'Show Name - S01E01') and try running the process again. See: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
                    )
                
                # Clean show names consistently - remove special characters
                shows = []
                for show_title in shows_df['Title'].tolist():
                    # Apply the same cleaning used everywhere else
                    cleaned_show = show_name_mapper.clean(show_title, mode='matching')
                    shows.append(cleaned_show)
                
                print("Toonami Shows retrieved.")
            

        except Exception as e:
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="run",
                message="Cannot read show information from previous step",
                details=str(e),
                suggestion="There may be an issue with your data from the previous step. Try running the process again from the beginning"
            )
            raise

        try:
            print("Retrieving and processing media files...")
            media_files = self._retrieve_media_files(self.bump_folder)
            initially_found = len(media_files)
            print(f"Initially found {initially_found} media files.")

            # Check if we found any bump files
            if initially_found == 0:
                self.error_manager.send_error_level(
                    source="LineupPrep",
                    operation="run",
                    message="No bump files found",
                    details=f"No .mkv or .mp4 files found in {self.bump_folder}",
                    suggestion="Make sure your bump folder contains Toonami bump video files"
                )
                raise Exception("No bump files found to process")
            
            processed_df, no_match_data = self._process_data_patterns(media_files, shows)
            print(f"Processed into {len(processed_df)} entries.")
            
            # NEW: Analyze all multi-bumps for coverage report
            multibump_analysis = self._analyze_all_multibumps(media_files, shows)
            
            # Print the analysis
            print("\n" + "="*60)
            print("SHOW MULTI-BUMP COVERAGE ANALYSIS")
            print("="*60)
            
            complete_shows = multibump_analysis['shows_with_complete_multibumps']
            incomplete_shows = multibump_analysis['shows_with_incomplete_multibumps']
            no_multibump_shows = multibump_analysis['shows_without_multibumps']
            
            print(f"\nShows with usable multi-bumps: {len(complete_shows)}")
            if complete_shows:
                for show in sorted(complete_shows):
                    print(f"  ✓ {show}")
            
            if incomplete_shows:
                print(f"\nShows only in incomplete multi-bumps: {len(incomplete_shows)}")
                print("(These reference shows not in your library)")
                for show in sorted(incomplete_shows):
                    print(f"  ⚠ {show}")
            
            if no_multibump_shows:
                print(f"\nShows with NO multi-bumps: {len(no_multibump_shows)}")
                for show in sorted(no_multibump_shows):
                    print(f"  ✗ {show}")
            
            # Only show truly missing shows, not episode numbers
            missing_shows = {s for s in multibump_analysis['shows_referenced_not_in_library'] 
                            if not re.match(r'^\d+$', s) and not any(show in s for show in shows)}
            
            if missing_shows:
                print(f"\nShows referenced but NOT in your library: {len(missing_shows)}")
                for show in sorted(missing_shows):
                    print(f"  ❌ {show}")
            
            print("="*60 + "\n")
            


            # SCENARIO 1: No multi-bumps at all
            if self.multi_bumps_with_keywords == 0:
                self.error_manager.send_critical(
                    source="LineupPrep",
                    operation="run",
                    message="CANNOT CONTINUE: No multi-show transition bumps found",
                    details="Your bump collection doesn't include ANY 'from', 'next', or 'later' transition bumps. The program uses multi-bumps to create your lineup.",
                    suggestion="You need multi-bumps that transition between shows (e.g., 'Toonami [Show1] from [Show2]'). See: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
                )
                raise Exception("No multi-bumps found - cannot create lineup")

            # SCENARIO 2: Have multi-bump files but none match the format
            elif self.multi_bumps_matched_structure == 0:
                self.error_manager.send_critical(
                    source="LineupPrep",
                    operation="run",
                    message="CANNOT CONTINUE: Multi-bump files don't follow Toonami format",
                    details=f"Found {self.multi_bumps_with_keywords} files with transition keywords, but none follow the required Toonami naming format.",
                    suggestion="Multi-bumps must follow this format: 'Toonami [Version] [Show1] from/next/later [Show2]'. See: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
                )
                raise Exception("No valid multi-bumps - cannot create lineup")

            # SCENARIO 3: Have valid multi-bumps but NONE match shows in library
            elif len(complete_shows) == 0:
                self.error_manager.send_critical(
                    source="LineupPrep",
                    operation="run",
                    message="CANNOT CONTINUE: No multi-bumps match your anime library",
                    details=f"Found {self.multi_bumps_matched_structure} properly formatted multi-bumps, but ALL of them reference shows not in your library.",
                    suggestion="ALL shows in a multi-bump must be in your library for it to work. Either add the missing shows or add multi-bumps that reference shows you have.",
                )
                raise Exception("No usable multi-bumps - cannot create lineup")

            # SCENARIO 4: Some shows can be used, but others can't
            if len(incomplete_shows) + len(no_multibump_shows) > 0:
                unusable_count = len(incomplete_shows) + len(no_multibump_shows)
                self.error_manager.send_warning(
                    source="LineupPrep",
                    operation="run",
                    message=f"{unusable_count} shows will be EXCLUDED from your lineup",
                    details=f"{len(no_multibump_shows)} have no multi-bumps, {len(incomplete_shows)} only appear in incomplete multi-bumps",
                    suggestion="Check the analysis in the logs for the full list. To include these shows, add multi-bumps that reference them."
                )

            # SCENARIO 5: Have unused multi-bumps (info level)
            if self.multi_bumps_matched_structure > self.multi_bumps_matched_shows:
                unused_count = self.multi_bumps_matched_structure - self.multi_bumps_matched_shows
                self.error_manager.send_info(
                    source="LineupPrep",
                    operation="run",
                    message=f"{unused_count} multi-bumps cannot be used",
                    details="These multi-bumps reference shows not in your library, but you have enough other multi-bumps to continue",
                    suggestion="This won't affect your lineup generation. Add the missing shows if you want to use these bumps."
                )

        except Exception as e:
            if "cannot create lineup" in str(e):
                raise  # Re-raise critical errors
            if "No bump files found" in str(e):
                raise  # Re-raise the specific no files error
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="_process_data_patterns",
                message="Error processing bump files",
                details=str(e),
                suggestion="Check that your bump files are accessible and not corrupted"
            )
            raise

        try:
            # Additional analysis: which shows have multi-bumps and which don't
            nice_df = processed_df[processed_df['Status'] == 'nice'].copy()
            
            # Collect all shows mentioned in multi-bumps
            shows_in_multibumps = set()
            multibump_df = nice_df[nice_df['PLACEMENT_2'].str.contains('from|next|later', case=False, na=False)]
            
            for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
                if col in multibump_df.columns:
                    show_names = multibump_df[col].dropna()
                    if len(show_names) > 0:
                        shows_in_multibumps.update(show_names.str.lower())
            
            # Find shows that will be excluded (no multi-bumps)
            shows_without_multibumps = set(s.lower() for s in shows) - shows_in_multibumps
            
            if shows_without_multibumps:
                excluded_shows_list = "\n• ".join(sorted(shows_without_multibumps))
                self.error_manager.send_warning(
                    source="LineupPrep",
                    operation="run",
                    message=f"{len(shows_without_multibumps)} shows will be EXCLUDED from your lineup",
                    details=f"These shows have no multi-bumps and cannot be used:\n• {excluded_shows_list}",
                    suggestion="To include these shows, you need multi-bumps that reference them (e.g., 'Now [Show] Next...', '[Show] From...', etc.)"
                )

        except Exception as e:
            if "No multi-bumps match your shows" in str(e):
                raise  # Re-raise the critical error
            if "No bump files found" in str(e):
                raise  # Re-raise the specific no files error
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="_process_data_patterns",
                message="Error processing bump files",
                details=str(e),
                suggestion="Check that your bump files are accessible and not corrupted"
            )
            raise

        # Check ratio of matched vs unmatched files
        matched_count = len(processed_df)
        if matched_count == 0:
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="run",
                message="No bump files matched expected naming patterns",
                details=f"Found {initially_found} files but none followed Toonami naming conventions",
                suggestion="Make sure your bump files follow the Toonami naming format (e.g., 'Toonami [Version] [Show] [Placement]'). See: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )
        elif matched_count < 10:
            self.error_manager.send_warning(
                source="LineupPrep",
                operation="run",
                message=f"Only {matched_count} bump files matched naming patterns",
                details=f"Found {initially_found} total files, but only {matched_count} were recognized",
                suggestion="Review your bump file names to make sure they follow the expected Toonami format. See: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )

        print("Making a list...")
        nice_df = processed_df[processed_df['Status'] == 'nice'].copy()
        naughty_df = processed_df[processed_df['Status'] == 'naughty']
        
        # Check for shows with no matching bumps
        nice_shows = set()
        if not nice_df.empty and 'SHOW_NAME_1' in nice_df.columns:
            show_names_1 = nice_df['SHOW_NAME_1'].dropna()
            if len(show_names_1) > 0:  # Only use .str if we have actual data
                nice_shows.update(show_names_1.str.lower())
        
        if not nice_df.empty and 'SHOW_NAME_2' in nice_df.columns:
            show_names_2 = nice_df['SHOW_NAME_2'].dropna()
            if len(show_names_2) > 0:  # Only use .str if we have actual data
                nice_shows.update(show_names_2.str.lower())
        
        if not nice_df.empty and 'SHOW_NAME_3' in nice_df.columns:
            show_names_3 = nice_df['SHOW_NAME_3'].dropna()
            if len(show_names_3) > 0:  # Only use .str if we have actual data
                nice_shows.update(show_names_3.str.lower())
                
        shows_without_bumps = set(s.lower() for s in shows) - nice_shows
        if len(shows_without_bumps) > len(shows) * 0.5:  # More than 50% of shows have no bumps
            self.error_manager.send_info(
                source="LineupPrep",
                operation="run",
                message=f"{len(shows_without_bumps)} shows don't have matching bump files",
                details=f"Out of {len(shows)} shows in your library, {len(shows_without_bumps)} don't have corresponding bumps",
                suggestion="Consider adding more bump files for these shows, or they will use generic bumps"
            )
        
        print("Checking it twice.")

        try:
            print("Saving processed data to SQLite tables...")
            self._save_to_sql(nice_df, "nice_list")
            self._save_to_sql(naughty_df, "naughty_list")
            self._save_to_sql(pd.DataFrame(no_match_data, columns=['ORIGINAL_FILE_PATH', 'CLEANED_BUMP']), "no_match")
            print("Data saved to SQLite tables.")

            print("Saving additional processed files...")
            self._save_to_sql(nice_df.drop(columns=['ORIGINAL_FILE_PATH', 'Status']), "lineup_prep_out")
            print("Additional files saved.")

        except Exception as e:
            self.error_manager.send_error_level(
                source="LineupPrep",
                operation="_save_to_sql",
                message="Failed to save bump information",
                details=str(e),
                suggestion="There may be an issue saving your data. Try running this step again"
            )
            raise

        print("Lineup Preparation Completed Successfully.")
