import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from fuzzywuzzy import process
from config import *
import sqlite3
from config import *
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, IntVar
import ttkthemes as ttkthemes
import sv_ttk
from unidecode import unidecode

class IMDBScraper:
    """
    Class for scraping IMDB data.
    """

    def __init__(self, urls):
        self.urls = urls
        self.headers = HEADERS

    def get_imdb_shows(self):
        """
        Scrapes IMDB data and returns it as a pandas DataFrame.
        """
        titles = []
        years = []
        for url in self.urls:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('div', class_='lister-list')
            rows = table.find_all('div', class_='lister-item mode-detail')
            for row in rows:
                title = row.h3.a.text
                titles.append(title)
                year = row.h3.find('span', class_='lister-item-year text-muted unbold').text.strip('()')
                years.append(year)
        return pd.DataFrame({'Title': titles, 'Year': years})


class ToonamiChecker(IMDBScraper):

    def __init__(self, root, anime_folder):
        urls = URLS
        super().__init__(urls)
        self.root_window = root
        self.anime_folder = anime_folder

    def display_show_selection(self, unique_show_names):
        selected_shows = []

        def on_continue():
            for show, var in zip(sorted_unique_show_names, checkboxes):
                if var.get():
                    selected_shows.append(show)
            selection_window.destroy()

        selection_window = tk.Toplevel(self.root_window)
        selection_window.title("Select Shows")

        # Create a frame to contain the checkboxes and a scrollbar
        frame = tk.Frame(selection_window)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create a canvas to host the frame with the checkboxes
        canvas = tk.Canvas(frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar to the canvas
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure the canvas to use the scrollbar
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Create a frame to host the checkboxes inside the canvas
        checkbox_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=checkbox_frame, anchor="nw")

        # Sort the unique_show_names
        sorted_unique_show_names = sorted(unique_show_names)

        checkboxes = [tk.IntVar(value=1) for _ in sorted_unique_show_names]
        for show, var in zip(sorted_unique_show_names, checkboxes):
            ttk.Checkbutton(checkbox_frame, text=show, variable=var).pack(anchor="w")

        ttk.Button(selection_window, text="Continue", command=on_continue).pack()

        # Wait for the selection_window to close before returning the result
        self.root_window.wait_window(selection_window)

        return selected_shows

    def get_video_files(self):
        """
        Retrieves all video files in a directory.
        """
        folder_path = self.anime_folder
        episode_files = {}
        file_count = 0
        print(f"Starting to walk through directory: {folder_path}")
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(('.mkv', '.mp4', '.avi', '.flv')):
                    file_count += 1
                    if matched_title := re.findall(
                        r'^(.*?)(?: - S\d{1,2}E\d{1,2})', file, re.IGNORECASE
                    ):
                        show_title = matched_title[0].strip()
                        episode = file
                        rel_path = os.path.relpath(root, folder_path)  # calculate the relative path
                        if show_title in episode_files:
                            episode_files[show_title].append(os.path.join(rel_path, episode))
                        else:
                            episode_files[show_title] = [os.path.join(rel_path, episode)]
        print(f"Processed {file_count} files.")
        return episode_files
    
    def normalize_and_map(self, show_name, mapping):
        """Normalizes the show name by making it lowercase, removing special characters, and applying a name mapping."""
        normalized_name = unidecode(show_name.lower())
        
        # Replace special characters and underscores with a space, then replace multiple spaces with a single space
        normalized_name = re.sub(r'[^\w\s]', ' ', normalized_name)
        normalized_name = re.sub(r'_', ' ', normalized_name)
        normalized_name = re.sub(r'\s+', ' ', normalized_name).strip()
        
        return mapping.get(normalized_name, normalized_name)
    
    def compare_shows(self):
        """
        Compares scraped IMDB data with video files in a directory.
        """
        folder_path = self.anime_folder

        print("Comparing scraped IMDB data with video files in directory.")
        toonami_shows = self.get_imdb_shows()
        video_files = self.get_video_files()
        toonami_episodes = {}

        # Use the helper function to normalize and map IMDb show titles
        normalized_imdb_shows = [self.normalize_and_map(x, show_name_mapping) for x in toonami_shows['Title']]
        #print(normalized_imdb_shows) 1 line at a time
        for title in normalized_imdb_shows:
            print(title)
        
        for show in video_files:
            # Use the helper function to normalize and map video file titles
            normalized_show = self.normalize_and_map(show, show_name_mapping)
            
            if normalized_show in normalized_imdb_shows:
                for episode in video_files[show]:
                    full_path = os.path.join(folder_path, episode)
                    normalized_path = os.path.normpath(full_path)
                    toonami_episodes[(show, episode)] = normalized_path
        
        print(f"Found matches for {len(toonami_episodes)} episodes.")
        return toonami_episodes

    def save_episodes_to_spreadsheet(self, toonami_episodes, db_path="toonami.db"):
        print(f"Writing episode data to SQLite database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Toonami_Episodes'")
        table_exists = bool(cursor.fetchone())

        df = pd.DataFrame([(k[0], k[1], v.replace("\\", "/")) for k, v in toonami_episodes.items()],
                        columns=['Title', 'Episode', 'File Path'])

        if table_exists:
            existing_df = pd.read_sql('SELECT * FROM Toonami_Episodes', conn)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            duplicates = combined_df.duplicated(subset=['Title', 'Episode', 'File Path'], keep='last')
            combined_df = combined_df[~duplicates]
            combined_df.to_sql('Toonami_Episodes', conn, if_exists='replace', index=False)
        else:
            df.to_sql('Toonami_Episodes', conn, if_exists='replace', index=False)

        conn.close()
        print(f'Successfully wrote rows to {db_path}')
        
    def save_show_names_to_spreadsheet(self, toonami_episodes, db_path="toonami.db"):
        print(f"Writing show names to SQLite database: {db_path}")
        unique_show_names = {k[0] for k in toonami_episodes.keys()}
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Toonami_Shows'")
        table_exists = bool(cursor.fetchone())

        df = pd.DataFrame(list(unique_show_names), columns=['Title'])

        if table_exists:
            existing_df = pd.read_sql('SELECT * FROM Toonami_Shows', conn)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            # Step 4: Identify duplicates based on 'FULL_FILE_PATH'
            duplicates = combined_df.duplicated(subset=['Title'], keep='last')
            # Remove entire rows where duplicates are found
            combined_df = combined_df[~duplicates]

            combined_df.to_sql('Toonami_Shows', conn, if_exists='replace', index=False)
        else:
            df.to_sql('Toonami_Shows', conn, if_exists='replace', index=False)

        conn.close()
        print(f'Successfully wrote rows to {db_path}')

    def run(self):
        toonami_episodes = self.compare_shows()
        unique_show_names = {k[0] for k in toonami_episodes.keys()}
        selected_shows = self.display_show_selection(unique_show_names)
        filtered_episodes = {k: v for k, v in toonami_episodes.items() if k[0] in selected_shows}

        self.save_episodes_to_spreadsheet(filtered_episodes)
        self.save_show_names_to_spreadsheet(filtered_episodes)