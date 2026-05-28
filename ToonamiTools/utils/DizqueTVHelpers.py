"""
DizqueTV Helper Functions

Utilities for creating DizqueTV-compatible data structures
"""

from typing import Union, Optional
from datetime import datetime


def create_program_dict_from_plex_item(
    plex_item,
    plex_server,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> dict:
    """
    Create a DizqueTV program dictionary from a PlexAPI item.

    Args:
        plex_item: PlexAPI Video, Movie, Episode, or Track object
        plex_server: PlexAPI PlexServer object
        start_time: Optional start time in milliseconds (for cutless mode)
        end_time: Optional end time in milliseconds (for cutless mode)

    Returns:
        Dictionary containing program data in DizqueTV format
    """
    # Get Plex server info
    plex_uri = plex_server.url("", includeToken=False)
    plex_token = plex_server._token

    # Determine item type
    item_type = plex_item.type.lower()  # 'episode', 'movie', 'track'

    # Get media file information
    try:
        plex_media_item_part = plex_item.media[0].parts[0]
    except (IndexError, AttributeError):
        raise ValueError(f"Could not find media parts for Plex item: {plex_item.title}")

    # Helper function to safely get date string
    def format_date(date_obj) -> str:
        if date_obj is None:
            return ""
        if isinstance(date_obj, datetime):
            return date_obj.strftime("%Y-%m-%d")
        return str(date_obj).split()[0]  # Remove time component if present

    # Helper function to get year from date
    def get_year(date_obj) -> str:
        if date_obj is None:
            return ""
        if isinstance(date_obj, datetime):
            return str(date_obj.year)
        date_str = str(date_obj)
        return date_str.split('-')[0] if '-' in date_str else date_str[:4]

    # Build base program dictionary
    program_data = {
        "title": plex_item.title,
        "key": plex_item.key,
        "ratingKey": str(plex_item.ratingKey),
        "icon": f"{plex_uri}{plex_item.thumb}?X-Plex-Token={plex_token}",
        "type": item_type,
        "duration": plex_item.duration,  # milliseconds
        "summary": getattr(plex_item, 'summary', ''),
        "rating": getattr(plex_item, 'contentRating', ''),
        "date": format_date(getattr(plex_item, 'originallyAvailableAt', None)),
        "year": get_year(getattr(plex_item, 'originallyAvailableAt', None)),
        "plexFile": plex_media_item_part.key,
        "file": plex_media_item_part.file,
        "serverKey": plex_server.friendlyName,
    }

    # Add episode-specific fields
    if item_type == "episode":
        program_data["showTitle"] = plex_item.grandparentTitle
        program_data["episode"] = int(plex_item.index)
        program_data["season"] = int(plex_item.parentIndex)
        program_data["episodeIcon"] = f"{plex_uri}{plex_item.thumb}?X-Plex-Token={plex_token}"
        program_data["seasonIcon"] = f"{plex_uri}{plex_item.parentThumb}?X-Plex-Token={plex_token}"
        program_data["showIcon"] = f"{plex_uri}{plex_item.grandparentThumb}?X-Plex-Token={plex_token}"

    # Add cutless mode timing parameters if provided
    if start_time is not None:
        program_data["seekPosition"] = start_time
    if end_time is not None:
        program_data["endPosition"] = end_time

    return program_data


def create_default_channel_settings(channel_number: int, channel_name: str) -> dict:
    """
    Create default channel settings for DizqueTV.

    Args:
        channel_number: Channel number
        channel_name: Channel name

    Returns:
        Dictionary containing default channel settings
    """
    return {
        "number": channel_number,
        "name": channel_name,
        "programs": [],
        "icon": "",
        "disableFillerOverlay": False,
        "startTime": 0,
        "offline": {
            "mode": "clip",
            "picture": "",
            "soundtrack": "",
            "timeslots": []
        },
        "fallback": [],
        "fillerCollections": [],
        "scheduleBackup": [],
        "transcoding": {
            "targetResolution": "1920x1080",
            "videoBitrate": 3000,
            "videoBufSize": 1000
        },
        "watermark": {
            "enabled": False,
            "width": 10,
            "verticalMargin": 1,
            "horizontalMargin": 1,
            "duration": 0,
            "fixedSize": False,
            "position": "bottom-right",
            "url": ""
        }
    }
