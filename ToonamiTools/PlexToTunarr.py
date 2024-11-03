import requests
import json
import uuid
from datetime import datetime, UTC, timedelta
import time
from typing import List, Dict, Optional, Union
from plexapi.server import PlexServer
from plexapi.video import Episode, Movie
import sqlite3
import pandas as pd
import config
import os

class PlexToTunarr:
    def __init__(self, plex_url: str, plex_token: str, library_name: str, table: str, tunarr_url: str, channel_number: int):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.library_name = library_name
        self.table = table
        self.base_url = f"{tunarr_url}/api"
        self.channel_number = channel_number
        
        self.headers = {
            "Content-Type": "application/json",
        }
        print(f"Connecting to Plex at {plex_url}")
        self.plex = PlexServer(plex_url, plex_token)
        print("Connected to Plex successfully")

    @staticmethod
    def get_filename_from_path(path: str) -> str:
        """Extract filename from full path."""
        return os.path.basename(path)

    def get_episodes_from_db(self) -> List[Episode]:
        """Get episodes from SQLite DB and match with Plex library."""
        # Connect to SQLite database
        network_db = sqlite3.connect(f'{config.network}.db')
        print(f"Connected to SQLite database '{config.network}.db', focusing on table '{self.table}'")
        
        # Read data from table
        df = pd.read_sql_query(f"SELECT * FROM {self.table}", network_db)
        
        # Get all media from Plex library
        all_media = self.plex.library.section(self.library_name).all()
        media_dict = {self.get_filename_from_path(media.media[0].parts[0].file): media 
                     for media in all_media if hasattr(media, 'media') and media.media}
        
        # Get file paths from database and convert to filenames
        file_paths = df['FULL_FILE_PATH'].tolist()
        file_names = [self.get_filename_from_path(path) for path in file_paths]
        
        # Match with Plex media
        playlist_media = [media_dict[file_name] for file_name in file_names if file_name in media_dict]
        print(f"Identified {len(playlist_media)} media items to add to the tunarr channel.")
        
        network_db.close()
        return playlist_media

    def create_program_entry(self, media_item: Union[Episode, Movie], index: int) -> Dict:
        """Create a program entry from a Plex media item (Episode or Movie)."""
        program_id = f"plex|Shenron|{media_item.ratingKey}"

        # Convert rating to number if possible, default to 0
        try:
            rating_value = float(media_item.contentRating.replace('TV-', '').replace('G', '0').replace('PG', '1').replace('14', '2').replace('MA', '3')) if hasattr(media_item, 'contentRating') and media_item.contentRating else 0
        except (ValueError, AttributeError):
            rating_value = 0

        # Basic program data that works for both movies and episodes
        program_data = {
            "ratingKey": str(media_item.ratingKey),
            "key": media_item.key,
            "guid": media_item.guid,
            "type": "movie" if not hasattr(media_item, 'parentRatingKey') else "episode",
            "title": media_item.title,
            "summary": media_item.summary or "",
            "duration": media_item.duration,
            "originallyAvailableAt": media_item.originallyAvailableAt.strftime("%Y-%m-%d") if hasattr(media_item, 'originallyAvailableAt') and media_item.originallyAvailableAt else "1970-01-01",
            "rating": rating_value,
            "year": media_item.year if hasattr(media_item, 'year') and media_item.year else 1970,
            "thumb": f"/library/metadata/{media_item.ratingKey}/thumb/{media_item.thumb}" if hasattr(media_item, 'thumb') else None,
        }

        # Add episode-specific fields if it's an episode
        if hasattr(media_item, 'parentRatingKey'):
            program_data.update({
                "parentRatingKey": str(media_item.parentRatingKey),
                "grandparentRatingKey": str(media_item.grandparentRatingKey),
                "grandparentKey": media_item.grandparentKey,
                "parentKey": media_item.parentKey,
                "grandparentTitle": media_item.grandparentTitle,
                "parentTitle": f"Season {media_item.seasonNumber}",
                "index": media_item.index,
                "parentIndex": media_item.seasonNumber,
            })
        
        base_entry = {
            "id": program_id,
            "persisted": False,
            "originalProgram": {
                "sourceType": "plex",
                "program": program_data
            },
            "duration": int(media_item.duration),
            "externalSourceName": "Shenron",
            "externalSourceType": "plex",
            "externalKey": str(media_item.ratingKey),
            "uniqueId": program_id,
            "type": "content",
            "subtype": "movie" if not hasattr(media_item, 'parentRatingKey') else "episode",
            "summary": media_item.summary or "",
            "title": media_item.grandparentTitle if hasattr(media_item, 'grandparentTitle') else media_item.title,
            "originalIndex": index,
            "startTimeOffset": 0
        }

        # Add episode-specific fields if it's an episode
        if hasattr(media_item, 'parentRatingKey'):
            base_entry.update({
                "episodeTitle": media_item.title,
                "episodeNumber": media_item.index,
                "seasonNumber": media_item.seasonNumber,
                "showId": f"plex|Shenron|{media_item.grandparentRatingKey}",
                "seasonId": f"plex|Shenron|{media_item.parentRatingKey}",
            })

        base_entry["externalIds"] = [{
            "type": "multi",
            "source": "plex",
            "sourceId": "Shenron",
            "id": str(media_item.ratingKey)
        }]

        return base_entry

    def create_lineup_entry(self, program_id: str, duration: int, index: int) -> Dict:
        """Create a lineup entry."""
        return {
            "duration": duration,
            "index": index,
            "persisted": True,
            "type": "content",
            "id": program_id
        }

    def create_channel(self, channel_name: str) -> Optional[str]:
        """Create a new channel."""
        channel_id = str(uuid.uuid4())
        start_time = int((datetime.now(UTC) + timedelta(seconds=5)).timestamp() * 1000)

        # Ensure channel_number is an integer
        try:
            channel_number = int(self.channel_number)
        except (ValueError, TypeError):
            print(f"Invalid channel number: {self.channel_number}")
            return None

        channel_payload = {
            "id": channel_id,
            "name": channel_name,
            "number": channel_number,  # Using the converted integer
            "startTime": start_time,
            "disableFillerOverlay": False,
            "duration": 3600,
            "groupTitle": "Default Group",
            "guideMinimumDuration": 1800,
            "icon": {
                "url": "https://example.com/icon.png"
            },
            "offline": {
                "mode": "pic",
                "picture": "https://example.com/offline-image.png"
            },
            "stealth": False,
            "transcoding": {
                "targetResolution": {
                    "widthPx": 1920,
                    "heightPx": 1080
                },
                "videoBitrate": 5000,
                "videoBufferSize": 10000
            },
            "streamMode": "hls"
        }

        url = f"{self.base_url}/channels"
        response = requests.post(url, headers=self.headers, json=channel_payload)

        if response.status_code in [200, 201]:
            print("Channel created successfully:", json.dumps(response.json(), indent=2))
            return response.json().get("id")
        print(f"Failed to create channel: {response.text}")
        return None

    def add_programming(self, channel_id: str, episodes: List[Episode]) -> bool:
        """Add multiple programs to a channel using Plex episodes."""
        time.sleep(2)

        programs = []
        lineup = []
        start_time_offsets = []
        current_offset = 0

        for index, episode in enumerate(episodes):
            program = self.create_program_entry(episode, index)
            program["startTimeOffset"] = current_offset
            programs.append(program)
            
            lineup_entry = self.create_lineup_entry(
                program_id=program["id"],
                duration=int(episode.duration),
                index=index
            )
            lineup.append(lineup_entry)
            
            start_time_offsets.append(current_offset)
            current_offset += int(episode.duration)

        programming_payload = {
            "type": "manual",
            "lineup": lineup,
            "programs": programs,
            "startTimeOffsets": start_time_offsets
        }

        print("\nSending programming payload:")
        print(json.dumps(programming_payload, indent=2))

        url = f"{self.base_url}/channels/{channel_id}/programming"
        response = requests.post(url, headers=self.headers, json=programming_payload)

        if response.status_code == 200:
            print("Programming added successfully:", json.dumps(response.json(), indent=2))
            return True
        print(f"Failed to add programming: {response.text}")
        return False

    def run(self):
        """Main execution method."""
        # Get episodes from database
        episodes = self.get_episodes_from_db()
        
        if not episodes:
            print("No episodes found in Plex matching the database entries")
            return False
        
        # Create channel
        channel_id = self.create_channel("Toonami")
        if not channel_id:
            print("Failed to create channel")
            return False
        
        # Add programming
        success = self.add_programming(channel_id, episodes)
        if success:
            print("\nSuccessfully created channel and added programming!")
            for episode in episodes:
                # Handle both movies and episodes
                if hasattr(episode, 'grandparentTitle'):
                    print(f"Added: {episode.grandparentTitle} - {episode.title}")
                else:
                    print(f"Added: {episode.title}")
            return True
        return False