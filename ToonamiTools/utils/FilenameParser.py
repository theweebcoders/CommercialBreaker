"""
FilenameParser - Centralized Episode Filename Parsing Utility

This module provides consistent parsing of anime episode filenames across the
CommercialBreaker application. It handles standard episode naming patterns and
automatically strips release years in parentheses.

Supported Formats:
    - Standard: "Show Name - S01E28 - Description.mkv"
    - With Year: "Show Name (2002) - S01E28 - Description.mkv"
    - Minimal: "Show Name - S1E5.mkv"

The parser ensures consistent show name extraction across all modules including
ToonamiChecker, CommercialBreaker, BlockMaker, and platform integrations.
"""

import re
import os
from typing import Optional, Dict, Union


class FilenameParser:
    """
    Centralized parser for anime episode filenames.

    Handles extraction of show names, season/episode numbers, and descriptions
    from standardized filename patterns. Automatically strips release years
    from show names when present.
    """

    # Primary pattern: Matches show name with optional year, season/episode, and description
    # Group 1: Show name (everything before optional year and season marker)
    # Group 2: Optional year in parentheses (e.g., "(2002)")
    # Group 3: Season number (1-2 digits)
    # Group 4: Episode number (1-2 digits)
    # Group 5: Optional description after second dash
    _EPISODE_PATTERN = re.compile(
        r'^(.*?)\s*(?:\((\d{4})\))?\s*-\s*S(\d{1,2})E(\d{1,2})(?:\s*-\s*(.*))?',
        re.IGNORECASE
    )

    # Validation pattern: Check if filename contains episode marker
    _CONTAINS_EPISODE = re.compile(r'S\d{1,2}E\d{1,2}', re.IGNORECASE)

    @classmethod
    def parse_episode_filename(cls, filename: str) -> Optional[Dict[str, Union[str, int]]]:
        """
        Parse an episode filename into its components.

        Extracts show name, season, episode, and optional description from
        a filename. Automatically removes release years in parentheses from
        the show name.

        Args:
            filename: Episode filename (with or without path/extension)

        Returns:
            Dictionary with keys:
                - show_name: str - Show title without year
                - season: int - Season number
                - episode: int - Episode number
                - season_episode: str - Formatted as "S##E##" (zero-padded)
                - description: str or None - Optional episode description
                - original_filename: str - Original input filename
                - has_year: bool - Whether a year was found and removed
                - year: int or None - The release year if present

            Returns None if filename doesn't match expected pattern.

        Examples:
            >>> FilenameParser.parse_episode_filename("Naruto - S01E28 - Description.mkv")
            {
                'show_name': 'Naruto',
                'season': 1,
                'episode': 28,
                'season_episode': 'S01E28',
                'description': 'Description',
                'original_filename': 'Naruto - S01E28 - Description.mkv',
                'has_year': False,
                'year': None
            }

            >>> FilenameParser.parse_episode_filename("Naruto (2002) - S01E28 - Description.mkv")
            {
                'show_name': 'Naruto',
                'season': 1,
                'episode': 28,
                'season_episode': 'S01E28',
                'description': 'Description',
                'original_filename': 'Naruto (2002) - S01E28 - Description.mkv',
                'has_year': True,
                'year': 2002
            }
        """
        # Remove path and extension if present
        base_filename = os.path.splitext(os.path.basename(filename))[0]

        # Attempt to match the pattern
        match = cls._EPISODE_PATTERN.match(base_filename)

        if not match:
            return None

        show_name = match.group(1).strip()
        year_str = match.group(2)  # Will be None if no year present
        season_str = match.group(3)
        episode_str = match.group(4)
        description = match.group(5).strip() if match.group(5) else None

        # Convert to integers
        season = int(season_str)
        episode = int(episode_str)
        year = int(year_str) if year_str else None

        # Format season/episode with zero padding
        season_episode = f"S{season:02d}E{episode:02d}"

        return {
            'show_name': show_name,
            'season': season,
            'episode': episode,
            'season_episode': season_episode,
            'description': description,
            'original_filename': filename,
            'has_year': year is not None,
            'year': year
        }

    @classmethod
    def extract_show_name(cls, filename: str) -> Optional[str]:
        """
        Extract just the show name from a filename.

        Convenience method that extracts only the show name, automatically
        stripping any release year in parentheses.

        Args:
            filename: Episode filename

        Returns:
            Show name without year, or None if parsing fails

        Examples:
            >>> FilenameParser.extract_show_name("Naruto - S01E28.mkv")
            'Naruto'

            >>> FilenameParser.extract_show_name("Naruto (2002) - S01E28.mkv")
            'Naruto'
        """
        parsed = cls.parse_episode_filename(filename)
        return parsed['show_name'] if parsed else None

    @classmethod
    def extract_season_episode(cls, filename: str) -> Optional[str]:
        """
        Extract the season/episode identifier from a filename.

        Args:
            filename: Episode filename

        Returns:
            Season/episode string formatted as "S##E##", or None if parsing fails

        Examples:
            >>> FilenameParser.extract_season_episode("Naruto - S1E5.mkv")
            'S01E05'
        """
        parsed = cls.parse_episode_filename(filename)
        return parsed['season_episode'] if parsed else None

    @classmethod
    def contains_episode_pattern(cls, filename: str) -> bool:
        """
        Check if a filename contains an episode pattern.

        Useful for distinguishing episode files from other media types
        (e.g., bump files, movies, etc.)

        Args:
            filename: Filename to check

        Returns:
            True if filename contains S##E## pattern, False otherwise

        Examples:
            >>> FilenameParser.contains_episode_pattern("Naruto - S01E28.mkv")
            True

            >>> FilenameParser.contains_episode_pattern("Toonami 2 0 Bump.mp4")
            False
        """
        return cls._CONTAINS_EPISODE.search(filename) is not None

    @classmethod
    def strip_year_from_show_name(cls, show_name: str) -> str:
        """
        Strip release year in parentheses from a show name.

        Utility method to clean show names that may already have been
        partially processed. Removes years like "(2002)" from the end
        of show names.

        Args:
            show_name: Show name that may contain a year

        Returns:
            Show name with year removed and trimmed

        Examples:
            >>> FilenameParser.strip_year_from_show_name("Naruto (2002)")
            'Naruto'

            >>> FilenameParser.strip_year_from_show_name("Naruto")
            'Naruto'
        """
        # Pattern to match year at the end: optional whitespace, year in parens
        year_pattern = re.compile(r'\s*\(\d{4}\)\s*$')
        return year_pattern.sub('', show_name).strip()

    @classmethod
    def validate_filename(cls, filename: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a filename matches expected episode format.

        Args:
            filename: Filename to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if filename is properly formatted
            - error_message: None if valid, otherwise description of issue

        Examples:
            >>> FilenameParser.validate_filename("Naruto - S01E28.mkv")
            (True, None)

            >>> FilenameParser.validate_filename("InvalidFormat.mkv")
            (False, "Filename does not match episode pattern")
        """
        parsed = cls.parse_episode_filename(filename)

        if not parsed:
            return False, "Filename does not match episode pattern: [SHOW_NAME] (YEAR) - S##E## - Description"

        # Additional validations
        if parsed['season'] < 1:
            return False, "Season number must be at least 1"

        if parsed['episode'] < 1:
            return False, "Episode number must be at least 1"

        if not parsed['show_name']:
            return False, "Show name cannot be empty"

        return True, None


# Convenience function for backward compatibility
def parse_episode_filename(filename: str) -> Optional[Dict[str, Union[str, int]]]:
    """
    Parse episode filename. Convenience function wrapper.

    See FilenameParser.parse_episode_filename() for details.
    """
    return FilenameParser.parse_episode_filename(filename)
