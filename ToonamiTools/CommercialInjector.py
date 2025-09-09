import pandas as pd
from itertools import cycle
import random
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
import config
from .utils import show_name_mapper


class LineupLogic:
    def __init__(self):
        print("Initializing database connection...")
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        print("Database connection established.")

    def generate_lineup(self):
        print("Fetching and preparing data...")
        
        try:
            with self.db_manager.transaction() as conn:
                df_parts = pd.read_sql('SELECT * FROM commercial_injector_prep', conn)
                df_bumps = pd.read_sql('SELECT * FROM singles_data', conn)
        except Exception as e:
            self.error_manager.send_critical(
                source="CommercialInjector",
                operation="generate_lineup",
                message="Cannot access required data",
                details=str(e),
                suggestion="Something went wrong accessing your data. Try running Prepare Content again"
            )
            raise
            
        # Check if we have any cut parts to work with
        if df_parts.empty:
            self.error_manager.send_error_level(
                source="CommercialInjector",
                operation="generate_lineup",
                message="No cut episode parts found",
                details="The commercial_injector_prep table is empty",
                suggestion="You need to run CommercialBreaker first to cut your episodes into parts"
            )
            raise Exception("No cut episode parts available")
            
        # Check if we have any bumps
        if df_bumps.empty:
            self.error_manager.send_error_level(
                source="CommercialInjector",
                operation="generate_lineup",
                message="No single-show bumps found",
                details="The singles_data table is empty - no bumps are available",
                suggestion="You need at least some single-show bumps (intro, to ads, back) for the cut lineup"
            )
            raise Exception("No bumps available for commercial injection")
            
        # Create a sanitized DataFrame for comparisons
        df_bumps_sanitized = df_bumps.copy()
        df_bumps_sanitized['FULL_FILE_PATH'] = df_bumps_sanitized['FULL_FILE_PATH'].apply(lambda x: x.split('Θ')[0])

        # Map to canonical values first
        df_parts['SHOW_NAME_1'] = df_parts['SHOW_NAME_1'].apply(lambda x: show_name_mapper.map(x, strategy='all'))
        df_bumps['SHOW_NAME_1'] = df_bumps['SHOW_NAME_1'].apply(lambda x: show_name_mapper.map(x, strategy='all'))
        df_bumps_sanitized['SHOW_NAME_1'] = df_bumps_sanitized['SHOW_NAME_1'].apply(lambda x: show_name_mapper.map(x, strategy='all'))

        # Then clean with 'matching' so ampersands/apostrophes/etc. align across sources
        df_parts['SHOW_NAME_1'] = df_parts['SHOW_NAME_1'].apply(lambda x: show_name_mapper.clean(x, mode='matching'))
        df_bumps['SHOW_NAME_1'] = df_bumps['SHOW_NAME_1'].apply(lambda x: show_name_mapper.clean(x, mode='matching'))
        df_bumps_sanitized['SHOW_NAME_1'] = df_bumps_sanitized['SHOW_NAME_1'].apply(lambda x: show_name_mapper.clean(x, mode='matching'))

        df_parts.sort_values(by=['SHOW_NAME_1', 'Season and Episode', 'Part Number'], inplace=True)

        print("Data preparation complete.")

        rows = []
        shows_without_bumps = set()
        shows_without_specific_bumps = {'to_ads': set(), 'back': set(), 'intro': set()}

        print("Generating lineup...")

        # Check for default/fallback bumps
        default_bumps = list(
            df_bumps_sanitized[
                (df_bumps_sanitized['SHOW_NAME_1'] == 'clydes')
                | (df_bumps_sanitized['SHOW_NAME_1'] == 'robot')
            ]['FULL_FILE_PATH']
        )
        
        if not default_bumps:
            self.error_manager.send_warning(
                source="CommercialInjector",
                operation="generate_lineup",
                message="No generic fallback bumps found",
                details="No 'clydes' or 'robot' bumps found to use as defaults",
                suggestion="Consider adding some generic Toonami bumps as fallbacks for shows without specific bumps"
            )

        for (show_name, season_and_episode), group in df_parts.groupby(['SHOW_NAME_1', 'Season and Episode']):
            # show_name is already mapped+cleaned; keep consistency
            mapped_show_name = show_name
            # Display name is not required for lineup logic; keep SHOW_NAME_1 only

            parts = list(group['FULL_FILE_PATH'])
            bumps = df_bumps_sanitized[df_bumps_sanitized['SHOW_NAME_1'] == mapped_show_name].sort_values('PLACEMENT_2')

            to_ads_bumps = list(
                bumps[bumps['PLACEMENT_2'].str.contains('to ads', case=False)][
                    'FULL_FILE_PATH'
                ]
            )
            back_bumps = list(
                bumps[bumps['PLACEMENT_2'].str.contains('back', case=False)][
                    'FULL_FILE_PATH'
                ]
            )
            intro_bumps = list(
                bumps[bumps['PLACEMENT_2'].str.contains('intro', case=False)][
                    'FULL_FILE_PATH'
                ]
            )
            generic_bumps = list(
                bumps[bumps['PLACEMENT_2'].str.contains('generic', case=False)][
                    'FULL_FILE_PATH'
                ]
            )

            random.shuffle(default_bumps)

            # Track which shows are missing specific bumps
            if not to_ads_bumps and not generic_bumps:
                shows_without_specific_bumps['to_ads'].add(show_name)
            if not back_bumps and not generic_bumps:
                shows_without_specific_bumps['back'].add(show_name)
            if not intro_bumps and not generic_bumps:
                shows_without_specific_bumps['intro'].add(show_name)
                
            # Check if show has NO bumps at all
            if not any([to_ads_bumps, back_bumps, intro_bumps, generic_bumps]):
                shows_without_bumps.add(show_name)
                if not default_bumps:
                    self.error_manager.send_error_level(
                        source="CommercialInjector",
                        operation="generate_lineup",
                        message=f"No bumps available for show: {show_name}",
                        details=f"'{show_name}' has no specific bumps and no fallback bumps are available",
                        suggestion="Add bumps for this show or add generic 'clydes' or 'robot' bumps to continue"
                    )
                    raise Exception(f"No bumps available for {show_name}")

            if not to_ads_bumps:
                to_ads_bumps = generic_bumps or default_bumps
            if not back_bumps:
                back_bumps = generic_bumps or default_bumps
            if not intro_bumps:
                intro_bumps = generic_bumps or default_bumps

            to_ads_bumps_cycle = cycle(to_ads_bumps) if to_ads_bumps else None
            back_bumps_cycle = cycle(back_bumps) if back_bumps else None
            intro_bumps_cycle = cycle(intro_bumps) if intro_bumps else None

            if intro_bumps_cycle:
                rows.append({'SHOW_NAME_1': show_name, 'Season and Episode': season_and_episode, 'FULL_FILE_PATH': next(intro_bumps_cycle, None)})

            for i, part in enumerate(parts):
                rows.append({'SHOW_NAME_1': show_name, 'Season and Episode': season_and_episode, 'FULL_FILE_PATH': part})
                if i != len(parts) - 1:
                    if to_ads_bumps_cycle:
                        rows.append({'SHOW_NAME_1': show_name, 'Season and Episode': season_and_episode, 'FULL_FILE_PATH': next(to_ads_bumps_cycle, None)})
                    if back_bumps_cycle:
                        rows.append({'SHOW_NAME_1': show_name, 'Season and Episode': season_and_episode, 'FULL_FILE_PATH': next(back_bumps_cycle, None)})

        # Report shows using generic/default bumps
        if shows_without_bumps:
            self.error_manager.send_info(
                source="CommercialInjector",
                operation="generate_lineup",
                message=f"{len(shows_without_bumps)} shows using only generic bumps",
                details=f"{len(shows_without_bumps)} shows have no specific bumps at all",
                suggestion="Consider adding intro, to ads, and back bumps for these shows for a better experience"
            )
            
        # Report specific missing bump types
        for bump_type, shows in shows_without_specific_bumps.items():
            if shows and len(shows) > len(df_parts['SHOW_NAME_1'].unique()) * 0.3:  # More than 30% of shows
                self.error_manager.send_info(
                    source="CommercialInjector",
                    operation="generate_lineup",
                    message=f"{len(shows)} shows missing '{bump_type}' bumps",
                    details=f"These shows are using generic or default bumps for '{bump_type}' transitions",
                    suggestion=f"Consider adding '{bump_type}' bumps for a more authentic Toonami experience"
                )

        print("Lineup generated. Proceeding to database writing.")
        
        if not rows:
            self.error_manager.send_error_level(
                source="CommercialInjector",
                operation="generate_lineup",
                message="No lineup entries generated",
                details="The lineup generation produced no entries",
                suggestion="Check that your cut episodes and bumps are properly set up"
            )
            raise Exception("Empty lineup generated")

        try:
            df_lineup = pd.DataFrame(rows, columns=['SHOW_NAME_1', 'Season and Episode', 'FULL_FILE_PATH'])
            with self.db_manager.transaction() as conn:
                df_lineup.to_sql('commercial_injector', conn, index=False, if_exists='replace')
        except Exception as e:
            self.error_manager.send_error_level(
                source="CommercialInjector",
                operation="generate_lineup",
                message="Failed to save commercial injection lineup",
                details=str(e),
                suggestion="There was an issue saving your lineup. Try running this step again"
            )
            raise

        print("Lineup has been written to the database.")
