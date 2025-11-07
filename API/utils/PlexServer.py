"""
PlexServer - Minimal Plex Media Server client implementation.

Components:
- SimplePlexServer: Main server connection and API operations
- SimplePlexLibrary: Library section management
- SimplePlexSection: Individual library section operations
- SimplePlexShow: TV show/movie objects
- SimplePlexEpisode: Episode objects with media file access
- SimplePlexMedia/SimplePlexPart: Media file metadata
"""

from typing import List, Optional, Dict, Any
from API.utils.NetworkUtils import CurlHttpClient, RequestException, Timeout, ConnectionError as NetConnectionError


class PlexServerError(Exception):
    """Exception raised for Plex server errors."""
    pass


class SimplePlexServer:
    """
    Minimal Plex Media Server client.

    Provides basic server operations including library access and item fetching.
    Uses JSON API instead of XML for simpler parsing.
    """

    def __init__(self, baseurl: str, token: str):
        """
        Initialize Plex server connection.

        Args:
            baseurl: Base URL of the Plex server (e.g., http://192.168.1.100:32400)
            token: Authentication token
        """
        self._baseurl = baseurl.rstrip('/')
        self._token = token
        self._library = None  # Lazy-loaded library

    @property
    def baseurl(self) -> str:
        """Get the base URL of the server."""
        return self._baseurl

    @property
    def library(self) -> 'SimplePlexLibrary':
        """Get the library object (lazy-loaded)."""
        if self._library is None:
            self._library = SimplePlexLibrary(self)
        return self._library

    @property
    def friendlyName(self) -> str:
        """
        Get the friendly name of the Plex server.

        Returns a default value since we don't store server metadata.
        For full compatibility, we'd need to query /identity endpoint.
        """
        return "Plex Server"

    def url(self, path: str = "", includeToken: bool = True) -> str:
        """
        Construct a full URL to the Plex server.

        Args:
            path: Path to append to base URL (default: empty string)
            includeToken: Whether to include the auth token as query parameter

        Returns:
            Full URL string
        """
        # Build base URL with path
        if path:
            full_url = f"{self._baseurl}{path}" if path.startswith('/') else f"{self._baseurl}/{path}"
        else:
            full_url = self._baseurl

        # Add token if requested
        if includeToken:
            separator = '&' if '?' in full_url else '?'
            full_url = f"{full_url}{separator}X-Plex-Token={self._token}"

        return full_url

    def query(self, key: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Query the Plex server API.

        Args:
            key: API endpoint path (e.g., '/library/sections')
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            PlexServerError: If the request fails
        """
        url = f"{self._baseurl}{key}"
        headers = {
            'X-Plex-Token': self._token,
            'Accept': 'application/json'
        }

        try:
            response = CurlHttpClient.get(url, headers=headers, timeout=timeout)

            if response.status_code == 401:
                raise PlexServerError("Unauthorized - invalid Plex token")
            elif response.status_code == 404:
                raise PlexServerError(f"Not found: {key}")
            elif response.status_code != 200:
                raise PlexServerError(f"Plex API error: HTTP {response.status_code}")

            return response.json()

        except (RequestException, NetConnectionError, Timeout) as e:
            raise PlexServerError(f"Network error querying Plex server: {e}")
        except ValueError as e:
            raise PlexServerError(f"Failed to parse JSON response: {e}")

    def fetchItem(self, key: str) -> 'SimplePlexEpisode':
        """
        Fetch a single item by its Plex key.

        Args:
            key: Plex item key (e.g., '/library/metadata/12345')

        Returns:
            SimplePlexEpisode or similar object

        Raises:
            PlexServerError: If the item cannot be fetched
        """
        data = self.query(key)

        # The response contains MediaContainer with Metadata array
        metadata_list = data.get('MediaContainer', {}).get('Metadata', [])
        if not metadata_list:
            raise PlexServerError(f"No metadata found for key: {key}")

        # Return the first item
        item_data = metadata_list[0]
        item_type = item_data.get('type')

        if item_type == 'episode':
            return SimplePlexEpisode(self, item_data)
        elif item_type == 'movie':
            return SimplePlexShow(self, item_data)
        else:
            # Generic item
            return SimplePlexShow(self, item_data)


class SimplePlexLibrary:
    """
    Plex library manager.

    Provides access to library sections and search functionality.
    """

    def __init__(self, server: SimplePlexServer):
        """
        Initialize library.

        Args:
            server: Parent SimplePlexServer instance
        """
        self._server = server
        self._sections_cache = None

    def sections(self) -> List['SimplePlexSection']:
        """
        Get all library sections.

        Returns:
            List of SimplePlexSection objects

        Raises:
            PlexServerError: If sections cannot be fetched
        """
        if self._sections_cache is None:
            data = self._server.query('/library/sections')
            directories = data.get('MediaContainer', {}).get('Directory', [])
            self._sections_cache = [SimplePlexSection(self._server, section) for section in directories]

        return self._sections_cache

    def section(self, title: str) -> 'SimplePlexSection':
        """
        Get a library section by title.

        Args:
            title: Section title (case-insensitive)

        Returns:
            SimplePlexSection object

        Raises:
            PlexServerError: If section is not found
        """
        sections = self.sections()
        title_lower = title.lower()

        for section in sections:
            if section.title.lower() == title_lower:
                return section

        raise PlexServerError(f"Library section not found: {title}")


class SimplePlexSection:
    """
    Plex library section (e.g., TV Shows, Movies, Anime).

    Provides access to items within the section.
    """

    def __init__(self, server: SimplePlexServer, data: Dict[str, Any]):
        """
        Initialize section from JSON data.

        Args:
            server: Parent SimplePlexServer instance
            data: Section metadata from API
        """
        self._server = server
        self.title = data.get('title', '')
        self.key = data.get('key', '')
        self.type = data.get('type', '')  # 'movie' or 'show'
        self.uuid = data.get('uuid', '')

    def all(self) -> List['SimplePlexShow']:
        """
        Get all items in this section.

        Returns:
            List of SimplePlexShow objects

        Raises:
            PlexServerError: If items cannot be fetched
        """
        data = self._server.query(f'/library/sections/{self.key}/all')
        metadata_list = data.get('MediaContainer', {}).get('Metadata', [])

        items = []
        for item_data in metadata_list:
            # Determine if this is a show or movie based on type
            item_type = item_data.get('type')
            if item_type in ('show', 'movie'):
                items.append(SimplePlexShow(self._server, item_data))
            else:
                # Could be an episode or other type - wrap it generically
                items.append(SimplePlexShow(self._server, item_data))

        return items

    def get(self, title: str) -> 'SimplePlexShow':
        """
        Get a show/movie by exact title match.

        Args:
            title: Show/movie title

        Returns:
            SimplePlexShow object

        Raises:
            PlexServerError: If item is not found
        """
        items = self.all()
        for item in items:
            if item.title == title:
                return item

        raise PlexServerError(f"Item not found in section: {title}")


class SimplePlexShow:
    """
    Plex TV show or movie object.

    Provides access to episodes and metadata.
    """

    def __init__(self, server: SimplePlexServer, data: Dict[str, Any]):
        """
        Initialize show/movie from JSON data.

        Args:
            server: Parent SimplePlexServer instance
            data: Show/movie metadata from API
        """
        self._server = server
        self.title = data.get('title', '')
        self.ratingKey = data.get('ratingKey', '')
        self.key = data.get('key', '')
        self.type = data.get('type', '')
        self.guid = data.get('guid', '')
        self.summary = data.get('summary', '')
        self.duration = data.get('duration')  # in milliseconds
        self.originallyAvailableAt = data.get('originallyAvailableAt')
        self.thumb = data.get('thumb', '')  # Thumbnail/poster image path

        # Parse media if this is a movie/video
        media_list = data.get('Media', [])
        self.media = [SimplePlexMedia(m) for m in media_list] if media_list else []

    def episodes(self) -> List['SimplePlexEpisode']:
        """
        Get all episodes for this show.

        Returns:
            List of SimplePlexEpisode objects

        Raises:
            PlexServerError: If episodes cannot be fetched
        """
        # Use ratingKey to construct the correct path to get seasons
        # The show's 'key' field may already include /children, so use ratingKey instead
        data = self._server.query(f'/library/metadata/{self.ratingKey}/children')
        metadata_list = data.get('MediaContainer', {}).get('Metadata', [])

        all_episodes = []
        for item in metadata_list:
            item_type = item.get('type')
            if item_type == 'season':
                # This is a season, fetch its episodes using ratingKey
                season_rating_key = item.get('ratingKey', '')
                if season_rating_key:
                    # Query the season's metadata directly using its ratingKey
                    season_data = self._server.query(f'/library/metadata/{season_rating_key}/children')
                    season_episodes = season_data.get('MediaContainer', {}).get('Metadata', [])
                    all_episodes.extend([SimplePlexEpisode(self._server, ep) for ep in season_episodes])
            elif item_type == 'episode':
                # Direct episode (rare but possible)
                all_episodes.append(SimplePlexEpisode(self._server, item))

        return all_episodes

    def episode(self, season: int, episode: int) -> 'SimplePlexEpisode':
        """
        Get a specific episode by season and episode number.

        Args:
            season: Season number
            episode: Episode number

        Returns:
            SimplePlexEpisode object

        Raises:
            PlexServerError: If episode is not found
        """
        episodes = self.episodes()

        for ep in episodes:
            if ep.parentIndex == season and ep.index == episode:
                return ep

        raise PlexServerError(f"Episode not found: S{season:02d}E{episode:02d}")


class SimplePlexEpisode:
    """
    Plex episode object.

    Provides access to episode metadata and media files.
    """

    def __init__(self, server: SimplePlexServer, data: Dict[str, Any]):
        """
        Initialize episode from JSON data.

        Args:
            server: Parent SimplePlexServer instance
            data: Episode metadata from API
        """
        self._server = server
        self.title = data.get('title', '')
        self.ratingKey = data.get('ratingKey', '')
        self.key = data.get('key', '')
        self.type = data.get('type', 'episode')
        self.guid = data.get('guid', '')
        self.summary = data.get('summary', '')
        self.index = data.get('index')  # Episode number
        self.parentIndex = data.get('parentIndex')  # Season number
        self.duration = data.get('duration')  # in milliseconds
        self.originallyAvailableAt = data.get('originallyAvailableAt')
        self.thumb = data.get('thumb', '')  # Episode thumbnail/poster image path
        self.parentThumb = data.get('parentThumb', '')  # Season thumbnail
        self.grandparentThumb = data.get('grandparentThumb', '')  # Show thumbnail
        self.grandparentTitle = data.get('grandparentTitle', '')  # Show title

        # Parse media
        media_list = data.get('Media', [])
        self.media = [SimplePlexMedia(m) for m in media_list]

        # Parse markers (intro/outro)
        self.markers = self._parse_markers(data.get('Marker', []))

    def _parse_markers(self, marker_data: List[Dict[str, Any]]) -> List['SimplePlexMarker']:
        """
        Parse intro/outro markers from episode data.

        Args:
            marker_data: List of marker dictionaries

        Returns:
            List of SimplePlexMarker objects with type, start, and end times
        """
        return [SimplePlexMarker(marker) for marker in marker_data]


class SimplePlexMarker:
    """
    Plex marker object for intro/outro timestamps.

    Wraps marker data to provide attribute-style access.
    """

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize marker from JSON data.

        Args:
            data: Marker metadata from API
        """
        self.type = data.get('type', '')  # 'intro', 'credits', etc.
        self.start = data.get('startTimeOffset')  # in milliseconds
        self.end = data.get('endTimeOffset')  # in milliseconds


class SimplePlexMedia:
    """
    Plex media wrapper.

    Contains media file parts and technical details.
    """

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize media from JSON data.

        Args:
            data: Media metadata from API
        """
        self.videoCodec = data.get('videoCodec', '')
        self.audioCodec = data.get('audioCodec', '')
        self.container = data.get('container', '')
        self.duration = data.get('duration')  # in milliseconds
        self.bitrate = data.get('bitrate')
        self.width = data.get('width')
        self.height = data.get('height')

        # Parse parts
        parts_list = data.get('Part', [])
        self.parts = [SimplePlexPart(p) for p in parts_list]


class SimplePlexPart:
    """
    Plex media part.

    Represents an actual media file on disk.
    """

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize part from JSON data.

        Args:
            data: Part metadata from API
        """
        self.file = data.get('file', '')  # Full file path
        self.key = data.get('key', '')  # Plex API key
        self.size = data.get('size', 0)
        self.duration = data.get('duration')  # in milliseconds
        self.container = data.get('container', '')
