"""
Factory Floor - Stores channels and generates all output files.

Three machines:
1. Channel Storage - Persists channel data to disk
2. Playlist Generator - Creates M3U and XMLTV files
3. File Manager - Handles disk operations

Input: Processed channel data from Loading Dock
Output: Generated playlists and guides (accessed via UnloadingDock wrapper)

NOTE: FactoryFloor does the work - UnloadingDock just hands it to clients.
"""

import json
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import config
from ..utilities import resolve_storage_path
from ToonamiTools.utils.FilenameParser import FilenameParser


class FactoryFloor:
    """Stores channel data (INTERNAL USE - accessed only by LoadingDock and UnloadingDock)."""

    def __init__(self, base_url: str, storage_path=None, segment_root=None, break_renderer=None, loading_dock=None):
        self.base_url = base_url
        self.channels: Dict[str, dict] = {}  # Channel data by number
        self._lock = threading.Lock()
        self.cleanup_manager = None
        # Back-reference to the LoadingDock that owns us — used by the
        # infinite-channel LineupExtender, which needs LoadingDock's
        # format_extension method to anchor new programs to the existing
        # timeline. None when running headless (e.g., tests).
        self.loading_dock = loading_dock
        # Per-channel LineupExtender instances (one per infinite channel).
        # Each one wraps a ``threading.Timer`` scheduled for the channel's
        # next end-of-runway. Keyed by channel-number string. Spawned lazily
        # by ``_maybe_spawn_extender`` during ``store_channel`` and
        # ``_load_channels``.
        self._extenders: Dict[str, object] = {}

        # Set up storage
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = resolve_storage_path()

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_channels()

        # Start cleanup manager if we have segment_root
        if segment_root:
            from ..utilities import CleanupManager
            self.cleanup_manager = CleanupManager(segment_root, break_renderer)
            self.cleanup_manager.start_cleanup_thread(
                segment_max_age_minutes=15,
                break_max_age_hours=4,
                cleanup_interval_minutes=5
            )

        # Spawn watchdogs for any infinite channels recovered from disk.
        # Happens after _load_channels has run so the channel dicts already
        # exist in self.channels.
        for channel_data in self.channels.values():
            self._maybe_spawn_extender(channel_data)

        print(f"[FACTORY_FLOOR] Ready with storage: {self.storage_path}")

    def store_channel(self, channel_data):
        """Channel Storage Machine - Store processed channel data."""
        channel_number = channel_data['number']
        print(f"[FACTORY_FLOOR] Storing channel {channel_number}")

        with self._lock:
            self.channels[str(channel_number)] = channel_data
            self._save_channels()

        print(f"[FACTORY_FLOOR] Channel {channel_number} stored with {len(channel_data['programs'])} programs")

        # If this is an infinite channel, spawn the LineupExtender watchdog.
        # Done outside the lock so the new thread can immediately take the
        # lock if needed (e.g., for its initial extend_channel call).
        self._maybe_spawn_extender(channel_data)

        return channel_number

    def _maybe_spawn_extender(self, channel_data):
        """Spawn a LineupExtender watchdog for ``channel_data`` if eligible.

        Eligibility: the channel must have ``_infinite_meta.enabled`` truthy
        and the FactoryFloor must have a LoadingDock back-reference. Idempotent
        — if a live watchdog already exists for the channel, this is a no-op.
        """
        meta = channel_data.get('_infinite_meta') or {}
        if not meta.get('enabled'):
            return
        if self.loading_dock is None:
            print(
                f"[FACTORY_FLOOR] Cannot spawn LineupExtender for channel "
                f"{channel_data.get('number')} — no LoadingDock reference"
            )
            return

        channel_key = str(channel_data['number'])
        existing = self._extenders.get(channel_key)
        if existing is not None and existing.is_active():
            return

        # Local import to avoid an import-time cycle between FactoryFloor
        # and LineupExtender via LoadingDock.
        from .LineupExtender import LineupExtender

        # Pass the FactoryFloor itself (not the LoadingDock) — at this point
        # we may be executing inside FactoryFloor.__init__ which was called
        # from LoadingDock.__init__'s ``self.factory_floor = FactoryFloor(...)``
        # assignment, so ``self.loading_dock.factory_floor`` does not yet
        # exist as an attribute. LineupExtender reads loading_dock lazily
        # off the FactoryFloor when its timer actually fires, by which time
        # LoadingDock has finished constructing.
        extender = LineupExtender(self, channel_data['number'])
        self._extenders[channel_key] = extender
        extender.start()
        print(
            f"[FACTORY_FLOOR] Armed LineupExtender for channel "
            f"{channel_data['number']}"
        )

    def extend_channel(self, channel_number, new_programs):
        """Append additional programs to an existing channel's lineup.

        Used by the infinite-channel LineupExtender to top up a running
        channel without disturbing the Studio thread that's reading the
        same ``programs`` list. The list is append-only by contract — never
        replace ``channel_data['programs']`` with a new list, and never
        reorder or remove entries; Studio's ``programs[current_index % len]``
        only stays coherent under that invariant.

        Returns the new total program count, or ``None`` if the channel is
        unknown.
        """
        if not new_programs:
            return None

        channel_key = str(channel_number)

        with self._lock:
            channel_data = self.channels.get(channel_key)
            if channel_data is None:
                print(f"[FACTORY_FLOOR] Cannot extend missing channel {channel_number}")
                return None

            programs = channel_data.setdefault('programs', [])
            programs.extend(new_programs)
            new_length = len(programs)

            meta = channel_data.setdefault('_infinite_meta', {})
            meta['extension_seq'] = int(meta.get('extension_seq') or 0) + 1
            meta['last_extension_at'] = datetime.now(timezone.utc).isoformat()
            meta['consecutive_failures'] = 0  # reset on successful extend

            self._save_channels()

        print(
            f"[FACTORY_FLOOR] Extended channel {channel_number} by "
            f"{len(new_programs)} programs (now {new_length} total)"
        )
        return new_length

    def get_channel(self, channel_number):
        """Get channel data (used internally by UnloadingDock)."""
        return self.channels.get(str(channel_number))

    def generate_playlist(self, external_url=None):
        """Playlist Generator Machine - Create M3U playlist."""
        print(f"[FACTORY_FLOOR] Generating M3U playlist for {len(self.channels)} channels")

        # Use external URL if provided, otherwise fall back to base_url
        playlist_url = external_url or self.base_url

        # M3U header
        lines = [f'#EXTM3U url-tvg="{playlist_url}/api/xmltv.xml"']

        # Filter valid channels and add each one
        for channel in sorted(self.channels.values(), key=lambda c: c.get('number', 0)):
            if not self._is_valid_channel(channel):
                continue

            channel_num = channel.get('number', 'Unknown')
            channel_name = channel.get('name', 'Unknown Channel')

            lines.append(
                f'#EXTINF:0 tvg-id="{channel_num}" tvg-chno="{channel_num}" '
                f'tvg-name="{channel_name}" group-title="ComBreakDirect",{channel_name}'
            )
            lines.append(f"{playlist_url}/channel{channel_num}.m3u8")

        return '\n'.join(lines)

    def generate_xmltv(self):
        """Playlist Generator Machine - Create XMLTV guide."""
        print(f"[FACTORY_FLOOR] Generating XMLTV guide for {len(self.channels)} channels")

        # Create XML structure
        tv = ET.Element('tv')
        tv.set('generator-info-name', 'ComBreakDirect')

        # Filter valid channels
        valid_channels = [ch for ch in self.channels.values() if self._is_valid_channel(ch)]

        # Add channels
        for channel in sorted(valid_channels, key=lambda c: c.get('number', 0)):
            self._add_channel_to_xmltv(tv, channel)

        # Add programs
        for channel in sorted(valid_channels, key=lambda c: c.get('number', 0)):
            self._add_programs_to_xmltv(tv, channel)

        return self._xml_to_string(tv)

    def generate_lineup_json(self, request_host: str) -> list:
        """Generate HDHomeRun lineup from stored channels."""
        channels = []
        for channel_data in self.channels.values():
            if self._is_valid_channel(channel_data):
                channel_num = channel_data.get('number', 1)
                channels.append({
                    "GuideNumber": str(channel_data.get('number', '1')),
                    "GuideName": channel_data.get('name', 'Unknown'),
                    "URL": f"http://{request_host}/video/channel/{channel_num}"
                })
        return channels

    def _is_valid_channel(self, channel):
        """Check if channel has proper structure."""
        required_keys = ['number', 'name', 'programs']
        return all(key in channel for key in required_keys)

    def _add_channel_to_xmltv(self, parent, channel):
        """Add channel element to XMLTV."""
        channel_elem = ET.SubElement(parent, 'channel')
        channel_elem.set('id', str(channel.get('number', 'Unknown')))

        display_name = ET.SubElement(channel_elem, 'display-name')
        display_name.set('lang', 'en')
        display_name.text = channel.get('name')

    def _add_programs_to_xmltv(self, parent, channel):
        """Add program elements to XMLTV - grouped by BLOCK_ID."""
        consolidated_programs = self._consolidate_programs_by_block_id(channel['programs'])

        for program_block in consolidated_programs:
            if not program_block.get('start') or not program_block.get('stop'):
                continue

            programme = ET.SubElement(parent, 'programme')
            programme.set('start', self._to_xmltv_time(program_block['start']))
            programme.set('stop', self._to_xmltv_time(program_block['stop']))
            programme.set('channel', str(channel.get('number', 'Unknown')))

            # Main title
            title = ET.SubElement(programme, 'title')
            title.set('lang', 'en')
            title.text = program_block['title']

            # Sub-title (episode title if available)
            if program_block.get('episode_title'):
                sub_title = ET.SubElement(programme, 'sub-title')
                sub_title.set('lang', 'en')
                sub_title.text = program_block['episode_title']

            # Description
            desc = ET.SubElement(programme, 'desc')
            desc.set('lang', 'en')
            if program_block.get('season') and program_block.get('episode'):
                desc.text = f"{program_block['title']} - Season {program_block['season']}, Episode {program_block['episode']}"
                if program_block.get('episode_title'):
                    desc.text += f": {program_block['episode_title']}"
            else:
                desc.text = f"{channel.get('name')} - {program_block['title']}"

            # Season/Episode metadata for Plex
            if program_block.get('season') and program_block.get('episode'):
                episode_num = ET.SubElement(programme, 'episode-num')
                episode_num.set('system', 'onscreen')
                episode_num.text = f"S{program_block['season']:02d}E{program_block['episode']:02d}"

                # Alternative format for better compatibility
                episode_num_xmltv = ET.SubElement(programme, 'episode-num')
                episode_num_xmltv.set('system', 'xmltv_ns')
                # XMLTV format: season.episode.part (all zero-indexed)
                episode_num_xmltv.text = f"{program_block['season']-1}.{program_block['episode']-1}.0/1"

            # Category for Plex recognition
            category = ET.SubElement(programme, 'category')
            category.set('lang', 'en')
            category.text = 'Animation'

    def _consolidate_programs_by_block_id(self, programs):
        """Consolidate programs by BLOCK_ID and extract show metadata from file paths."""
        import re

        if not programs:
            return []

        consolidated = []
        current_block = None
        current_block_title = None

        for program in programs:
            program_block_id = program.get('block_id', 'Unknown')
            file_path = program.get('file', '')

            # Group by BLOCK_ID - bumps/commercials should inherit BLOCK_ID from surrounding show
            if current_block_title != program_block_id and not self._is_bump_or_commercial_by_path(file_path):
                # Save previous block if exists
                if current_block is not None:
                    current_block['stop'] = program.get('start', current_block['stop'])
                    consolidated.append(current_block)

                # Find show metadata within this BLOCK_ID group
                show_metadata = self._extract_show_metadata_from_block_id(programs, program_block_id)

                # Start new block with proper show metadata
                current_block = {
                    'title': show_metadata['show_name'],
                    'season': show_metadata['season'],
                    'episode': show_metadata['episode'],
                    'episode_title': show_metadata['episode_title'],
                    'start': program.get('start'),
                    'stop': program.get('stop')
                }
                current_block_title = program_block_id
            else:
                # Extend current block
                if current_block is not None:
                    current_block['stop'] = program.get('stop', current_block['stop'])

        # Add final block
        if current_block is not None:
            consolidated.append(current_block)

        return consolidated

    def _extract_show_metadata_from_block_id(self, programs, block_id):
        """Extract show metadata from file paths within a BLOCK_ID group using centralized parser."""
        # Find an anime file within this BLOCK_ID (not bumps/commercials)
        for program in programs:
            if program.get('block_id') != block_id:
                continue

            file_path = program.get('file', '')
            if not file_path:
                continue

            # Check if this is anime (has at least one of start_time or end_time, not both null)
            seek_pos = program.get('seekPosition')
            end_pos = program.get('endPosition')
            if seek_pos is None and end_pos is None:
                continue  # This is not anime (both are null)

            # Extract metadata from file path
            filename = file_path.split('/')[-1]  # Get filename after last slash

            # Use centralized parser (handles years in parentheses automatically)
            parsed = FilenameParser.parse_episode_filename(filename)
            if parsed:
                # Clean episode title by removing quality terms at the end
                episode_title = self._clean_episode_title(parsed.get('description', ''))

                return {
                    'show_name': parsed['show_name'],
                    'season': parsed['season'],
                    'episode': parsed['episode'],
                    'episode_title': episode_title
                }

        # Fallback if no anime found in this block
        return {
            'show_name': block_id.replace('_', ' ').title(),
            'season': None,
            'episode': None,
            'episode_title': None
        }

    @staticmethod
    def _is_bump_or_commercial_by_path(file_path):
        """Check if this is a bump or commercial based on file path."""
        if not file_path:
            return True  # No file path suggests it's not anime content

        path_lower = file_path.lower()
        return ('/bump/' in path_lower or
                '/commercial' in path_lower or
                'commercial' in path_lower)

    def _clean_episode_title(self, episode_title):
        """Remove video quality terms that appear at the very end of episode titles."""
        import re

        if not episode_title:
            return episode_title

        cleaned_title = episode_title

        # Get quality terms from config
        quality_terms = getattr(config, 'VIDEO_QUALITY_TERMS', [])
        if not quality_terms:
            return cleaned_title

        # Create pattern for quality terms - match them at the end with separators
        quality_pattern = '|'.join(re.escape(term) for term in quality_terms)

        # Match pattern: (space/dash/dot) + quality_term + (optional additional quality terms) + end of string
        pattern = r'[\s\-\.]+(?:' + quality_pattern + r')(?:[\s\-\.]*(?:' + quality_pattern + r'))*$'

        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE).strip()

        return cleaned_title

    @staticmethod
    def _to_xmltv_time(iso_time):
        """Convert ISO time to XMLTV format."""
        return iso_time[:19].replace('-', '').replace('T', '').replace(':', '') + ' +0000'

    @staticmethod
    def _xml_to_string(element):
        """Convert XML to formatted string."""
        from xml.dom import minidom
        rough = ET.tostring(element, 'unicode')
        reparsed = minidom.parseString(rough)
        return reparsed.toprettyxml(indent='  ')

    def _load_channels(self):
        """File Manager Machine - Load channels from disk."""
        if not self.storage_path.exists():
            return

        try:
            with self.storage_path.open('r') as f:
                data = json.load(f)
                self.channels = data.get('channels', {})
            print(f"[FACTORY_FLOOR] Loaded {len(self.channels)} channels from disk")
        except Exception as e:
            print(f"[FACTORY_FLOOR] Error loading channels: {e}")

    def _save_channels(self):
        """File Manager Machine - Save channels to disk."""
        try:
            # Strip ephemeral _runtime keys (e.g., Studio's current_index)
            # before persisting — Studio re-derives position from UTC time
            # on restart, so the on-disk value would be stale and misleading.
            sanitized = {
                key: {k: v for k, v in chan.items() if k != '_runtime'}
                for key, chan in self.channels.items()
            }
            data = {
                'version': 1,
                'channels': sanitized
            }

            # Atomic write
            tmp_path = self.storage_path.with_suffix('.tmp')
            with tmp_path.open('w') as f:
                json.dump(data, f, indent=2)
            tmp_path.replace(self.storage_path)

        except Exception as e:
            print(f"[FACTORY_FLOOR] Error saving channels: {e}")

    def get_status(self):
        """Get factory status."""
        return {
            'channels': len(self.channels),
            'storage_path': str(self.storage_path)
        }
