import pandas as pd
from itertools import cycle
import random
import sqlite3
import config


class LineupLogic:
    def __init__(self):
        print("Initializing database connection...")
        db_path = 'toonami.db'
        self.conn = sqlite3.connect(db_path)
        print("Database connection established.")

    def generate_lineup(self):
        print("Fetching and preparing data...")
        df_parts = pd.read_sql('SELECT * FROM commercial_injector_prep', self.conn)
        df_bumps = pd.read_sql('SELECT * FROM singles_data', self.conn)
        # Create a sanitized DataFrame for comparisons
        df_bumps_sanitized = df_bumps.copy()
        df_bumps_sanitized['FULL_FILE_PATH'] = df_bumps_sanitized['FULL_FILE_PATH'].apply(lambda x: x.split('Θ')[0])

        def apply_show_name_mapping(show_name):
            show_name = config.show_name_mapping.get(show_name, show_name)
            show_name = config.show_name_mapping_2.get(show_name, show_name)
            show_name = config.how_name_mapping_3.get(show_name, show_name)
            return show_name

        df_parts['SHOW_NAME_1'] = df_parts['SHOW_NAME_1'].str.lower().apply(apply_show_name_mapping)
        df_bumps['SHOW_NAME_1'] = df_bumps['SHOW_NAME_1'].str.lower().apply(apply_show_name_mapping)
        df_bumps_sanitized['SHOW_NAME_1'] = df_bumps_sanitized['SHOW_NAME_1'].str.lower().apply(apply_show_name_mapping)

        df_parts.sort_values(by=['SHOW_NAME_1', 'Season and Episode', 'Part Number'], inplace=True)

        print("Data preparation complete.")

        rows = []

        print("Generating lineup...")

        for (show_name, season_and_episode), group in df_parts.groupby(['SHOW_NAME_1', 'Season and Episode']):
            mapped_show_name = config.how_name_mapping.get(show_name, show_name)

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

            default_bumps = list(
                df_bumps_sanitized[
                    (df_bumps_sanitized['SHOW_NAME_1'] == 'clydes')
                    | (df_bumps_sanitized['SHOW_NAME_1'] == 'robot')
                ]['FULL_FILE_PATH']
            )
            random.shuffle(default_bumps)

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

        print("Lineup generated. Proceeding to database writing.")

        df_lineup = pd.DataFrame(rows, columns=['SHOW_NAME_1', 'Season and Episode', 'FULL_FILE_PATH'])
        df_lineup.to_sql('commercial_injector', self.conn, index=False, if_exists='replace')

        print("Lineup has been written to the database.")
