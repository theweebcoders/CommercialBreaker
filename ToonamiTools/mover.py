import os
import shutil
import pathlib
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import sqlite3


class FileMover:
    def __init__(self, destination, fake_move=False):
        self.db_path = 'toonami.db'
        self.destination = destination
        self.fake_move = fake_move
        self.input_dir = ''

    def move_files(self):
        # Connect to the SQLite database and read the DataFrame
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql('SELECT * FROM Toonami_Episodes', conn)
        conn.close()

        # Define a helper function to get the root directory
        def get_root_dir(path):
            parts = pathlib.Path(path).parts
            # Find the "Anime" directory dynamically, instead of hardcoding the structure
            anime_index = parts.index('Anime') if 'Anime' in parts else None
            if anime_index is None:
                raise ValueError('Anime directory not found in path')
            return os.path.join(*parts[:anime_index + 1])

        # Apply the helper function to each file path to get the corresponding root directory
        root_dirs = df['File Path'].apply(get_root_dir)

        # Determine the most common root directory
        root_dir = root_dirs.mode()[0]
        if not root_dir:
            raise ValueError('Unable to identify root directory')

        if self.fake_move:
            for file_path in df['File Path']:
                # Preserve file structure
                relative_path = os.path.relpath(file_path, root_dir)
                new_path = os.path.join(self.destination, relative_path)
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                open(new_path, 'a').close()  # Create an empty file
        else:
            try:
                # Use a ThreadPoolExecutor to run each file move in a separate thread
                with ThreadPoolExecutor(max_workers=5) as executor:
                    # Create a list of futures
                    futures = []
                    for index, row in df.iterrows():
                        file_path = row['File Path']
                        # Preserve file structure
                        relative_path = os.path.relpath(file_path, root_dir)
                        new_path = os.path.join(self.destination, relative_path)

                        os.makedirs(os.path.dirname(new_path), exist_ok=True)
                        # Submit the move operation to the executor
                        futures.append(executor.submit(shutil.move, file_path, new_path))

                    # Wait for all futures to complete before continuing
                    for future in futures:
                        future.result()

            except Exception as e:  # Replace 'Exception' with more specific exception types if needed
                print(f"File move failed due to: {e}")
                print("Continuing anyway")

        self.input_dir = root_dir

    def remove_empty_dirs(self, path):
        for dirpath, dirnames, filenames in os.walk(path, topdown=False):
            if dirpath == path:  # Don't remove root directory
                continue

            if not os.listdir(dirpath):
                os.rmdir(dirpath)

    def cleanup(self):
        self.remove_empty_dirs(self.input_dir)
        print("removed empty directories")

    def run(self):
        print("Starting the file moving process")
        self.move_files()
        self.cleanup()
        print("File moving process completed")