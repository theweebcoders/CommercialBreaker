import os
import re
import pandas as pd
import sqlite3
from itertools import cycle
import config


class UncutEncoder:
    def __init__(self, toonami_folder):
        self.file_paths = []
        self.block_ids = []
        self.bumps_df = None
        self.folder = toonami_folder
        self.intro_bump_cycle = {}
        self.generic_bump_cycle = {}
        self.default_bump_cycle = None  # Cycling default bumps
        db_path = 'toonami.db'
        self.conn = sqlite3.connect(db_path)

    def apply_show_name_mappings(self, show_name):
        show_name = config.show_name_mapping.get(show_name, show_name)
        show_name = config.show_name_mapping_2.get(show_name, show_name)
        show_name = config.show_name_mapping_3.get(show_name, show_name)
        return show_name

    def load_bumps_data(self):
        self.bumps_df = pd.read_sql('SELECT * FROM singles_data', self.conn)
        self.bumps_df['SHOW_NAME_1'] = self.bumps_df['SHOW_NAME_1'].str.lower().apply(self.apply_show_name_mappings)
        if default_bumps := self.bumps_df[
            (self.bumps_df['SHOW_NAME_1'].str.contains('clydes', case=False))
            | (self.bumps_df['SHOW_NAME_1'].str.contains('robot', case=False))
        ]['FULL_FILE_PATH'].tolist():
            self.default_bump_cycle = cycle(default_bumps)

    def find_files(self, base_dir):
        self.base_dir = base_dir
        pattern = re.compile(r"\\([^\\]+)\\Season (\d+)\\[^\\]+ - S(\d+)E(\d+)")
        for dirpath, dirnames, filenames in os.walk(self.base_dir):
            for file in filenames:
                if file.endswith(".mkv") or file.endswith(".mp4"):
                    full_path = os.path.join(dirpath, file)
                    self.file_paths.append(full_path)
                    if match := pattern.search(full_path):
                        show_name = match[1].upper().replace(' ', '_')
                        show_name = re.sub(r'[^A-Z0-9_]', '', show_name)
                        show_name = re.sub(r'_+', '_', show_name)
                        season = match[2]
                        episode = match[4]
                        self.block_ids.append(f"{show_name}_S{season.zfill(2)}E{episode.zfill(2)}")
                    else:
                        self.block_ids.append("")

    def insert_intro_bumps(self):
        for i in range(len(self.file_paths) - 1, -1, -1):
            block_id = self.block_ids[i]
            show_name = block_id.split('_S')[0].lower()
            show_name = show_name.replace('_', ' ')
            show_name = re.sub(r'[^a-z0-9\s]', '', show_name)
            show_name = re.sub(r'\s+', ' ', show_name).strip()
            show_name = self.apply_show_name_mappings(show_name)
            if intro_bumps := self.bumps_df[
                (self.bumps_df['SHOW_NAME_1'].str.lower() == show_name)
                & (self.bumps_df['PLACEMENT_2'].str.contains('Intro', case=False))
            ]['FULL_FILE_PATH'].tolist():
                if show_name not in self.intro_bump_cycle:
                    self.intro_bump_cycle[show_name] = cycle(intro_bumps)
                intro_bump = next(self.intro_bump_cycle[show_name])

            elif generic_bumps := self.bumps_df[
                (self.bumps_df['SHOW_NAME_1'].str.lower() == show_name)
                & (
                    self.bumps_df['PLACEMENT_2'].str.contains(
                        'Generic', case=False
                    )
                )
            ]['FULL_FILE_PATH'].tolist():
                if show_name not in self.generic_bump_cycle:
                    self.generic_bump_cycle[show_name] = cycle(generic_bumps)
                intro_bump = next(self.generic_bump_cycle[show_name])

            else:
                intro_bump = next(self.default_bump_cycle)

            if intro_bump:
                self.file_paths.insert(i, intro_bump)
                self.block_ids.insert(i, block_id)

    def create_table(self):
        print("Creating table in the database")
        df = pd.DataFrame(list(zip(self.file_paths, self.block_ids)), columns=['FULL_FILE_PATH', 'BLOCK_ID'])
        df.to_sql('uncut_encoded_data', self.conn, index=False, if_exists='replace')
        print("Table created in the database.")

    def run(self):
        print(f"Starting process for folder: {self.folder}")
        self.load_bumps_data()
        self.find_files(self.folder)
        self.insert_intro_bumps()
        self.create_table()
        print("Process completed.")
