#!/usr/bin/env python3
import os
import re
import json
import sqlite3
import logging
import requests
import pandas as pd
from datetime import datetime
from plexapi.server import PlexServer
import config

# ------------------------------------------------------------------
# LOGGING CONFIGURATION: log to console by default, file only in debug mode
# ------------------------------------------------------------------
logger = logging.getLogger("TunarrSync")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')

# Console handler only by default
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Add function to enable debug mode if needed
def enable_debug_logging():
    logger.setLevel(logging.DEBUG)
    # Add file handler only when debug is enabled
    file_handler = logging.FileHandler("tunarrsync.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Debug logging enabled with log file")

class PlexToTunarr:
    def __init__(self, plex_url, plex_token, library_name, table, tunarr_url, channel_number, channel_name=None):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.plex = PlexServer(plex_url, plex_token)
        self.library_name = library_name
        self.tunarr_url = tunarr_url.rstrip('/')
        self.channel_number = channel_number
        self.channel_name = channel_name or library_name
        self.table = table
        self.df = self.load_db_data()
        self.skip_reasons = {}  # Used to tally why items might be skipped if needed
        self.plex_source_info = self.get_plex_source_info()

    # ------------------------------------------------------------------
    # Helper: Log skip messages.
    # ------------------------------------------------------------------
    def log_skip(self, program_or_id, reason):
        if isinstance(program_or_id, dict):
            unique_id = program_or_id.get("uniqueId", "unknown")
        else:
            unique_id = str(program_or_id)
        if reason not in self.skip_reasons:
            self.skip_reasons[reason] = []
        self.skip_reasons[reason].append(unique_id)
        logger.debug("Skipping program %s (%s)", unique_id, reason)

    def show_skip_summary(self):
        if not self.skip_reasons:
            logger.info("No programs were skipped.")
            return
        logger.info("==== Skipped Programs Summary ====")
        total = 0
        for reason, items in self.skip_reasons.items():
            logger.info("  Reason '%s': %d programs", reason, len(items))
            total += len(items)
        logger.info("  Total skipped: %d", total)

    # ------------------------------------------------------------------
    # DB Loading: load the table containing file paths.
    # ------------------------------------------------------------------
    def load_db_data(self):
        for base in (
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            os.path.dirname(os.path.abspath(__file__))
        ):
            db_path = os.path.join(base, f"{config.network}.db")
            try:
                logger.debug("Attempting to connect to SQLite database at: %s", db_path)
                con = sqlite3.connect(db_path)
                df = pd.read_sql_query(f"SELECT * FROM {self.table}", con)
                logger.info("Loaded %d rows from table '%s'", len(df), self.table)
                return df
            except Exception as e:
                logger.error("Error connecting to database at %s: %s", db_path, e)
        logger.warning("No valid DB data found; using all Plex media.")
        return None

    def get_filename_from_path(self, path):
        return os.path.basename(path)

    # ------------------------------------------------------------------
    # Tunarr Channel Management Methods
    # ------------------------------------------------------------------
    def get_channel_by_number(self, channel_number):
        try:
            response = requests.get(f"{self.tunarr_url}/api/channels")
            if response.status_code == 200:
                channels = response.json()
                for channel in channels:
                    if channel.get("number") == channel_number:
                        return channel
            return None
        except Exception as e:
            logger.error("Error getting channel: %s", e)
            return None

    def create_channel(self, name, number):
        configs = self.get_transcode_configs()
        if not configs:
            logger.error("No transcode configs found.")
            return None
        channel_data = {
            "name": name,
            "number": number,
            "stealth": False,
            "duration": 0,
            "icon": {"path": "", "color": "#4338ca"},
            "groupTitle": name,
            "disableFillerOverlay": False,
            "transcodeConfigId": configs[0]["id"],
            "transcoding": {
                "targetResolution": "global",
                "videoBitrate": "global",
                "videoBufferSize": "global"
            },
            "startTime": 0,
            "fillerRepeatCooldown": 3600000,
            "id": "",
            "offline": {"picture": "", "soundtrack": "", "mode": "pic"},
            "streamMode": "mpegts",
            "guideMinimumDuration": 0
        }
        logger.debug("Creating channel with data: %s", channel_data)
        response = requests.post(f"{self.tunarr_url}/api/channels", json=channel_data)
        if response.status_code == 201:
            new_channel = response.json()
            logger.info("Channel '%s' created successfully.", new_channel.get("name"))
            return new_channel
        else:
            logger.error("Failed to create channel. Status code: %d", response.status_code)
            logger.error(response.text)
            return None

    def get_transcode_configs(self):
        try:
            response = requests.get(f"{self.tunarr_url}/api/transcode_configs")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error("Error getting transcode configs: %s", e)
            return []

    def delete_all_programs(self, channel_id):
        payload = {"type": "manual", "programs": [], "lineup": []}
        logger.debug("Deleting all programs from channel: %s", channel_id)
        url = f"{self.tunarr_url}/api/channels/{channel_id}/programming"
        response = requests.post(url, json=payload)
        return response.status_code == 200

    def get_plex_source_info(self):
        """
        Get Plex server information from Tunarr to obtain the externalSourceId
        """
        return {
            "id": self.get_plex_media_source_id(),
            "name": "Plex Server"
        }

    def get_plex_media_source_id(self):
        """Get the ID of the Plex media source in Tunarr"""
        try:
            response = requests.get(f"{self.tunarr_url}/api/media-sources")
            if response.status_code == 200:
                sources = response.json()
                # Print out all available media sources for debugging
                logger.debug(f"Available media sources: {json.dumps(sources, indent=2)}")
                
                # Look for a match with our Plex URL
                plex_host = self.plex_url.split('://')[1].split(':')[0]  # Extract host from URL
                
                for source in sources:
                    if source.get('type') == 'plex':
                        # Try to match by hostname
                        source_uri = source.get('uri', '')
                        if plex_host in source_uri:
                            logger.info(f"Found matching Plex source: {source.get('id')} - {source.get('name')}")
                            return source.get('id')
                
                # If no exact match found but there's at least one Plex source, use the first one
                plex_sources = [s for s in sources if s.get('type') == 'plex']
                if plex_sources:
                    logger.info(f"No exact match found. Using first available Plex source: {plex_sources[0].get('id')} - {plex_sources[0].get('name')}")
                    return plex_sources[0].get('id')
                
                # No Plex sources found, attempt to create one automatically
                logger.info(f"No Plex media source found in Tunarr. Attempting to create one automatically...")
                return self.create_plex_media_source()
            
            logger.error(f"Failed to get media sources. Status code: {response.status_code}")
            raise ValueError(f"Failed to get media sources from Tunarr: {response.text if hasattr(response, 'text') else ''}")
        except Exception as e:
            logger.error(f"Error getting media sources: {e}")
            raise ValueError(f"Error getting media sources: {e}")
    
    def create_plex_media_source(self):
        """Create a Plex media source in Tunarr if one doesn't exist"""
        try:
            logger.info(f"Creating a Plex media source for {self.plex_url}...")
            
            # Prepare the media source data according to InsertMediaSourceRequestSchema
            media_source_data = {
                "type": "plex",
                "name": "Plex Server",  # Default name that can be changed later
                "uri": self.plex_url,
                "accessToken": self.plex_token,
                "sendGuideUpdates": False,
                "sendChannelUpdates": False
            }
            
            response = requests.post(
                f"{self.tunarr_url}/api/media-sources",
                json=media_source_data
            )
            
            if response.status_code == 201:
                result = response.json()
                logger.info(f"Successfully created Plex media source with ID: {result.get('id')}")
                return result.get('id')
            else:
                logger.error(f"Failed to create Plex media source. Status code: {response.status_code}")
                logger.error(f"Response: {response.text if hasattr(response, 'text') else ''}")
                raise ValueError(f"Failed to create Plex media source: {response.text if hasattr(response, 'text') else ''}")
        except Exception as e:
            logger.error(f"Error creating Plex media source: {e}")
            raise ValueError(f"Error creating Plex media source: {e}")

    # ------------------------------------------------------------------
    # Build Full Program Object from Plex Metadata
    # ------------------------------------------------------------------
    def build_full_program(self, plex_item):
        """
        Build a complete program object that follows the expected final JSON schema.
        Fields like date, duration, serverFileKey, and serverFilePath are extracted
        directly from the Plex item.
        """
        try:
            rating_key = plex_item.ratingKey
            source_id = self.plex_source_info["id"]
            source_name = self.plex_source_info["name"]
            unique_id = f"plex|{source_name}|{rating_key}"
            if hasattr(plex_item, "originallyAvailableAt") and plex_item.originallyAvailableAt:
                date_str = plex_item.originallyAvailableAt.strftime("%Y-%m-%d")
            else:
                date_str = "1970-01-01"
            duration_ms = plex_item.duration or 0

            server_file_path = ""
            server_file_key = ""
            if plex_item.media and plex_item.media[0].parts:
                part = plex_item.media[0].parts[0]
                server_file_path = part.file
                server_file_key = part.key

            subtype = "movie"

            external_ids = [{
                "source": "plex",
                "id": str(rating_key),
                "sourceId": source_id,
                "type": "multi"
            }]
            if hasattr(plex_item, "guid") and plex_item.guid:
                external_ids.append({
                    "type": "single",
                    "source": "plex-guid",
                    "id": plex_item.guid
                })

            program = {
                "type": "content",
                "externalSourceType": "plex",
                "externalSourceId": source_id,
                "externalSourceName": source_name,
                "date": date_str,
                "duration": duration_ms,
                "serverFileKey": server_file_key,
                "serverFilePath": server_file_path,
                "externalKey": str(rating_key),
                "summary": getattr(plex_item, "summary", "") or "",
                "title": plex_item.title or "",
                "subtype": subtype,
                "persisted": False,
                "externalIds": external_ids,
                "uniqueId": unique_id,
                "id": unique_id,
                "originalIndex": 0,    # To be set later in payload builder.
                "startTimeOffset": 0   # To be set later.
            }
            return program
        except Exception as e:
            logger.error("Error building program for Plex item '%s': %s", plex_item.title, e)
            return None

    # ------------------------------------------------------------------
    # Build the JSON payload and POST to Tunarr (with duplicate handling)
    # ------------------------------------------------------------------
    def post_manual_lineup(self, channel_id, plex_items):
        programs = []         # Will contain full program records.
        lineup = []           # Will contain lineup entries that refer to an index in programs.
        cumulative_offset = 0
        first_occurrence_index = {}  # Maps ratingKey (as string) to index in programs.
        total_items = len(plex_items)

        for i, item in enumerate(plex_items):
            key = str(item.ratingKey)
            if key not in first_occurrence_index:
                # First occurrence: add full record.
                prog = self.build_full_program(item)
                if not prog:
                    continue
                prog["originalIndex"] = i
                prog["startTimeOffset"] = cumulative_offset
                current_prog_index = len(programs)
                programs.append(prog)
                first_occurrence_index[key] = current_prog_index
                lineup_prog_index = current_prog_index
            else:
                # Duplicate found.
                # If this duplicate is the very last item in the overall list, add a new duplicate record.
                if i == total_items - 1:
                    dup_prog = self.build_full_program(item)
                    if not dup_prog:
                        continue
                    # Mark duplicate record; override persisted flag.
                    dup_prog["persisted"] = False
                    # Set its uniqueId (using Plex's ratingKey as instructed).
                    dup_prog["uniqueId"] = f"plex|Plex Server|{key}"
                    dup_prog["id"] = dup_prog["uniqueId"]
                    dup_prog["originalIndex"] = i
                    dup_prog["startTimeOffset"] = cumulative_offset
                    current_prog_index = len(programs)
                    programs.append(dup_prog)
                    lineup_prog_index = current_prog_index
                else:
                    # For other duplicate occurrences, simply reference the first record.
                    lineup_prog_index = first_occurrence_index[key]

            # For each item, add to the lineup array.
            lineup.append({
                "duration": item.duration,
                "index": lineup_prog_index,
                "type": "index"
            })
            cumulative_offset += item.duration

        payload = {
            "type": "manual",
            "lineup": lineup,
            "programs": programs,
            "append": False
        }

        logger.debug("Final JSON payload to POST:\n%s", json.dumps(payload, indent=2))
        url = f"{self.tunarr_url}/api/channels/{channel_id}/programming"
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info("Programs added successfully!")
            return True
        else:
            logger.error("Failed to add programs. Status code: %d", response.status_code)
            logger.error(response.text)
            return False

    # ------------------------------------------------------------------
    # MAIN RUN LOGIC
    # ------------------------------------------------------------------
    def run(self):
        # Fetch all Plex media from the given library section.
        all_media = self.plex.library.section(self.library_name).all()
        logger.info("Found %d items in Plex library '%s'", len(all_media), self.library_name)

        # Filter Plex items based on the DB table (match file name)
        if self.df is not None and not self.df.empty and "FULL_FILE_PATH" in self.df.columns:
            media_dict = {}
            for item in all_media:
                if item.media and item.media[0].parts:
                    fname = self.get_filename_from_path(item.media[0].parts[0].file)
                    media_dict[fname] = item
            db_file_names = [self.get_filename_from_path(p) for p in self.df["FULL_FILE_PATH"].tolist()]
            filtered_media = []
            for fname in db_file_names:
                if fname in media_dict:
                    filtered_media.append(media_dict[fname])
            logger.info("Filtered down to %d items from DB data", len(filtered_media))
        else:
            filtered_media = all_media
            logger.info("Using all %d items from Plex library", len(filtered_media))

        # Create or find the Tunarr channel.
        channel = self.get_channel_by_number(self.channel_number)
        if not channel:
            logger.info("Channel number %d not found; creating.", self.channel_number)
            channel = self.create_channel(self.channel_name, self.channel_number)
            if not channel:
                logger.error("Failed to create channel. Exiting.")
                self.show_skip_summary()
                return False
        else:
            logger.info("Using existing channel: %s", channel.get("name"))

        channel_id = channel.get("uuid", channel.get("id"))
        if not channel_id:
            logger.error("Could not determine channel ID from channel object. Exiting.")
            self.show_skip_summary()
            return False

        # Clear the existing channel schedule.
        logger.info("Deleting old programs from channel %s", channel_id)
        if not self.delete_all_programs(channel_id):
            logger.error("Failed to delete old programs. Exiting.")
            self.show_skip_summary()
            return False

        # Build the final JSON payload from Plex items and POST it.
        logger.info("Posting new programs to channel %s", channel_id)
        success = self.post_manual_lineup(channel_id, filtered_media)
        if success:
            logger.info("Channel programming updated successfully!")
        else:
            logger.error("Failed to update channel programming.")
        self.show_skip_summary()
        return success