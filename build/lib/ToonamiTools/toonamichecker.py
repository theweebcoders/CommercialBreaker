import config
import os
import pandas as pd
import re
import requests
import sqlite3
from unidecode import unidecode
from bs4 import BeautifulSoup

class ToonamiShowsFetcher:
    def __init__(self):
        self.api_url = "https://en.wikipedia.org/w/api.php"
                
    def get_toonami_shows(self):
        """
        Fetches data of shows aired on Toonami from Wikipedia API and returns it as a pandas DataFrame.
        """
        params = {
            "action": "parse",
            "page": f"List of programs broadcast by {config.network}",
            "format": "json",
            "prop": "text",
        }

        response = requests.get(self.api_url, params=params)
        if response.status_code != 200:
            raise Exception("Failed to fetch data from Wikipedia API")

        data = response.json()
        html_content = data["parse"]["text"]["*"]

        soup = BeautifulSoup(html_content, 'html.parser')

        # Initialize lists to hold titles and years
        titles = []
        years = []

        # Find all tables with class 'wikitable'
        tables = soup.find_all('table', {'class': 'wikitable'})

        for table in tables:
            # Get the headers from the table
            header_row = table.find('tr')
            if not header_row:
                continue
            headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
            # Remove footnotes from headers (e.g., 'Airdate[a]' -> 'Airdate')
            headers = [re.sub(r'\[.*?\]', '', h) for h in headers]
            # Normalize headers
            headers = [h.strip().lower() for h in headers]

            # Check if 'title' or 'program' and 'year(s) aired' or 'airdate' are in headers
            if ('title' in headers or 'program' in headers) and any(h in headers for h in ['year(s) aired', 'airdate']):
                # This is a programming table
                # Get indices for 'title'/'program' and 'year(s) aired' or 'airdate'
                if 'title' in headers:
                    title_idx = headers.index('title')
                else:
                    title_idx = headers.index('program')

                if 'year(s) aired' in headers:
                    year_idx = headers.index('year(s) aired')
                else:
                    year_idx = headers.index('airdate')

                for row in table.find_all('tr')[1:]:  # Skip the header row
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= max(title_idx, year_idx) + 1:
                        title = cols[title_idx].get_text(strip=True)
                        year = cols[year_idx].get_text(strip=True)
                        # Clean up the title by removing references in brackets
                        title = re.sub(r'\[.*?\]', '', title)
                        # Remove any extra spaces
                        title = title.strip()
                        # Filter out rows where title is empty or looks like a date/time
                        if title and not re.match(r'^\d', title) and '–' not in title:
                            titles.append(title)
                            years.append(year)

        # Clean up 'Year' data
        cleaned_years = []
        for y in years:
            # Remove footnotes
            y = re.sub(r'\[.*?\]', '', y)
            # Extract all four-digit years
            extracted_years = re.findall(r'\b(?:19|20)\d{2}\b', y)
            if extracted_years:
                # Join multiple years with a comma
                cleaned_year = ', '.join(extracted_years)
            else:
                # If no year found, keep the original
                cleaned_year = y
            cleaned_years.append(cleaned_year)

        # Create DataFrame
        df = pd.DataFrame({'Title': titles, 'Year': cleaned_years})

        # Remove duplicates
        df = df.drop_duplicates(subset='Title')

        return df
    
class ToonamiChecker:
    def __init__(self, anime_folder):
        self.anime_folder = anime_folder
        self.toonami_shows_fetcher = ToonamiShowsFetcher()

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
        Compares Toonami shows data with video files in a directory.
        """
        folder_path = self.anime_folder

        print("Comparing Toonami shows data with video files in directory.")
        toonami_shows = self.toonami_shows_fetcher.get_toonami_shows()
        video_files = self.get_video_files()
        toonami_episodes = {}

        # Use the helper function to normalize and map Toonami show titles
        normalized_toonami_shows = [self.normalize_and_map(x, config.show_name_mapping) for x in toonami_shows['Title']]
        #print(normalized_toonami_shows) 1 line at a time
        for title in normalized_toonami_shows:
            print(title)

        for show in video_files:
            # Use the helper function to normalize and map video file titles
            normalized_show = self.normalize_and_map(show, config.show_name_mapping)

            if normalized_show in normalized_toonami_shows:
                for episode in video_files[show]:
                    full_path = os.path.join(folder_path, episode)
                    normalized_path = os.path.normpath(full_path)
                    toonami_episodes[(show, episode)] = normalized_path

        print(f"Found matches for {len(toonami_episodes)} episodes.")
        return toonami_episodes

    def save_episodes_to_spreadsheet(self, toonami_episodes, db_path=f"{config.network}.db"):
        print(f"Writing episode data to SQLite database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Toonami_Episodes'")
        table_exists = bool(cursor.fetchone())

        df = pd.DataFrame([(k[0], k[1], v.replace("\\", "/")) for k, v in toonami_episodes.items()],
                          columns=['Title', 'Episode', 'Full_File_Path'])

        if table_exists:
            existing_df = pd.read_sql('SELECT * FROM Toonami_Episodes', conn)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            duplicates = combined_df.duplicated(subset=['Title', 'Episode', 'Full_File_Path'], keep='last')
            combined_df = combined_df[~duplicates]
            combined_df.to_sql('Toonami_Episodes', conn, if_exists='replace', index=False)
        else:
            df.to_sql('Toonami_Episodes', conn, if_exists='replace', index=False)

        conn.close()
        print(f'Successfully wrote rows to {db_path}')

    def save_show_names_to_spreadsheet(self, toonami_episodes, db_path=f"{config.network}.db"):
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

    def prepare_episode_data(self):
        toonami_episodes = self.compare_shows()
        unique_show_names = {k[0] for k in toonami_episodes.keys()}

        return unique_show_names, toonami_episodes

    def process_selected_shows(self, selected_shows, toonami_episodes):
        filtered_episodes = {k: v for k, v in toonami_episodes.items() if k[0] in selected_shows}
        self.save_episodes_to_spreadsheet(filtered_episodes)
        self.save_show_names_to_spreadsheet(filtered_episodes)