import pandas as pd
import sqlite3
from pandas import DataFrame
from typing import Dict

class ToonamiEncoder:
    def __init__(self):
        print("Initializing ToonamiEncoder...")
        db_path = 'toonami.db'
        self.codes: Dict[str, str] = {}
        self.conn = sqlite3.connect(db_path)

    def get_abbr(self, name, kind, index):
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
        placements = [self.get_abbr(row['PLACEMENT_' + str(i+1)], 'P', i+1) for i in range(3)]
        shows = [self.get_abbr(row['SHOW_NAME_' + str(i+1)], 'S', i+1) for i in range(3)]

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
        print("Encoding DataFrame...")
        df['Code'] = df.apply(self.create_code, axis=1)
        df['sort_ver'] = df['Code'].str.extract('V(\d+)', expand=False).fillna('9').astype(int)
        df['sort_ns'] = df['Code'].str.extract('NS(\d+)', expand=False).astype(int)
        df.sort_values(['sort_ver', 'sort_ns'], inplace=True)
        print("DataFrame encoded.")
        return df

    def save_codes_to_db(self):
        print("Saving codes to database...")
        codes_df = pd.DataFrame(list(self.codes.items()), columns=['Name', 'Code'])
        codes_df.to_sql('codes', self.conn, index=False, if_exists='replace')
        print("Codes saved.")

    def save_encoded_dataframes(self, df: DataFrame):
        print("Saving encoded DataFrames to database...")
        df.drop(['sort_ver', 'sort_ns'], axis=1).to_sql('main_data', self.conn, index=False, if_exists='replace')
        singles_df = df[df['Code'].str.contains('-NS1$')]
        multibumps_df = df[df['Code'].str.contains('-NS[2-9]$')]
        singles_df.drop(['sort_ver', 'sort_ns'], axis=1).to_sql('singles_data', self.conn, index=False, if_exists='replace')
        multibumps_df.drop(['sort_ver', 'sort_ns'], axis=1).to_sql('multibumps_v8_data', self.conn, index=False, if_exists='replace')
        
        for ver in multibumps_df['sort_ver'].unique():
            multibumps_ver_df = multibumps_df[multibumps_df['sort_ver'] == ver]
            multibumps_ver_df.drop(['sort_ver', 'sort_ns'], axis=1).to_sql(f'multibumps_v{ver}_data', self.conn, index=False, if_exists='replace')
        print("Encoded DataFrames saved.")

    def encode_and_save(self):
        print("Beginning encode_and_save operation...")
        df = pd.read_sql_query("SELECT * FROM lineup_prep_out", self.conn)
        df = self.encode_dataframe(df)
        self.save_encoded_dataframes(df)
        self.save_codes_to_db()
        print("encode_and_save operation complete.")