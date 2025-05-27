import os
import pandas as pd
import re
import shutil
import sqlite3

import config


class MediaProcessor:
    def __init__(self, bump_folder):
        self.keywords = config.keywords
        self.bump_folder = bump_folder
        self.columns = ['ORIGINAL_FILE_PATH', 'FULL_FILE_PATH', 'TOONAMI_VERSION', 'PLACEMENT_1', 'SHOW_NAME_1', 'PLACEMENT_2', 'SHOW_NAME_2', 'PLACEMENT_3', 'SHOW_NAME_3', 'PLACEMENT_4', 'AD_VERSION', 'COLOR', 'Status']
        self.show_name_mappings_lower = None
        self.show_name_mapping = config.show_name_mapping
        self.show_name_mapping_2 = config.show_name_mapping_2  # Add this line
        self.show_name_mapping_3 = config.show_name_mapping_3  # Add this line
        self.colors = config.colors

    def generate_dynamic_regex(self, count, shows):
        # Create a dynamic part of the regex pattern that matches the show names
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
            self.regex = rf"(?i)^{config.network}\s?(?P<TOONAMI_VERSION>\d\s\d)?\s?(?P<SPECIAL_SHOW_NAME>robot|robots|clyde|clydes)(?:\s(?P<AD_VERSION>\d{{1,2}}))?$"
        return self.regex

    def _retrieve_media_files(self, directory):
        media_files = []
        for root, dirs, files in os.walk(directory):
            media_files.extend(
                (os.path.basename(file), os.path.join(root, file))
                for file in files
                if file.endswith(".mkv") or file.endswith(".mp4")
            )
        return media_files

    def _save_to_sql(self, df, table_name, conn):
        print(f"Saving data to {table_name} table...")
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        table_exists = bool(cursor.fetchone())

        if table_exists:
            # Read existing data
            existing_df = pd.read_sql(f'SELECT * FROM {table_name}', conn)
            # Append new data and drop duplicates
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            duplicates = combined_df.duplicated(keep='last')
            combined_df = combined_df[~duplicates]
            # Replace the table with updated data
            combined_df.to_sql(table_name, conn, if_exists='replace', index=False)
        else:
            # Create a new table and insert the data
            df.to_sql(table_name, conn, if_exists='replace', index=False)

        print(f"Data saved to {table_name} table.")

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
        # Sort keys by length, in descending order, to handle multi-word mappings first
        for mapping in [self.show_name_mapping, self.show_name_mapping_2, self.show_name_mapping_3]:  # Loop over mappings
            sorted_keys = sorted(mapping.keys(), key=len, reverse=True)

            # Transform to lowercase for easier matching
            transformed_bump = bump.lower()

            # Replace mapped words
            for key in sorted_keys:
                value = mapping[key]
                transformed_bump = transformed_bump.replace(key.lower(), value.lower())

            # Update bump for next mapping
            bump = transformed_bump

        # Clean the transformed bump
        transformed_bump = self._clean_show_name(transformed_bump)

        return transformed_bump

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
        return re.sub(r'[^a-zA-Z0-9\s]', '', show_name).replace('  ', ' ').strip().lower()

    def _process_data_patterns(self, media_files, shows):
        new_df = []
        no_match_df = []

        for base_name, full_path in media_files:
            cleaned_bump = os.path.splitext(base_name)[0].replace('_', ' ')
            if matched_data := self._extract_data_from_pattern(
                cleaned_bump, shows
            ):
                matched_data['ORIGINAL_FILE_PATH'] = base_name
                matched_data['FULL_FILE_PATH'] = full_path

                for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
                    if col in matched_data and pd.notna(matched_data[col]):
                        matched_data[col] = self._clean_show_name(self.show_name_mappings_lower.get(matched_data[col].lower(), matched_data[col]))

                self._set_status(matched_data, shows)

                # Explicitly set SHOW_NAME_1 for generic bumps
                if matched_data['Status'] == 'nice' and matched_data.get('SHOW_NAME_1') is None:
                    for bump in config.genric_bumps:
                        if re.search(bump, matched_data['ORIGINAL_FILE_PATH'], re.IGNORECASE):
                            matched_data['SHOW_NAME_1'] = bump
                            break

                new_df.append(matched_data)
            else:
                no_match_df.append((base_name, cleaned_bump))

        return pd.DataFrame(new_df, columns=self.columns), no_match_df

    def _set_status(self, matched_data, shows):
        # Initialize status as 'nice' by default
        status = 'nice'

        # First, handle the case for genric_bumps using the old straightforward approach
        for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
            if col in matched_data and matched_data[col] in config.genric_bumps:
                matched_data['Status'] = 'nice'
                matched_data['SHOW_NAME_1'] = matched_data[col]
                return matched_data  # Explicitly return

        # Then, handle other cases using the new method
        for col in ['SHOW_NAME_1', 'SHOW_NAME_2', 'SHOW_NAME_3']:
            if col in matched_data and pd.notna(matched_data[col]):
                cleaned_value = str(matched_data[col]).strip()
                if not cleaned_value:
                    continue

                show_name = self._clean_show_name(cleaned_value)

                if show_name not in shows:
                    status = 'naughty'
                    break

        # Assign the final status
        matched_data['Status'] = status
        return matched_data  # Explicitly return

    def run(self):
        print("Initiating database connection...")
        conn = sqlite3.connect(f'{config.network}.db')
        print("Database connection established.")

        # Initialize the show name mappings to lowercase
        all_mappings = [self.show_name_mapping, self.show_name_mapping_2, self.show_name_mapping_3]
        self.show_name_mappings_lower = {k.lower(): v.lower() for mapping in all_mappings for k, v in mapping.items()}

        print("Retrieving Toonami Shows from the database...")
        shows_df = pd.read_sql_query("SELECT * FROM Toonami_Shows", conn)
        shows = shows_df['Title'].apply(lambda x: self._clean_show_name(self.show_name_mappings_lower.get(x.lower(), x))).tolist()
        print("Toonami Shows retrieved.")

        print("Retrieving and processing media files...")
        media_files = self._retrieve_media_files(self.bump_folder)
        initially_found = len(media_files)
        print(f"Initially found {initially_found} media files.")

        processed_df, no_match_data = self._process_data_patterns(media_files, shows)
        print(f"Processed into {len(processed_df)} entries.")

        print("Making a list...")
        nice_df = processed_df[processed_df['Status'] == 'nice'].copy()
        naughty_df = processed_df[processed_df['Status'] == 'naughty']
        print("Checking it twice.")

        print("Saving processed data to SQLite tables...")
        self._save_to_sql(nice_df, "nice_list", conn)
        self._save_to_sql(naughty_df, "naughty_list", conn)
        self._save_to_sql(pd.DataFrame(no_match_data, columns=['ORIGINAL_FILE_PATH', 'CLEANED_BUMP']), "no_match", conn)
        print("Data saved to SQLite tables.")

        print("Saving additional processed files...")
        self._save_to_sql(nice_df.drop(columns=['ORIGINAL_FILE_PATH', 'Status']), "lineup_prep_out", conn)
        print("Additional files saved.")

        print("Lineup Preparation Completed Successfully.")

        conn.close()
