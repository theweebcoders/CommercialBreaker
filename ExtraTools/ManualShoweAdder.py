import os
import re
import pandas as pd
import random
import sqlite3
from functools import cmp_to_key
import tkinter as tk
from tkinter import filedialog


class AnimeShowCompilerGUI:
    def __init__(self, processor):
        self.processor = processor
        self.root = tk.Tk()
        self.root.title("Add Show Prepper")
        self.create_widgets()

    def create_widgets(self):
        self._create_file_selection("Select Intro Bumps:", "intro_label")
        self._create_file_selection("Select To Ads Bumps:", "to_ads_label")
        self._create_file_selection("Select Back Bumps:", "back_label")
        self._create_file_selection("Select Generic Bumps (Optional):", "generic_label")
        self._create_folder_selection("Select Show Folder:", "show_folder_label")
        tk.Button(self.root, text="Execute", command=self.execute).pack()

    def _create_file_selection(self, text, label_name):
        frame = tk.Frame(self.root)
        frame.pack(fill="both")
        tk.Label(frame, text=text).pack(side="left")
        label = tk.Label(frame, text="")
        label.pack(side="left")
        tk.Button(frame, text="Browse", command=lambda: self.select_files(label)).pack(side="right")
        setattr(self, label_name, label)

    def _create_folder_selection(self, text, label_name):
        frame = tk.Frame(self.root)
        frame.pack(fill="both")
        tk.Label(frame, text=text).pack(side="left")
        label = tk.Label(frame, text="")
        label.pack(side="left")
        tk.Button(frame, text="Browse", command=lambda: self.select_folder(label)).pack(side="right")
        setattr(self, label_name, label)

    def select_files(self, label):
        files = filedialog.askopenfilenames()
        label.config(text=str(files))

    def select_folder(self, label):
        folder = filedialog.askdirectory()
        label.config(text=folder)

    def execute(self):
        # Passing the selected paths to the processor class
        self.processor.process(
            intros=self.intro_label.cget("text"),
            to_ads=self.to_ads_label.cget("text"),
            backs=self.back_label.cget("text"),
            generics=self.generic_label.cget("text"),
            show_folder=self.show_folder_label.cget("text"),
        )

    def run(self):
        self.root.mainloop()


class AnimeShowProcessor:
    def process(self, intros, to_ads, backs, generics, show_folder):
        # Correcting the formatting of the selected paths by concatenating and splitting
        intros = [path.strip("'") for path in intros[2:-2].split("', '")]
        to_ads = [path.strip("'") for path in to_ads[2:-2].split("', '")]
        backs = [path.strip("'") for path in backs[2:-2].split("', '")]
        generics = [path.strip("'") for path in generics[2:-2].split("', '")] if generics else []
        db = sqlite3.connect("toonami.db")
        print(f"Intros: {intros}")
        print(f"To Ads: {to_ads}")
        print(f"Backs: {backs}")
        print(f"Generics: {generics}")
        print(f"Show Folder: {show_folder}")

        # Prepare DataFrame to store results
        result_df = pd.DataFrame(columns=["FULL_FILE_PATH", "BLOCK_ID"])

        # Custom comparison function for sorting
        def compare(file1, file2):
            season1, episode1 = map(int, re.findall(r'S(\d+)E(\d+)', file1)[0])
            season2, episode2 = map(int, re.findall(r'S(\d+)E(\d+)', file2)[0])
            return (season1 - season2) * 1000 + (episode1 - episode2)

        current_block_id = None
        sequence = []
        for root, _, files in os.walk(show_folder):
            # Sorting files using custom comparison function
            files.sort(key=cmp_to_key(compare))
            for i, file in enumerate(files):
                if file.endswith(".mp4"):
                    full_path = os.path.join(root, file)

                    # Extract show details
                    show_name, season, episode = self._extract_details(full_path)

                    # Create block ID
                    block_id = self._create_block_id(show_name, season, episode)

                    # Check if new episode (different block_id)
                    if current_block_id and block_id != current_block_id:
                        # Using pd.concat to append DataFrames
                        result_df = pd.concat([result_df, pd.DataFrame({
                            "FULL_FILE_PATH": sequence,
                            "BLOCK_ID": [current_block_id] * len(sequence)
                        })], ignore_index=True)
                        sequence = []  # Reset sequence for new episode

                    # Determine if the current file is the first or last part
                    is_first_part = re.search(r'Part 1.mp4', file) is not None
                    is_last_part = i == len(files) - 1 or re.search(r'Part 1.mp4', files[i + 1]) is not None

                    # Organize the sequence for the current part
                    sequence += self._organize_sequence(intros, to_ads, backs, generics, full_path, is_first_part, is_last_part)
                    print(f"Current sequence: {sequence}")
                    current_block_id = block_id

        # Append remaining sequence for the last episode
        result_df = pd.concat([result_df, pd.DataFrame({
            "FULL_FILE_PATH": sequence,
            "BLOCK_ID": [current_block_id] * len(sequence)
        })], ignore_index=True)

        # Save the Excel file
        print(f"Final result DataFrame:\n{result_df}")
        self.add_to_commercial_injector_final(result_df)

    def add_to_commercial_injector_final(self, result_df):
        db = sqlite3.connect("toonami.db")
        c = db.cursor()

        # Add a 'Priority' column to the DataFrame and set it to 'High'
        result_df['Priority'] = 'High'

        # Check if 'Priority' column exists in SQLite table; if not, add it
        c.execute("PRAGMA table_info(commercial_injector_final);")
        columns = [column[1] for column in c.fetchall()]
        if "Priority" not in columns:
            c.execute("ALTER TABLE commercial_injector_final ADD COLUMN Priority TEXT;")

        # Update existing records in SQLite table to have 'Low' in 'Priority' column if they are blank or NULL
        c.execute("UPDATE commercial_injector_final SET Priority = 'Low' WHERE Priority IS NULL OR Priority = '';")

        # Append DataFrame to SQLite table
        result_df.to_sql('commercial_injector_final', db, if_exists='append', index=False)

        # Commit changes and close connection
        db.commit()
        db.close()

    def _extract_details(self, path):
        # Extracting show name, season, and episode using regex
        show_name = re.search(r'/([^/]+)/Season \d+/[^/]+ - S\d+E\d+', path.replace('\\', '/')).group(1)  # Modified line
        season = re.search(r'S(\d+)', path).group(1)
        episode = re.search(r'E(\d+)', path).group(1)
        return show_name, season, episode

    def _create_block_id(self, show_name, season, episode):
        # Handling special characters and forming the block ID
        show_name = re.sub(r'[^\w\s]', '', show_name).replace(" ", "_").upper()
        return f"{show_name}_S{season}E{episode}"

    def _organize_sequence(self, intros, to_ads, backs, generics, episode_part, is_first_part, is_last_part):
        # Organizing the sequence with intro, to ads, back, and episode part
        sequence = []
        if is_first_part:
            sequence.append(random.choice(intros))
        sequence.append(episode_part)
        if not is_last_part:
            if generics and random.random() < 0.5:  # 50% chance to replace "To Ads" or "Back" with a generic bump
                sequence.append(random.choice(to_ads) if random.random() < 0.5 else random.choice(generics))
                sequence.append(random.choice(backs) if random.random() >= 0.5 else random.choice(generics))
            else:
                sequence.append(random.choice(to_ads))
                sequence.append(random.choice(backs))

        # Optional: Rotating the intros, to ads, and backs for next selection
        intros.append(intros.pop(0))
        to_ads.append(to_ads.pop(0))
        backs.append(backs.pop(0))

        return sequence

if __name__ == "__main__":
    processor = AnimeShowProcessor()
    app = AnimeShowCompilerGUI(processor)
    app.run()
