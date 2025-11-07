import re
import os
import sys
import config
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
from API.utils.NetworkUtils import CurlHttpClient, RequestException, Timeout, ConnectionError
from plexapi.server import PlexServer
from .utils import show_name_mapper
from .utils.DizqueTVHelpers import create_program_dict_from_plex_item, create_default_channel_settings


class PlexToDizqueTVSimplified:
    def __init__(self, plex_url, plex_token, anime_library, toonami_library, table, dizquetv_url, channel_number, cutless_mode):
        self.error_manager = get_error_manager()
        
        # Store all parameters directly from arguments - no DB interaction
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.anime_library = anime_library
        self.toonami_library = toonami_library
        self.table = table
        self.dizquetv_url = dizquetv_url
        self.channel_number = channel_number
        # Determine cutless mode based on command-line arguments
        self.cutless_mode = cutless_mode
        
        # These will be initialized in run()
        self.plex = None
        self.df = None
        self.anime_media = {}
        self.toonami_media = {}

    def run(self, df=None):
        print("Initializing the connection to Plex and dizqueTV...")
        
        # Connect to Plex
        try:
            self.plex = PlexServer(self.plex_url, self.plex_token)
        except Exception as e:
            self.error_manager.send_error_level(
                source="PlexToDizqueTV",
                operation="run",
                message="Cannot connect to Plex",
                details=str(e),
                suggestion="Check that your Plex server is running and your credentials are correct"
            )
            raise

        # Test DizqueTV connection
        try:
            response = CurlHttpClient.get(f"{self.dizquetv_url}/api/channels", timeout=10)
            if response.status_code != 200:
                raise Exception(f"DizqueTV returned status code {response.status_code}")
            print("Connected to DizqueTV successfully.")
        except (Timeout, ConnectionError, RequestException) as e:
            self.error_manager.send_error_level(
                source="PlexToDizqueTV",
                operation="run",
                message="Cannot connect to DizqueTV",
                details=f"Failed to connect to {self.dizquetv_url}: {str(e)}",
                suggestion="Check that DizqueTV is running and the URL is correct"
            )
            raise
        
        # Use provided dataframe or load from table name
        if df is not None:
            self.df = df
            print("Using provided DataFrame for lineup data.")
        else:
            # The caller should provide the dataframe, but this provides backward compatibility
            print(f"Loading data from table '{self.table}' in database.")
            db_manager = get_db_manager()
            
            # Check if table exists
            if not db_manager.table_exists(self.table):
                self.error_manager.send_error_level(
                    source="PlexToDizqueTV",
                    operation="run",
                    message=f"Lineup table '{self.table}' not found",
                    details="The specified lineup table does not exist in the database",
                    suggestion="Run 'Prepare Cut Anime for Lineup' first to create the necessary lineup data"
                )
                raise Exception(f"Table {self.table} not found")

            self.df = db_manager.fetchall_as_dicts(f"SELECT * FROM {self.table}")

        # Initialize libraries
        self._init_libraries()
        
        print("Processing media items for dizqueTV...")
        
        # Process each file in the database
        to_add = []
        missing_files = []
        
        for index, row in enumerate(self.df):
            file_path = row['FULL_FILE_PATH']
            filename = self.get_filename_from_path(file_path)

            # Get the media item
            plex_item = self.get_media_item(file_path)

            if plex_item:
                print(f"Converting Plex item: {plex_item.title}")

                try:
                    # Get custom timing parameters if available
                    start_time = int(row['startTime']) if row.get('startTime') is not None else None
                    end_time = int(row['endTime']) if row.get('endTime') is not None else None

                    # Convert the plex item to a program dictionary
                    program = create_program_dict_from_plex_item(
                        plex_item=plex_item,
                        plex_server=self.plex,
                        start_time=start_time,
                        end_time=end_time
                    )

                    if start_time is not None:
                        print(f"  - Using custom start time: {start_time}ms")
                    if end_time is not None:
                        print(f"  - Using custom end time: {end_time}ms")

                    to_add.append(program)
                except Exception as e:
                    print(f"Error converting {plex_item.title}: {e}")
            else:
                print(f"Warning: Could not find {filename} in Plex libraries")
                missing_files.append(filename)
        
        if missing_files:
            print("\n===== MISSING FILES =====")
            print(f"Failed to find {len(missing_files)} files in Plex:")
            for missing_file in missing_files:
                print(f"  - {missing_file}")
                
            error_msg = f"Failed to find {len(missing_files)} files in Plex. See above for details."
            raise Exception(error_msg)
        
        print(f"Identified {len(to_add)} media items to add to the dizqueTV channel.")
        
        # Skip channel update if no programs were found
        if not to_add:
            print("No programs to add. Exiting.")
            return
        
        print("Checking and updating the dizqueTV channel...")

        # Get existing channel or create new one
        channel_data = None
        try:
            response = CurlHttpClient.get(f"{self.dizquetv_url}/api/channel/{self.channel_number}", timeout=10)
            if response.status_code == 200:
                channel_data = response.json()
                print(f"Found existing channel: {channel_data.get('name', 'Unknown')}")
            elif response.status_code == 404:
                print("Channel not found. Creating a new one...")
            else:
                raise Exception(f"Unexpected status code {response.status_code}")
        except (Timeout, ConnectionError, RequestException) as e:
            self.error_manager.send_error_level(
                source="PlexToDizqueTV",
                operation="run",
                message="Failed to get channel from DizqueTV",
                details=str(e),
                suggestion="Check DizqueTV connection"
            )
            raise

        # Create or update channel
        if channel_data is None:
            # Create new channel
            channel_data = create_default_channel_settings(
                channel_number=self.channel_number,
                channel_name=f"{config.network} Channel {self.channel_number}"
            )
            channel_data['programs'] = to_add

            try:
                response = CurlHttpClient.post(
                    f"{self.dizquetv_url}/api/channel",
                    json_data=channel_data,
                    timeout=30
                )
                if response.status_code not in [200, 201]:
                    raise Exception(f"Failed to create channel: status {response.status_code}")
                print("Channel created successfully.")
            except (Timeout, ConnectionError, RequestException) as e:
                self.error_manager.send_error_level(
                    source="PlexToDizqueTV",
                    operation="run",
                    message="Failed to create channel in DizqueTV",
                    details=str(e),
                    suggestion="Check DizqueTV connection and channel settings"
                )
                raise
        else:
            # Update existing channel - clear old programs and add new ones
            print("Clearing old programs and adding new ones...")
            channel_data['programs'] = to_add

            # Calculate total duration
            total_duration = sum(prog['duration'] for prog in to_add)
            channel_data['duration'] = total_duration

            try:
                response = CurlHttpClient.post(
                    f"{self.dizquetv_url}/api/channel",
                    json_data=channel_data,
                    timeout=60
                )
                if response.status_code != 200:
                    raise Exception(f"Failed to update channel: status {response.status_code}")
                print("Channel updated successfully.")
            except (Timeout, ConnectionError, RequestException) as e:
                self.error_manager.send_error_level(
                    source="PlexToDizqueTV",
                    operation="run",
                    message="Failed to update channel in DizqueTV",
                    details=str(e),
                    suggestion="Check DizqueTV connection and channel data"
                )
                raise

        print("Operation complete.")

    def _init_libraries(self):
        """Initialize Plex libraries and cache all media for faster lookup"""
        self.anime_media = {}
        self.toonami_media = {}

        # Get anime library media only if cutless mode is True (original behavior)
        if self.cutless_mode:
            try:
                print(f"Loading Anime library: {self.anime_library}")
                anime_section = self.plex.library.section(self.anime_library)

                # Get all shows in the anime library
                anime_shows = anime_section.all()
                print(f"Found {len(anime_shows)} shows in Anime library")

                # For each show, get all episodes
                for show in anime_shows:
                    try:
                        # For TV shows, episodes are organized by seasons
                        if hasattr(show, 'episodes') and callable(getattr(show, 'episodes')):
                            for episode in show.episodes():
                                try:
                                    # Get the file path and map it to the episode
                                    file_path = episode.media[0].parts[0].file
                                    filename = self.get_filename_from_path(file_path)
                                    # Store with and without extension for backward compatibility
                                    self.anime_media[filename] = episode
                                    self.anime_media[self.strip_extension(filename)] = episode
                                except (AttributeError, IndexError) as e:
                                    print(f"Error accessing episode {episode.title} of {show.title}: {e}")
                        # For movies, the show itself is the media item
                        elif hasattr(show, 'media') and show.media:
                            file_path = show.media[0].parts[0].file
                            filename = self.get_filename_from_path(file_path)
                            # Store with and without extension for backward compatibility
                            self.anime_media[filename] = show
                            self.anime_media[self.strip_extension(filename)] = show
                    except Exception as e:
                        print(f"Error processing show {show.title}: {e}")
            except Exception as e:
                print(f"Error loading Anime library: {e}")
        else:
            print("Cutless mode is False, skipping Anime library loading.")

        # Get toonami library media
        try:
            print(f"Loading Toonami library: {self.toonami_library}")
            toonami_section = self.plex.library.section(self.toonami_library)
            
            # For a standard library with videos, get all videos directly
            for video in toonami_section.all():
                try:
                    if hasattr(video, 'media') and video.media:
                        file_path = video.media[0].parts[0].file
                        filename = self.get_filename_from_path(file_path)
                        # Store with and without extension for backward compatibility
                        self.toonami_media[filename] = video
                        self.toonami_media[self.strip_extension(filename)] = video
                except (AttributeError, IndexError) as e:
                    print(f"Error accessing media for {video.title}: {e}")
        except Exception as e:
            print(f"Error loading Toonami library: {e}")
        
        print(f"Loaded {len(self.anime_media)} anime media items and {len(self.toonami_media)} toonami media items")

    def get_filename_from_path(self, path):
        """Extract the filename from a file path"""
        return re.split(r'[\\/]', path)[-1]
        
    def strip_extension(self, filename):
        """Remove the file extension from a filename"""
        return os.path.splitext(filename)[0]

    def determine_library(self, file_path):
        """Determine which Plex library to use based on file path"""
        # If cutless mode is False, always assume Toonami library
        if not self.cutless_mode:
            return self.toonami_library

        # Original logic if cutless mode is True
        filename = self.get_filename_from_path(file_path)
        if config.network.lower() in filename.lower() or re.search(r' - Part \d{1,2}\.', filename, re.IGNORECASE):
            return self.toonami_library
        else:
            return self.anime_library

    def parse_show_info(self, filename):
        """Parse show title, season, and episode from filename."""
        # Example: Fullmetal Alchemist - Brotherhood - S01E01 - Fullmetal Alchemist Bluray-1080p.mkv
        match = re.search(r'^(.*?)[\-_ ]+S(\d{2})E(\d{2})', filename, re.IGNORECASE)
        if match:
            show_title = match.group(1).replace('.', ' ').replace('_', ' ').strip()
            season = int(match.group(2))
            episode = int(match.group(3))
            return show_title, season, episode
        return None, None, None

    def fuzzy_find_show(self, anime_section, show_title):
        """Try to find a show in the section by fuzzy matching the title (ignoring punctuation/case)."""
        # Apply show name mappings using the mapper utility
        original_title = show_title
        mapped_title = show_name_mapper.map(show_title, strategy='first_match')

        def normalize(s):
            return re.sub(r'[^a-z0-9]', '', s.lower())
        
        target = normalize(mapped_title)
        
        # Try exact match first
        for show in anime_section.all():
            if normalize(show.title) == target:
                return show
        
        # Try partial match if exact fails
        for show in anime_section.all():
            if target in normalize(show.title):
                return show
        
        # If we get here and we applied a mapping, try the original title as a fallback
        if original_title != mapped_title:
            print(f"Mapped title not found, trying original title: '{original_title}'")
            target = normalize(original_title)
            
            # Exact match with original
            for show in anime_section.all():
                if normalize(show.title) == target:
                    return show
                    
            # Partial match with original
            for show in anime_section.all():
                if target in normalize(show.title):
                    return show
        
        return None

    def get_media_item(self, file_path):
        filename = self.get_filename_from_path(file_path)
        filename_no_ext = self.strip_extension(filename)

        # If cutless is False, only search Toonami library
        if not self.cutless_mode:
            print(f"Cutless mode False: Searching only Toonami library for '{filename}'")
            item = self._find_in_library(filename, filename_no_ext, self.toonami_library)
            # Return item if found, otherwise None
            return item

        # Original logic for cutless mode True
        primary_library = self.determine_library(file_path)
        secondary_library = self.toonami_library if primary_library == self.anime_library else self.anime_library

        # Try to find in primary library first
        item = self._find_in_library(filename, filename_no_ext, primary_library)
        if item:
            return item

        # If not found, try the other library
        print(f"File '{filename}' not found in {primary_library} library, trying {secondary_library} library...")
        item = self._find_in_library(filename, filename_no_ext, secondary_library)
        if item:
            return item

        # If still not found, return None
        return None
        
    def _find_in_library(self, filename, filename_no_ext, library_name):
        """Helper method to find a media item in a specific library"""
        # Skip anime library search if cutless mode is False
        if library_name == self.anime_library and not self.cutless_mode:
            return None

        if library_name == self.anime_library:
            # Try to find the file with extension
            if filename in self.anime_media:
                return self.anime_media[filename]
            # Try to find the file without extension
            if filename_no_ext in self.anime_media:
                return self.anime_media[filename_no_ext]
            
            # Try with Unicode normalization if we have special characters
            if any(ord(c) > 127 for c in filename):
                normalized_versions = self._normalize_unicode(filename)
                for norm_filename in normalized_versions:
                    if norm_filename in self.anime_media:
                        print(f"  Found via Unicode normalization: {norm_filename}")
                        return self.anime_media[norm_filename]

                # Also try with extension stripped
                for norm_filename in normalized_versions:
                    norm_no_ext = self.strip_extension(norm_filename)
                    if norm_no_ext in self.anime_media:
                        print(f"  Found via Unicode normalization (no ext): {norm_no_ext}")
                        return self.anime_media[norm_no_ext]

            # Fallback to parsing show info if not found by filename
            show_title, season, episode = self.parse_show_info(filename)
            if show_title and season and episode:
                try:
                    anime_section = self.plex.library.section(self.anime_library)
                    try:
                        show = anime_section.get(show_title)
                    except Exception:
                        show = self.fuzzy_find_show(anime_section, show_title)
                    if show:
                        ep = show.episode(season=season, episode=episode)
                        return ep
                    else:
                        print(f"Fuzzy match failed for show title: {show_title}")
                except Exception as e:
                    print(f"Could not find by show/season/episode: {show_title} S{season:02d}E{episode:02d}: {e}")
        else:
            # Try to find the file with extension
            if filename in self.toonami_media:
                return self.toonami_media[filename]
            # Try to find the file without extension
            if filename_no_ext in self.toonami_media:
                return self.toonami_media[filename_no_ext]

            # Try with Unicode normalization if we have special characters
            if any(ord(c) > 127 for c in filename):
                normalized_versions = self._normalize_unicode(filename)
                for norm_filename in normalized_versions:
                    if norm_filename in self.toonami_media:
                        print(f"  Found via Unicode normalization: {norm_filename}")
                        return self.toonami_media[norm_filename]

                # Also try with extension stripped
                for norm_filename in normalized_versions:
                    norm_no_ext = self.strip_extension(norm_filename)
                    if norm_no_ext in self.toonami_media:
                        print(f"  Found via Unicode normalization (no ext): {norm_no_ext}")
                        return self.toonami_media[norm_no_ext]
                    
        return None

    def _normalize_unicode(self, filename):
        """Generate variations of the filename with different Unicode normalizations"""
        import unicodedata
        
        variations = [filename]
        
        # Try different Unicode normalization forms
        for form in ['NFC', 'NFKC', 'NFD', 'NFKD']:
            normalized = unicodedata.normalize(form, filename)
            if normalized != filename and normalized not in variations:
                variations.append(normalized)
        
        # Also try ASCII-only version (remove accents)
        ascii_version = ''.join(c for c in unicodedata.normalize('NFKD', filename)
                               if not unicodedata.combining(c))
        if ascii_version != filename and ascii_version not in variations:
            variations.append(ascii_version)
            
        return variations