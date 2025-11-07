import re
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
from typing import Dict, List, Any
import config


class ToonamiEncoder:
    """
    Creates a code for each bump based on the bump's Toonami Version, placements, show names, number of shows, Ad Version, and color.
    These codes allow for efficeint library management and bump selection for lineup generation.
    """
    def __init__(self):
        """
        Creates a dictionary to store the codes and connects to the SQLite database.
        """
        print("Initializing ToonamiEncoder...")
        self.codes: Dict[str, str] = {}
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()

    def get_abbr(self, name, kind, index):
        """
        Generates an abbreviation from the first few letters of the name (one or two words). If that abbreviation already exists appends a number to differentiate. Returns a string with 'kind', 'index', and abbreviation.
        This enables the creation of unique codes for each bump.

        """
        if name is None or name == '':
            return None

        if name not in self.codes:
            name_parts = name.split()
            if len(name_parts) > 1:
                base_abbr = name_parts[0][:2].upper() + name_parts[1][0].upper()
            else:
                base_abbr = name.replace(' ', '')[:3].upper()

            abbr = base_abbr
            abbr_num = 1
            while any(val == abbr for val in self.codes.values()):
                abbr = base_abbr + str(abbr_num)
                abbr_num += 1

            self.codes[name] = abbr

        return kind + str(index) + ':' + self.codes[name]

    def create_code(self, row):
        """
        Uses the 'get_abbr' function to create a code for each bump based on the bump's Toonami Version, placements, show names, number of shows, Ad Version, and color.
        The codes are unique to each bump and allow for efficeint library management and bump selection for lineup generation.
        """
        placements = [self.get_abbr(row.get('PLACEMENT_' + str(i + 1)), 'P', i + 1) for i in range(3)]
        shows = [self.get_abbr(row.get('SHOW_NAME_' + str(i + 1)), 'S', i + 1) for i in range(3)]

        merged = []
        for i in range(len(shows)):
            if placements[i] is not None:
                merged.append(placements[i])
            if shows[i] is not None:
                merged.append(shows[i])

        num_shows = len([s for s in shows if s is not None])
        toonami_ver = row.get('TOONAMI_VERSION')
        version = 'V' + str(toonami_ver).split()[0] if toonami_ver is not None else 'V9'

        ad_ver = row.get('AD_VERSION')
        ad_version = '-AV' + str(ad_ver) if ad_ver is not None else ''

        color = row.get('COLOR')
        color_code = '-' + color[0].upper() if color is not None and len(color) > 0 else ''

        code = version + '-' + '-'.join(merged) + ad_version + color_code + '-NS' + str(num_shows)

        return code

    def encode_dataframe(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Uses regex to extract the Toonami Version and number of shows from the code. Sorts the data by Toonami Version and number of shows.
        Allows for a clear and concise way to sort the data.
        """
        print("Encoding data...")

        if len(data) == 0:
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="encode_dataframe",
                message="No bump files were found to process",
                details="Your bump folder appears to be empty or contains no valid bump files",
                suggestion="Make sure your bump folder contains Toonami bump video files and try running Prepare Content again"
            )
            raise Exception("No bump data to encode")

        # Check for required columns
        required_columns = ['PLACEMENT_1', 'SHOW_NAME_1', 'TOONAMI_VERSION']
        if data:
            first_row_keys = set(data[0].keys())
            missing_columns = [col for col in required_columns if col not in first_row_keys]
            if missing_columns:
                self.error_manager.send_error_level(
                    source="BumpEncoder",
                    operation="encode_dataframe",
                    message="Bump files are missing important information",
                    details=f"Expected data fields not found: {', '.join(missing_columns)}",
                    suggestion="Check that your bump files follow the correct naming format: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
                )
                raise Exception(f"Missing required data: {missing_columns}")

        try:
            for row in data:
                row['Code'] = self.create_code(row)
        except Exception as e:
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="encode_dataframe",
                message="Unable to process bump file information",
                details=str(e),
                suggestion="Your bump files may not follow the expected naming format. Check the naming guide: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )
            raise

        # Check if any codes were successfully generated
        if all(row.get('Code') is None for row in data):
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="encode_dataframe",
                message="None of your bump files could be processed correctly",
                details="All bump files failed to generate proper identification codes",
                suggestion="Make sure your bump files follow the expected Toonami naming format: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )
            raise Exception("No valid codes generated")

        # Warn if many codes failed to generate
        failed_codes = sum(1 for row in data if row.get('Code') is None)
        if failed_codes > 0:
            self.error_manager.send_warning(
                source="BumpEncoder",
                operation="encode_dataframe",
                message=f"{failed_codes} bump files couldn't be processed properly",
                details=f"Out of {len(data)} bump files, {failed_codes} have naming issues",
                suggestion="Some bumps will be skipped. Review your bump file naming: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )

        try:
            # Extract version and NS numbers for sorting
            for row in data:
                code = row.get('Code', '')
                if code:
                    # Extract version number (V1, V2, etc.)
                    ver_match = re.search(r'V(\d+)', code)
                    row['sort_ver'] = int(ver_match.group(1)) if ver_match else 9

                    # Extract NS number (NS1, NS2, etc.)
                    ns_match = re.search(r'NS(\d+)', code)
                    row['sort_ns'] = int(ns_match.group(1)) if ns_match else 0
                else:
                    row['sort_ver'] = 9
                    row['sort_ns'] = 0

            # Sort by version, then by number of shows
            data.sort(key=lambda x: (x['sort_ver'], x['sort_ns']))
        except Exception as e:
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="encode_dataframe",
                message="Unable to organize bump file data",
                details=str(e),
                suggestion="Something went wrong organizing your bump files. Try running Prepare Content again"
            )
            raise

        print("Data encoded.")
        return data

    def save_codes_to_db(self):
        """
        Saves the codes to the SQLite database in the 'codes' table for decoding as needed.
        Later in the program this allows for the codes to be used without having to carry over columns with bump data and then decode them.
        """
        print("Saving codes to database...")

        if not self.codes:
            self.error_manager.send_warning(
                source="BumpEncoder",
                operation="save_codes_to_db",
                message="No bump codes were generated",
                details="No identification codes are available to save",
                suggestion="This may be due to bump file naming issues. The process will continue but some features may not work properly"
            )
            return

        try:
            codes_data = [{'Name': name, 'Code': code} for name, code in self.codes.items()]
            self.db_manager.replace_table_data('codes', codes_data)
        except Exception as e:
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="save_codes_to_db",
                message="Could not save bump information",
                details=str(e),
                suggestion="There was an issue saving your bump data. Try running Prepare Content again"
            )
            raise

        print("Codes saved.")

    def save_encoded_dataframes(self, data: List[Dict[str, Any]]):
        """
        Saves separate data for the codes for singles and multibumps to the SQLite database.
        This allows for more organized and efficient data management.
        """
        print("Saving encoded data to database...")

        try:
            # Remove sort columns for saving, but keep index mapping
            data_to_save = []
            index_mapping = []  # Maps data_to_save index -> original data index
            for idx, row in enumerate(data):
                save_row = {k: v for k, v in row.items() if k not in ['sort_ver', 'sort_ns']}
                data_to_save.append(save_row)
                index_mapping.append(idx)

            # Save main data
            self.db_manager.replace_table_data('main_data', data_to_save)

            # Create singles and multibumps, keeping track of original indices
            singles_data = [row for row in data_to_save if row.get('Code') and re.search(r'-NS1$', row['Code'])]

            # For multibumps, keep (original_data_idx, row) pairs
            multibumps_with_idx = [(index_mapping[i], row) for i, row in enumerate(data_to_save)
                                   if row.get('Code') and re.search(r'-NS[2-9]$', row['Code'])]
            multibumps_data = [row for _, row in multibumps_with_idx]
            multibumps_orig_indices = [idx for idx, _ in multibumps_with_idx]

            # Check if we have any singles
            if len(singles_data) == 0:
                self.error_manager.send_warning(
                    source="BumpEncoder",
                    operation="save_encoded_dataframes",
                    message="No single-show bumps found",
                    details="Your bump collection doesn't include any single-show intro bumps",
                    suggestion="Single-show bumps are used for episode intros. Consider adding some to improve your lineup experience"
                )
            else:
                self.db_manager.replace_table_data('singles_data', singles_data)

            # Check if we have any multibumps
            if len(multibumps_data) == 0:
                self.error_manager.send_warning(
                    source="BumpEncoder",
                    operation="save_encoded_dataframes",
                    message="No multi-show bumps found",
                    details="Your bump collection doesn't include any transition bumps between shows",
                    suggestion="Multi-show bumps create smooth transitions between different anime. Consider adding some for a better viewing experience"
                )
            else:
                self.db_manager.replace_table_data('multibumps_v8_data', multibumps_data)

                # Save version-specific multibump tables
                # Get unique versions from the original data (which has sort_ver)
                unique_versions = set(row['sort_ver'] for row in data if row.get('sort_ver') is not None)

                for ver in unique_versions:
                    # Use the correct index mapping to find matching versions
                    multibumps_ver_data = [multibumps_data[i] for i in range(len(multibumps_data))
                                           if data[multibumps_orig_indices[i]]['sort_ver'] == ver]
                    if multibumps_ver_data:
                        table_name = f'multibumps_v{ver}_data'
                        self.db_manager.replace_table_data(table_name, multibumps_ver_data)

        except Exception as e:
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="save_encoded_dataframes",
                message="Could not save processed bump data",
                details=str(e),
                suggestion="There was an issue saving your processed bump files. Try running Prepare Content again"
            )
            raise

        print("Encoded data saved.")

    def encode_and_save(self):
        """
        Runs the 'encode_dataframe', 'save_codes_to_db', and 'save_encoded_dataframes' functions.
        """
        print("Beginning encode_and_save operation...")

        try:
            data = self.db_manager.fetchall_as_dicts("SELECT * FROM lineup_prep_out")
        except Exception as e:
            self.error_manager.send_critical(
                source="BumpEncoder",
                operation="encode_and_save",
                message="Cannot access your processed bump data",
                details=str(e),
                suggestion="Something went wrong with your bump file processing. Try running Prepare Content again from the beginning"
            )
            raise

        try:
            data = self.encode_dataframe(data)
            self.save_encoded_dataframes(data)
            self.save_codes_to_db()
        except Exception as e:
            # Error already logged by individual methods
            raise

        print("encode_and_save operation complete.")
