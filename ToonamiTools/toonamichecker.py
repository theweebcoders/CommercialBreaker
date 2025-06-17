import config
import os
import pandas as pd
import re
import requests
from unidecode import unidecode
from bs4 import BeautifulSoup
from .utils import show_name_mapper
from API.utils import get_db_manager
from API.utils.ErrorManager import get_error_manager
import socket

class ToonamiShowsFetcher:
    def __init__(self):
        self.api_url = "https://en.wikipedia.org/w/api.php"
        self.error_manager = get_error_manager()
    
    def check_internet_connection(self):
        """Check if we have internet connectivity by trying to reach common DNS servers."""
        try:
            # Try to connect to Cloudflare DNS (1.1.1.1) on port 53
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            return True
        except (socket.timeout, socket.error):
            try:
                # Fallback to Google DNS (8.8.8.8)
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                return True
            except (socket.timeout, socket.error):
                return False
    
    def check_wikipedia_connection(self):
        """Check if Wikipedia is reachable."""
        try:
            response = requests.get("https://en.wikipedia.org", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
                
    def get_toonami_shows(self):
        """
        Fetches data of shows aired on Toonami from Wikipedia API and returns it as a pandas DataFrame.
        """
        # Check internet connectivity first
        if not self.check_internet_connection():
            self.error_manager.send_critical(
                source="ToonamiShowsFetcher",
                operation="get_toonami_shows",
                message="No internet connection detected",
                details="Unable to connect to external DNS servers (1.1.1.1, 8.8.8.8)",
                suggestion="Please check your internet connection and try again"
            )
            raise Exception("No internet connection")
        
        # Check Wikipedia specifically
        if not self.check_wikipedia_connection():
            self.error_manager.send_error_level(
                source="ToonamiShowsFetcher",
                operation="get_toonami_shows",
                message="Cannot connect to Wikipedia",
                details="Internet connection is working but Wikipedia is unreachable",
                suggestion="Wikipedia may be down or blocked. Try again later or check https://www.isitdownrightnow.com/wikipedia.org.html"
            )
            raise Exception("Cannot connect to Wikipedia")
        
        params = {
            "action": "parse",
            "page": f"List of programs broadcast by {config.network}",
            "format": "json",
            "prop": "text",
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
        except requests.Timeout:
            self.error_manager.send_error_level(
                source="ToonamiShowsFetcher",
                operation="get_toonami_shows",
                message="Wikipedia API request timed out",
                details="The request took longer than 10 seconds",
                suggestion="Wikipedia may be slow. Try again in a few minutes"
            )
            raise
        except requests.HTTPError as e:
            self.error_manager.send_error_level(
                source="ToonamiShowsFetcher",
                operation="get_toonami_shows",
                message=f"Wikipedia API returned error: {e.response.status_code}",
                details=f"Failed to fetch page: {params['page']}",
                suggestion="Check if the page name is correct or if Wikipedia's API has changed"
            )
            raise
        except requests.RequestException as e:
            self.error_manager.send_error_level(
                source="ToonamiShowsFetcher",
                operation="get_toonami_shows",
                message="Failed to fetch data from Wikipedia API",
                details=str(e),
                suggestion="Check your internet connection and try again"
            )
            raise

        data = response.json()
        
        # Check if we got valid data
        if "parse" not in data or "text" not in data["parse"]:
            self.error_manager.send_error_level(
                source="ToonamiShowsFetcher",
                operation="get_toonami_shows",
                message="Invalid response from Wikipedia API",
                details="Response missing expected 'parse' or 'text' fields",
                suggestion="Wikipedia API format may have changed. Please report this issue"
            )
            raise Exception("Invalid Wikipedia API response")
        
        html_content = data["parse"]["text"]["*"]

        soup = BeautifulSoup(html_content, 'html.parser')

        # Initialize lists to hold titles and years
        titles = []
        years = []

        # Find all tables with class 'wikitable'
        tables = soup.find_all('table', {'class': 'wikitable'})
        
        if not tables:
            self.error_manager.send_warning(
                source="ToonamiShowsFetcher",
                operation="get_toonami_shows",
                message="No tables found on Wikipedia page",
                details=f"Expected wikitable elements on page: {params['page']}",
                suggestion="The page format may have changed or the network name may be incorrect"
            )

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
        self.error_manager = get_error_manager()

    def get_video_files(self):
        """
        Retrieves all video files in a directory.
        """
        folder_path = self.anime_folder
        
        # Check if folder exists
        if not os.path.exists(folder_path):
            self.error_manager.send_error_level(
                source="ToonamiChecker",
                operation="get_video_files",
                message=f"Anime folder not found: {folder_path}",
                details="The specified directory does not exist",
                suggestion="Check the folder path in your configuration"
            )
            raise FileNotFoundError(f"Directory not found: {folder_path}")
        
        # Check if we have read permissions
        if not os.access(folder_path, os.R_OK):
            self.error_manager.send_error_level(
                source="ToonamiChecker",
                operation="get_video_files",
                message=f"No read permission for folder: {folder_path}",
                details="Cannot access the specified directory",
                suggestion="Check folder permissions or run with appropriate privileges"
            )
            raise PermissionError(f"No read access to: {folder_path}")
        
        episode_files = {}
        file_count = 0
        print(f"Starting to walk through directory: {folder_path}")
        
        try:
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
        except Exception as e:
            self.error_manager.send_error_level(
                source="ToonamiChecker",
                operation="get_video_files",
                message="Error scanning video files",
                details=str(e),
                suggestion="Check if the directory is accessible and not corrupted"
            )
            raise
        
        print(f"Processed {file_count} files.")
        
        if file_count == 0:
            self.error_manager.send_error_level(
                source="ToonamiChecker",
                operation="get_video_files",
                message="No video files found",
                details=f"No .mkv, .mp4, .avi, or .flv files in {folder_path}",
                suggestion="Check if the folder contains video files or adjust the file extensions"
            )
            raise FileNotFoundError("No video files found")
        
        return episode_files

    def compare_shows(self):
        """
        Compares Toonami shows data with video files in a directory.
        """
        folder_path = self.anime_folder

        print("Comparing Toonami shows data with video files in directory.")
        
        try:
            toonami_shows = self.toonami_shows_fetcher.get_toonami_shows()
        except Exception as e:
            # Error already logged by get_toonami_shows
            return {}
        
        try:
            video_files = self.get_video_files()
        except Exception as e:
            # Error already logged by get_video_files
            return {}
        
        toonami_episodes = {}

        # Use the show_name_mapper to normalize and map Toonami show titles
        normalized_toonami_shows = [show_name_mapper.normalize_and_map(x) for x in toonami_shows['Title']]
        #print(normalized_toonami_shows) 1 line at a time
        for title in normalized_toonami_shows:
            print(title)

        for show in video_files:
            # Use the show_name_mapper to normalize and map video file titles
            normalized_show = show_name_mapper.normalize_and_map(show)

            if normalized_show in normalized_toonami_shows:
                for episode in video_files[show]:
                    full_path = os.path.join(folder_path, episode)
                    normalized_path = os.path.normpath(full_path)
                    toonami_episodes[(show, episode)] = normalized_path

        print(f"Found matches for {len(toonami_episodes)} episodes.")
        
        if len(toonami_episodes) == 0:
            self.error_manager.send_error_level(
                source="ToonamiChecker",
                operation="compare_shows",
                message=f"No {config.network} shows found in your library",
                details=f"None of your video files match shows that aired on {config.network}",
                suggestion="Check if your files are named correctly (ShowName - S##E##). See: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )
            raise ValueError("No matching Toonami shows found")
        return toonami_episodes

    def save_episodes_to_spreadsheet(self, toonami_episodes, db_path = config.DATABASE_PATH):
        print(f"Writing episode data to SQLite database: {db_path}")
        db_manager = get_db_manager()

        # Check if table exists
        result = db_manager.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='Toonami_Episodes'"
        )
        table_exists = bool(result)

        # Apply show name mapping to episode data BEFORE saving
        mapped_episodes = []
        for (show_title, episode), full_path in toonami_episodes.items():
            # Map the show title
            mapped_title = show_name_mapper.map(show_title, strategy='all')
            mapped_episodes.append((mapped_title, episode, full_path.replace("\\", "/")))
        
        df = pd.DataFrame(mapped_episodes, columns=['Title', 'Episode', 'Full_File_Path'])

        with db_manager.transaction() as conn:
            if table_exists:
                existing_df = pd.read_sql('SELECT * FROM Toonami_Episodes', conn)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                duplicates = combined_df.duplicated(subset=['Title', 'Episode', 'Full_File_Path'], keep='last')
                combined_df = combined_df[~duplicates]
                combined_df.to_sql('Toonami_Episodes', conn, if_exists='replace', index=False)
            else:
                df.to_sql('Toonami_Episodes', conn, if_exists='replace', index=False)

        print(f'Successfully wrote rows to {db_path}')

    def save_show_names_to_spreadsheet(self, toonami_episodes, db_path = config.DATABASE_PATH):
        print(f"Writing show names to SQLite database: {db_path}")
        unique_show_names = {k[0] for k in toonami_episodes.keys()}
        db_manager = get_db_manager()

        # Check if table exists
        result = db_manager.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='Toonami_Shows'"
        )
        table_exists = bool(result)

        # Apply show name mapping BEFORE saving to database
        mapped_show_names = []
        for show_name in unique_show_names:
            # Map the show name using all strategies
            mapped_name = show_name_mapper.map(show_name, strategy='all')
            mapped_show_names.append(mapped_name)
        
        df = pd.DataFrame(mapped_show_names, columns=['Title'])

        with db_manager.transaction() as conn:
            if table_exists:
                existing_df = pd.read_sql('SELECT * FROM Toonami_Shows', conn)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                # Step 4: Identify duplicates based on 'Title'
                duplicates = combined_df.duplicated(subset=['Title'], keep='last')
                # Remove entire rows where duplicates are found
                combined_df = combined_df[~duplicates]

                combined_df.to_sql('Toonami_Shows', conn, if_exists='replace', index=False)
            else:
                df.to_sql('Toonami_Shows', conn, if_exists='replace', index=False)

        print(f'Successfully wrote rows to {db_path}')

    def prepare_episode_data(self):
        toonami_episodes = self.compare_shows()
        unique_show_names = {k[0] for k in toonami_episodes.keys()}

        return unique_show_names, toonami_episodes

    def process_selected_shows(self, selected_shows, toonami_episodes):
        filtered_episodes = {k: v for k, v in toonami_episodes.items() if k[0] in selected_shows}
        self.save_episodes_to_spreadsheet(filtered_episodes)
        self.save_show_names_to_spreadsheet(filtered_episodes)