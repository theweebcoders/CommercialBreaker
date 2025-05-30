import os
import sqlite3
import pandas as pd
import numpy as np
import config

class FileProcessor:
    def __init__(self, input_dir):
        self.input_dir = input_dir
        db_path = config.DATABASE_PATH
        self.conn = sqlite3.connect(db_path)
        self.lineup_dataframes = [name[0] for name in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'lineup_v%'")]
        print(f"Initialized FileProcessor with DataFrames: {self.lineup_dataframes}")

    def process_files(self):
        for lineup_name in self.lineup_dataframes:
            df_input = pd.read_sql(f"SELECT * FROM {lineup_name}", self.conn)

            full_paths = []
            for dirpath, dirnames, filenames in os.walk(self.input_dir):
                for filename in filenames:
                    full_path = os.path.join(dirpath, filename)
                    full_paths.append(full_path)

            df = pd.DataFrame(full_paths, columns=["FULL_FILE_PATH"])
            df["Code"] = ""
            df["BLOCK_ID"] = ""
            df = df.sample(frac=1).reset_index(drop=True)

            print("Shuffled DataFrame: ")
            print(df.head())

            pos = 0
            for i in range(len(df)):
                pos += np.random.randint(3, 8)
                if pos < len(df_input):
                    df_input = pd.concat([df_input.iloc[:pos], df.iloc[i:i + 1], df_input.iloc[pos:]]).reset_index(drop=True)
                else:
                    break

            # Create output DataFrame name with '_bonus' suffix
            output_name = lineup_name + '_bonus'

            # Write DataFrame back to the database with the new name
            df_input.to_sql(output_name, self.conn, if_exists='replace', index=False)

            print(f"Processed {lineup_name} and saved as {output_name}")
