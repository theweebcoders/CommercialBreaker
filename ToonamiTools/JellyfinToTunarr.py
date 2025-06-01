#!/usr/bin/env python3
import os
import json
import sqlite3
import logging
import requests
import pandas as pd
import config

# ------------------------------------------------------------------
# LOGGING CONFIGURATION
# ------------------------------------------------------------------
DEBUG_MODE = False

# Setup logger
logger = logging.getLogger("JellyfinToTunarrSync")
logger.setLevel(logging.INFO if not DEBUG_MODE else logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

# Console handler for console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler only when DEBUG_MODE is True
if DEBUG_MODE:
    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "jellyfintotunarrsync.log"
    )
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(f"Debug log file created at: {log_path}")


class JellyfinToTunarr:
    def __init__(
        self,
        jellyfin_url,
        jellyfin_token,
        jellyfin_user_id,
        library_name,
        table,
        tunarr_url,
        channel_number,
        flex_duration,
        channel_name=None,
    ):
        self.jellyfin_url = jellyfin_url
        self.jellyfin_token = jellyfin_token
        self.jellyfin_user_id = jellyfin_user_id
        self.library_name = library_name
        self.tunarr_url = tunarr_url.rstrip("/")
        self.channel_number = channel_number
        self.flex_duration = flex_duration
        self.channel_name = channel_name or library_name
        self.table = table
        self.df = self.load_db_data()
        self.skip_reasons = {}  # Used to tally why items might be skipped if needed
        self.jellyfin_source_info = self.get_jellyfin_source_info()

    def load_db_data(self):
        """Load data from the specified database table."""
        try:
            db_path = config.DATABASE_PATH
            with sqlite3.connect(db_path) as conn:
                df = pd.read_sql_query(f"SELECT * FROM {self.table}", conn)
                logger.info(
                    f"Loaded {len(df)} records from database table '{self.table}'"
                )
                return df
        except Exception as e:
            logger.error(f"Error loading database data: {e}")
            return pd.DataFrame()

    def get_jellyfin_source_info(self):
        """Get or create a Jellyfin media source in Tunarr"""
        try:
            # Check if Jellyfin source already exists
            response = requests.get(f"{self.tunarr_url}/api/media-sources")
            if response.status_code == 200:
                sources = response.json()
                for source in sources:
                    if (
                        source.get("type") == "jellyfin"
                        and source.get("uri") == self.jellyfin_url
                    ):
                        logger.info(
                            f"Found existing Jellyfin media source: {source.get('name')}"
                        )
                        return source

            # Create new Jellyfin source if none exists
            source_id = self.create_jellyfin_media_source()
            if source_id:
                # Fetch the created source info
                response = requests.get(
                    f"{self.tunarr_url}/api/media-sources/{source_id}"
                )
                if response.status_code == 200:
                    return response.json()

            return None
        except Exception as e:
            logger.error(f"Error getting Jellyfin source info: {e}")
            return None

    def create_jellyfin_media_source(self):
        """Create a Jellyfin media source in Tunarr if one doesn't exist"""
        try:
            logger.info(f"Creating a Jellyfin media source for {self.jellyfin_url}...")

            # Prepare the media source data according to InsertMediaSourceRequestSchema
            media_source_data = {
                "type": "jellyfin",
                "name": "Jellyfin Server",  # Default name that can be changed later
                "uri": self.jellyfin_url,
                "accessToken": self.jellyfin_token,
                "sendGuideUpdates": False,
                "sendChannelUpdates": False,
            }

            response = requests.post(
                f"{self.tunarr_url}/api/media-sources", json=media_source_data
            )

            if response.status_code == 201:
                result = response.json()
                logger.info(
                    f"Successfully created Jellyfin media source with ID: {result.get('id')}"
                )
                return result.get("id")
            else:
                logger.error(
                    f"Failed to create Jellyfin media source. Status code: {response.status_code}"
                )
                logger.error(
                    f"Response: {response.text if hasattr(response, 'text') else ''}"
                )
                raise ValueError(
                    f"Failed to create Jellyfin media source: {response.text if hasattr(response, 'text') else ''}"
                )
        except Exception as e:
            logger.error(f"Error creating Jellyfin media source: {e}")
            raise ValueError(f"Error creating Jellyfin media source: {e}")

    def get_jellyfin_library_id(self):
        """Get the Jellyfin library ID for the specified library name"""
        try:
            headers = {
                "Authorization": f"MediaBrowser Token={self.jellyfin_token}",
                "Content-Type": "application/json",
            }

            # Get user's accessible libraries
            response = requests.get(
                f"{self.jellyfin_url}/Users/{self.jellyfin_user_id}/Views",
                headers=headers,
            )

            if response.status_code == 200:
                libraries_data = response.json()
                items = libraries_data.get("Items", [])

                for item in items:
                    if item.get("Name") == self.library_name:
                        return item.get("Id")

                logger.error(f"Library '{self.library_name}' not found")
                return None
            else:
                logger.error(f"Failed to get libraries: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting Jellyfin library ID: {e}")
            return None

    def get_all_jellyfin_media(self):
        """Fetch all media items from the specified Jellyfin library"""
        library_id = self.get_jellyfin_library_id()
        if not library_id:
            return []

        try:
            headers = {
                "Authorization": f"MediaBrowser Token={self.jellyfin_token}",
                "Content-Type": "application/json",
            }

            # Get all items from the library
            params = {
                "ParentId": library_id,
                "Recursive": "true",
                "IncludeItemTypes": "Episode,Movie",  # Focus on episodes and movies
                "Fields": "Path,MediaStreams,Overview,Genres,ProductionYear,PremiereDate",
            }

            response = requests.get(
                f"{self.jellyfin_url}/Users/{self.jellyfin_user_id}/Items",
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                media_data = response.json()
                items = media_data.get("Items", [])
                logger.info(
                    f"Retrieved {len(items)} media items from Jellyfin library '{self.library_name}'"
                )
                return items
            else:
                logger.error(f"Failed to get media items: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching Jellyfin media: {e}")
            return []

    def filter_media_by_database(self, jellyfin_items):
        """Filter Jellyfin media items based on database entries"""
        if self.df.empty:
            logger.warning("Database table is empty, no filtering will be applied")
            return jellyfin_items

        filtered_items = []
        self.skip_reasons = {"not_in_db": 0, "no_path_match": 0}

        for item in jellyfin_items:
            item_path = item.get("Path", "")
            item_name = item.get("Name", "")

            # Try to match with database entries
            matched = False
            for _, db_row in self.df.iterrows():
                db_path = str(db_row.get("file_path", ""))

                # Simple path matching - could be enhanced
                if item_path and (item_path in db_path or db_path in item_path):
                    matched = True
                    break

                # Try name matching as fallback
                if item_name and item_name in str(db_row.get("show_name", "")):
                    matched = True
                    break

            if matched:
                filtered_items.append(item)
            else:
                self.skip_reasons["not_in_db"] += 1
                logger.debug(f"Skipping '{item_name}' - not found in database")

        logger.info(
            f"Filtered to {len(filtered_items)} items (skipped {len(jellyfin_items) - len(filtered_items)})"
        )
        return filtered_items

    def convert_jellyfin_to_tunarr_format(self, jellyfin_items):
        """Convert Jellyfin media items to Tunarr format"""
        tunarr_items = []

        for item in jellyfin_items:
            try:
                tunarr_item = {
                    "type": "content",
                    "duration": item.get("RunTimeTicks", 0)
                    // 10000,  # Convert from ticks to milliseconds
                    "title": item.get("Name", "Unknown"),
                    "externalSourceType": "jellyfin",
                    "externalSourceName": (
                        self.jellyfin_source_info.get("name", "Jellyfin Server")
                        if self.jellyfin_source_info
                        else "Jellyfin Server"
                    ),
                    "externalKey": item.get("Id"),
                    "externalSourceId": (
                        self.jellyfin_source_info.get("id")
                        if self.jellyfin_source_info
                        else None
                    ),
                    "summary": item.get("Overview", ""),
                    "date": item.get("PremiereDate", ""),
                    "rating": "",  # Jellyfin doesn't have the same rating system as Plex
                    "year": item.get("ProductionYear"),
                    "plexFilePath": item.get(
                        "Path", ""
                    ),  # Keep original field name for compatibility
                    "showTitle": self._extract_show_title(item),
                    "seasonNumber": self._extract_season_number(item),
                    "episodeNumber": self._extract_episode_number(item),
                    "episodeTitle": item.get("Name", ""),
                }

                tunarr_items.append(tunarr_item)

            except Exception as e:
                logger.error(
                    f"Error converting Jellyfin item '{item.get('Name', 'Unknown')}': {e}"
                )
                continue

        logger.info(f"Converted {len(tunarr_items)} Jellyfin items to Tunarr format")
        return tunarr_items

    def _extract_show_title(self, item):
        """Extract show title from Jellyfin item"""
        # For episodes, get the series name
        if item.get("Type") == "Episode":
            return item.get("SeriesName", item.get("Name", "Unknown"))
        else:
            return item.get("Name", "Unknown")

    def _extract_season_number(self, item):
        """Extract season number from Jellyfin item"""
        if item.get("Type") == "Episode":
            return item.get("ParentIndexNumber", 1)
        return 1

    def _extract_episode_number(self, item):
        """Extract episode number from Jellyfin item"""
        if item.get("Type") == "Episode":
            return item.get("IndexNumber", 1)
        return 1

    def get_channel_by_number(self, channel_number):
        """Get channel information by channel number from Tunarr"""
        try:
            response = requests.get(f"{self.tunarr_url}/api/channels")
            if response.status_code == 200:
                channels = response.json()
                for channel in channels:
                    if str(channel.get("number")) == str(channel_number):
                        return channel
            return None
        except Exception as e:
            logger.error(f"Error getting channel by number: {e}")
            return None

    def create_channel(self, name, number):
        """Create a new channel in Tunarr"""
        try:
            channel_data = {
                "name": name,
                "number": number,
                "watermark": {"enabled": False},
                "icon": {
                    "path": "",
                    "width": 0,
                    "duration": 0,
                    "position": "bottom-right",
                },
                "guideMinimumDuration": 30000,
                "groupTitle": "",
                "disableFillerOverlay": False,
                "startTime": 0,
                "offline": {"picture": "", "soundtrack": "", "mode": "pic"},
            }

            logger.debug("Creating channel with data: %s", channel_data)
            response = requests.post(
                f"{self.tunarr_url}/api/channels", json=channel_data
            )
            if response.status_code == 201:
                new_channel = response.json()
                logger.info(
                    "Channel '%s' created successfully.", new_channel.get("name")
                )
                return new_channel
            else:
                logger.error(
                    "Failed to create channel. Status code: %d", response.status_code
                )
                logger.error(response.text)
                return None
        except Exception as e:
            logger.error(f"Error creating channel: {e}")
            return None

    def delete_all_programs(self, channel_id):
        """Delete all existing programs from a channel"""
        try:
            response = requests.delete(
                f"{self.tunarr_url}/api/channels/{channel_id}/programming"
            )
            if response.status_code == 200:
                logger.info("Successfully deleted all programs from channel")
                return True
            else:
                logger.error(
                    "Failed to delete programs. Status code: %d", response.status_code
                )
                return False
        except Exception as e:
            logger.error(f"Error deleting programs: {e}")
            return False

    def post_manual_lineup(self, channel_id, jellyfin_items):
        """Post the manual lineup to Tunarr"""
        try:
            # Convert Jellyfin items to Tunarr format
            tunarr_items = self.convert_jellyfin_to_tunarr_format(jellyfin_items)

            if not tunarr_items:
                logger.warning("No items to add to channel")
                return False

            # Add flex items between content if flex duration is specified
            final_lineup = []
            for i, item in enumerate(tunarr_items):
                final_lineup.append(item)

                # Add flex between items (except after the last item)
                if i < len(tunarr_items) - 1 and self.flex_duration > 0:
                    flex_item = {
                        "type": "flex",
                        "duration": self.flex_duration
                        * 1000,  # Convert to milliseconds
                    }
                    final_lineup.append(flex_item)

            payload = {"lineup": final_lineup}

            logger.debug(
                "Final JSON payload to POST:\n%s", json.dumps(payload, indent=2)
            )
            url = f"{self.tunarr_url}/api/channels/{channel_id}/programming"
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Programs added successfully!")
                return True
            else:
                logger.error(
                    "Failed to add programs. Status code: %d", response.status_code
                )
                logger.error(response.text)
                return False
        except Exception as e:
            logger.error(f"Error posting manual lineup: {e}")
            return False

    def show_skip_summary(self):
        """Display summary of skipped items"""
        if self.skip_reasons:
            logger.info("=== SKIP SUMMARY ===")
            for reason, count in self.skip_reasons.items():
                logger.info(f"{reason}: {count} items")
            logger.info("==================")

    def run(self):
        """Main execution method"""
        try:
            logger.info(
                f"Starting JellyfinToTunarr sync for library '{self.library_name}'"
            )

            # Fetch all media from Jellyfin
            logger.info("Fetching media items from Jellyfin...")
            all_media = self.get_all_jellyfin_media()

            if not all_media:
                logger.error("No media items found in Jellyfin library")
                self.show_skip_summary()
                return False

            # Filter media based on database if available
            if not self.df.empty:
                logger.info("Filtering media based on database entries...")
                filtered_media = self.filter_media_by_database(all_media)
            else:
                filtered_media = all_media
                logger.info(
                    "Using all %d items from Jellyfin library", len(filtered_media)
                )

            # Create or find the Tunarr channel
            channel = self.get_channel_by_number(self.channel_number)
            if not channel:
                logger.info(
                    "Channel number %s not found; creating.", str(self.channel_number)
                )
                channel = self.create_channel(self.channel_name, self.channel_number)
                if not channel:
                    logger.error("Failed to create channel. Exiting.")
                    self.show_skip_summary()
                    return False
            else:
                logger.info("Using existing channel: %s", channel.get("name"))

            channel_id = channel.get("uuid", channel.get("id"))
            if not channel_id:
                logger.error(
                    "Could not determine channel ID from channel object. Exiting."
                )
                self.show_skip_summary()
                return False

            # Clear the existing channel schedule
            logger.info("Deleting old programs from channel %s", channel_id)
            if not self.delete_all_programs(channel_id):
                logger.error("Failed to delete old programs. Exiting.")
                self.show_skip_summary()
                return False

            # Build the final JSON payload from Jellyfin items and POST it
            logger.info("Posting new programs to channel %s", channel_id)
            success = self.post_manual_lineup(channel_id, filtered_media)
            if success:
                logger.info("Channel programming updated successfully!")
            else:
                logger.error("Failed to update channel programming.")
            self.show_skip_summary()
            return success

        except Exception as e:
            logger.error(f"Error in JellyfinToTunarr run: {e}")
            self.show_skip_summary()
            return False
