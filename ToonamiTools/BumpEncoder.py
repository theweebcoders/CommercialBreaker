import pandas as pd
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
from pandas import DataFrame
from typing import Dict
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
        if pd.isna(name):
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
        placements = [self.get_abbr(row['PLACEMENT_' + str(i + 1)], 'P', i + 1) for i in range(3)]
        shows = [self.get_abbr(row['SHOW_NAME_' + str(i + 1)], 'S', i + 1) for i in range(3)]

        merged = []
        for i in range(len(shows)):
            if placements[i] is not None:
                merged.append(placements[i])
            if shows[i] is not None:
                merged.append(shows[i])

        num_shows = len([s for s in shows if s is not None])
        version = 'V' + str(row['TOONAMI_VERSION']).split()[0] if pd.notna(row['TOONAMI_VERSION']) else 'V9'
        ad_version = '-AV' + str(row['AD_VERSION']) if not pd.isna(row['AD_VERSION']) else ''
        color = '-' + row['COLOR'][0].upper() if not pd.isna(row['COLOR']) else ''
        code = version + '-' + '-'.join(merged) + ad_version + color + '-NS' + str(num_shows)

        return code

    def encode_dataframe(self, df: DataFrame) -> DataFrame:
        """
        Uses regex to extract the Toonami Version and number of shows from the code. Sorts the DataFrame by Toonami Version and number of shows.
        Allows for a clear and concise way to sort the DataFrame.
        """
        print("Encoding DataFrame...")
        
        if df.empty:
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
        missing_columns = [col for col in required_columns if col not in df.columns]
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
            df['Code'] = df.apply(self.create_code, axis=1)
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
        if df['Code'].isna().all():
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="encode_dataframe",
                message="None of your bump files could be processed correctly",
                details="All bump files failed to generate proper identification codes",
                suggestion="Make sure your bump files follow the expected Toonami naming format: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )
            raise Exception("No valid codes generated")
        
        # Warn if many codes failed to generate
        failed_codes = df['Code'].isna().sum()
        if failed_codes > 0:
            self.error_manager.send_warning(
                source="BumpEncoder",
                operation="encode_dataframe",
                message=f"{failed_codes} bump files couldn't be processed properly",
                details=f"Out of {len(df)} bump files, {failed_codes} have naming issues",
                suggestion="Some bumps will be skipped. Review your bump file naming: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )
        
        try:
            df['sort_ver'] = df['Code'].str.extract(r'V(\d+)', expand=False).fillna('9').astype(int)
            df['sort_ns'] = df['Code'].str.extract(r'NS(\d+)', expand=False).astype(int)
            df.sort_values(['sort_ver', 'sort_ns'], inplace=True)
        except Exception as e:
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="encode_dataframe",
                message="Unable to organize bump file data",
                details=str(e),
                suggestion="Something went wrong organizing your bump files. Try running Prepare Content again"
            )
            raise
        
        print("DataFrame encoded.")
        return df

    def save_codes_to_db(self):
        """
        Saves the codes to the SQLite database in the 'codes' table for decoding as needed.
        Later in the program this allows for the codes to be used without having to carry over columns with bump data and then decode them to get the bump data.
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
            codes_df = pd.DataFrame(list(self.codes.items()), columns=['Name', 'Code'])
            with self.db_manager.transaction() as conn:
                codes_df.to_sql('codes', conn, index=False, if_exists='replace')
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

    def save_encoded_dataframes(self, df: DataFrame):
        """
        Saves separate DataFrames for the codes for singles and multibumps to the SQLite database.
        This allows for more organized and efficient data management.
        """
        print("Saving encoded DataFrames to database...")
        
        try:
            with self.db_manager.transaction() as conn:
                # Save main data
                df.drop(['sort_ver', 'sort_ns'], axis=1).to_sql('main_data', conn, index=False, if_exists='replace')
                
                # Create singles and multibumps
                singles_df = df[df['Code'].str.contains('-NS1$', na=False)]
                multibumps_df = df[df['Code'].str.contains('-NS[2-9]$', na=False)]
                
                # Check if we have any singles
                if singles_df.empty:
                    self.error_manager.send_warning(
                        source="BumpEncoder",
                        operation="save_encoded_dataframes",
                        message="No single-show bumps found",
                        details="Your bump collection doesn't include any single-show intro bumps",
                        suggestion="Single-show bumps are used for episode intros. Consider adding some to improve your lineup experience"
                    )
                else:
                    singles_df.drop(['sort_ver', 'sort_ns'], axis=1).to_sql('singles_data', conn, index=False, if_exists='replace')
                
                # Check if we have any multibumps
                if multibumps_df.empty:
                    self.error_manager.send_warning(
                        source="BumpEncoder",
                        operation="save_encoded_dataframes",
                        message="No multi-show bumps found",
                        details="Your bump collection doesn't include any transition bumps between shows",
                        suggestion="Multi-show bumps create smooth transitions between different anime. Consider adding some for a better viewing experience"
                    )
                else:
                    multibumps_df.drop(['sort_ver', 'sort_ns'], axis=1).to_sql('multibumps_v8_data', conn, index=False, if_exists='replace')

                    # Save version-specific multibump tables
                    for ver in multibumps_df['sort_ver'].unique():
                        multibumps_ver_df = multibumps_df[multibumps_df['sort_ver'] == ver]
                        multibumps_ver_df.drop(['sort_ver', 'sort_ns'], axis=1).to_sql(f'multibumps_v{ver}_data', conn, index=False, if_exists='replace')
                        
        except Exception as e:
            self.error_manager.send_error_level(
                source="BumpEncoder",
                operation="save_encoded_dataframes",
                message="Could not save processed bump data",
                details=str(e),
                suggestion="There was an issue saving your processed bump files. Try running Prepare Content again"
            )
            raise
        
        print("Encoded DataFrames saved.")

    def encode_and_save(self):
        """
        Runs the 'encode_dataframe', 'save_codes_to_db', and 'save_encoded_dataframes' functions.
        """
        print("Beginning encode_and_save operation...")
        
        try:
            with self.db_manager.transaction() as conn:
                df = pd.read_sql_query("SELECT * FROM lineup_prep_out", conn)
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
            df = self.encode_dataframe(df)
            self.save_encoded_dataframes(df)
            self.save_codes_to_db()
        except Exception as e:
            # Error already logged by individual methods
            raise
        
        print("encode_and_save operation complete.")