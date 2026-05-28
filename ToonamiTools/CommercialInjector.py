from collections import defaultdict
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
            parts_data = self.db_manager.fetchall_as_dicts('SELECT * FROM commercial_injector_prep')
            bumps_data = self.db_manager.fetchall_as_dicts('SELECT * FROM singles_data')
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
        if len(parts_data) == 0:
            self.error_manager.send_error_level(
                source="CommercialInjector",
                operation="generate_lineup",
                message="No cut episode parts found",
                details="The commercial_injector_prep table is empty",
                suggestion="You need to run CommercialBreaker first to cut your episodes into parts"
            )
            raise Exception("No cut episode parts available")

        # Check if we have any bumps
        if len(bumps_data) == 0:
            self.error_manager.send_error_level(
                source="CommercialInjector",
                operation="generate_lineup",
                message="No single-show bumps found",
                details="The singles_data table is empty - no bumps are available",
                suggestion="You need at least some single-show bumps (intro, to ads, back) for the cut lineup"
            )
            raise Exception("No bumps available for commercial injection")

        # Create sanitized bumps data for comparisons (split on Θ)
        bumps_data_sanitized = [
            {**row, 'FULL_FILE_PATH': row['FULL_FILE_PATH'].split('Θ')[0]}
            for row in bumps_data
        ]

        # Map to canonical values first
        for row in parts_data:
            row['SHOW_NAME_1'] = show_name_mapper.map(row['SHOW_NAME_1'], strategy='all')
        for row in bumps_data:
            row['SHOW_NAME_1'] = show_name_mapper.map(row['SHOW_NAME_1'], strategy='all')
        for row in bumps_data_sanitized:
            row['SHOW_NAME_1'] = show_name_mapper.map(row['SHOW_NAME_1'], strategy='all')

        # Then clean with 'matching' so ampersands/apostrophes/etc. align across sources
        for row in parts_data:
            row['SHOW_NAME_1'] = show_name_mapper.clean(row['SHOW_NAME_1'], mode='matching')
        for row in bumps_data:
            row['SHOW_NAME_1'] = show_name_mapper.clean(row['SHOW_NAME_1'], mode='matching')
        for row in bumps_data_sanitized:
            row['SHOW_NAME_1'] = show_name_mapper.clean(row['SHOW_NAME_1'], mode='matching')

        # Sort parts by show name, season/episode, and part number
        parts_data.sort(key=lambda x: (x['SHOW_NAME_1'], x['Season and Episode'], x['Part Number']))

        print("Data preparation complete.")

        rows = []
        shows_without_bumps = set()
        shows_without_specific_bumps = {'to_ads': set(), 'back': set(), 'intro': set()}

        print("Generating lineup...")

        # Check for default/fallback bumps
        default_bumps = [
            row['FULL_FILE_PATH'] for row in bumps_data_sanitized
            if row['SHOW_NAME_1'] == 'clydes' or row['SHOW_NAME_1'] == 'robot'
        ]

        if not default_bumps:
            self.error_manager.send_warning(
                source="CommercialInjector",
                operation="generate_lineup",
                message="No generic fallback bumps found",
                details="No 'clydes' or 'robot' bumps found to use as defaults",
                suggestion="Consider adding some generic Toonami bumps as fallbacks for shows without specific bumps"
            )

        # Group parts by show and episode
        grouped_parts = defaultdict(list)
        for row in parts_data:
            key = (row['SHOW_NAME_1'], row['Season and Episode'])
            grouped_parts[key].append(row)

        for (show_name, season_and_episode), group in grouped_parts.items():
            # show_name is already mapped+cleaned; keep consistency
            mapped_show_name = show_name
            # Display name is not required for lineup logic; keep SHOW_NAME_1 only

            parts = [row['FULL_FILE_PATH'] for row in group]

            # Filter bumps for this show and sort by PLACEMENT_2
            bumps = [row for row in bumps_data_sanitized if row['SHOW_NAME_1'] == mapped_show_name]
            bumps.sort(key=lambda x: x.get('PLACEMENT_2', ''))

            to_ads_bumps = [
                row['FULL_FILE_PATH'] for row in bumps
                if row.get('PLACEMENT_2') and 'to ads' in row['PLACEMENT_2'].lower()
            ]
            back_bumps = [
                row['FULL_FILE_PATH'] for row in bumps
                if row.get('PLACEMENT_2') and 'back' in row['PLACEMENT_2'].lower()
            ]
            intro_bumps = [
                row['FULL_FILE_PATH'] for row in bumps
                if row.get('PLACEMENT_2') and 'intro' in row['PLACEMENT_2'].lower()
            ]
            generic_bumps = [
                row['FULL_FILE_PATH'] for row in bumps
                if row.get('PLACEMENT_2') and 'generic' in row['PLACEMENT_2'].lower()
            ]

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
        unique_shows = set(row['SHOW_NAME_1'] for row in parts_data)
        for bump_type, shows in shows_without_specific_bumps.items():
            if shows and len(shows) > len(unique_shows) * 0.3:  # More than 30% of shows
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
            self.db_manager.replace_table_data('commercial_injector', rows)
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
