"""
Loading Dock - Where cutless data comes in and gets processed for streaming.

Two machines:
1. Commercial Injector - Adds commercials between consecutive bumps
2. Data Formatter - Converts to streaming format

Input: Raw cutless lineup data from client
Output: Streaming-ready channel data (stored in FactoryFloor)

NOTE: LoadingDock creates the FactoryFloor - server doesn't need to know about it!
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..utilities import CommercialBreakRenderer


class LoadingDock:
    """Processes incoming cutless data into streaming-ready format."""

    def __init__(self, commercial_folder: str, base_url: str, storage_path=None, segment_root=None):
        from pathlib import Path
        from .FactoryFloor import FactoryFloor

        self._commercial_cache = {}
        self._pending_breaks = []

        # Configure commercials first to get break_renderer
        self._configure_commercials(commercial_folder)

        # LoadingDock creates the FactoryFloor internally
        print(f"[LOADING_DOCK] Initializing internal FactoryFloor...")

        # Set up segment root if not provided
        if segment_root is None:
            segment_root = Path("combreak_direct_data/segments")
            segment_root.mkdir(parents=True, exist_ok=True)

        self.factory_floor = FactoryFloor(
            base_url,
            storage_path=storage_path,
            segment_root=segment_root,
            break_renderer=self.break_renderer
        )

        print(f"[LOADING_DOCK] Ready with commercial folder: {self.commercial_folder}")

    def process_lineup(self, payload):
        """Main pipeline: Raw Data → Streaming Data → Store in Factory"""
        print(f"[LOADING_DOCK] Processing incoming payload...")
        self._pending_breaks = []

        # Extract data and metadata
        metadata, lineup_data = self._extract_data(payload)

        commercial_override = metadata.get('commercial_folder') if isinstance(metadata, dict) else None
        if commercial_override:
            self.update_commercial_folder(commercial_override)

        if not lineup_data:
            raise ValueError('No lineup data found')

        print(f"[LOADING_DOCK] Processing {len(lineup_data)} items...")

        # Get configuration
        channel_number = metadata.get('channel_number', 1)
        network_name = metadata.get('network', f"Channel {channel_number}")
        flex_duration = metadata.get('flex_duration')

        # Machine 1: Commercial Injection
        if flex_duration:
            lineup_data = self._inject_commercials(lineup_data, network_name, flex_duration)
            self._prime_initial_breaks()

        # Machine 2: Data Formatting
        channel_data = self._format_for_streaming(lineup_data, channel_number, network_name)

        print(f"[LOADING_DOCK] Processed channel {channel_number} with {len(channel_data['programs'])} programs")

        # Automatically send to Factory Floor for storage
        if self.factory_floor:
            print(f"[LOADING_DOCK] Sending processed data to Factory Floor...")
            stored_channel_number = self.factory_floor.store_channel(channel_data)
            print(f"[LOADING_DOCK] Channel {stored_channel_number} stored in Factory Floor")
            return stored_channel_number
        else:
            # Fallback if no factory_floor (for testing)
            return channel_data

    def _extract_data(self, payload):
        """Extract lineup data and metadata from client payload."""
        if isinstance(payload, dict):
            metadata = payload
            lineup_data = payload.get('lineup', payload.get('programs', payload.get('items', [])))
        else:
            metadata = {}
            lineup_data = payload if isinstance(payload, list) else []

        return metadata, lineup_data

    def update_commercial_folder(self, folder: str) -> None:
        path = Path(folder)
        if path.resolve() == self.commercial_folder.resolve():
            return
        print(f"[LOADING_DOCK] Updating commercial folder to {path}")
        self._commercial_cache.clear()
        self._pending_breaks = []
        self._configure_commercials(str(path))

    def _configure_commercials(self, folder: str) -> None:
        self.commercial_folder = Path(folder)
        self.commercial_folder.mkdir(parents=True, exist_ok=True)
        temp_break_folder = self.commercial_folder / '_pre_rendered_breaks'
        temp_break_folder.mkdir(parents=True, exist_ok=True)
        self.break_renderer = CommercialBreakRenderer(
            str(self.commercial_folder),
            str(temp_break_folder),
        )

    def _inject_commercials(self, lineup_data, network_name, flex_duration):
        """Commercial Injection Machine"""
        print(f"[LOADING_DOCK] Injecting commercials (flex_duration: {flex_duration}ms)")

        # Find consecutive bumps and inject commercials
        result = []
        timeline_ms = 0
        for i, item in enumerate(lineup_data):
            result.append(item)

            # Check if this and next item are both bumps
            next_item = lineup_data[i + 1] if i + 1 < len(lineup_data) else None
            if (next_item and
                self._is_bump(item, network_name) and
                self._is_bump(next_item, network_name)):

                break_id = self._generate_break_id(item, next_item, flex_duration, index=i)
                pre_rendered_block = self._inject_pre_rendered_break(break_id, flex_duration, timeline_ms)
                if not pre_rendered_block:
                    raise RuntimeError(f"Pre-rendered break REQUIRED but failed: {break_id}")

                result.append(pre_rendered_block)
                print(f"[LOADING_DOCK] Injected pre-rendered commercial break: {break_id}")

            timeline_ms += self._calculate_item_duration(item)

        return result

    def _is_bump(self, item, network_name):
        """Check if item is a bump."""
        title = (item.get('title', '') or '').lower()
        path = (item.get('file_path', '') or '').lower()

        # Check network prefix or bump path
        if network_name and title.startswith(network_name.lower()):
            return True
        return '/bump/' in path

    @staticmethod
    def _generate_break_id(current_item, next_item, flex_duration, index):
        """Generate a stable identifier for the break between two bumps."""
        block_id = current_item.get('block_id') or next_item.get('block_id') or f'idx_{index}'
        end_marker = current_item.get('end_time') or current_item.get('stop') or index
        network = current_item.get('network') or ''
        return f"break_{block_id}_{network}_{end_marker}_{flex_duration}"

    def _inject_pre_rendered_break(self, break_id, flex_duration, offset_ms):
        """Attempt to fetch or build a pre-rendered commercial break."""
        if not self.break_renderer:
            return None

        self._pending_breaks.append({
            'id': break_id,
            'duration_ms': flex_duration,
            'offset_ms': offset_ms,
        })

        break_path = self.break_renderer.plan_break(break_id, flex_duration)
        if not break_path:
            return None

        return {
            'title': 'Commercial Break',
            'file': break_path,
            'start_time': 0,
            'end_time': flex_duration,
            'type': 'commercial_break',
            'break_id': break_id,  # Store deterministic break_id for rebuilding
        }

    def _calculate_item_duration(self, item):
        start_ms = self._coerce_ms(item.get('start_time'))
        end_ms = self._coerce_ms(item.get('end_time'))
        duration_ms = self._coerce_ms(item.get('duration'))

        # No start time = run from beginning (0) to end time
        if start_ms is None and end_ms is not None:
            return max(0, end_ms - 0)

        # No end time = run from start time to end of show (duration)
        if start_ms is not None and end_ms is None and duration_ms is not None:
            return max(0, duration_ms - start_ms)

        # Both start and end times = normal segment
        if start_ms is not None and end_ms is not None:
            return max(0, end_ms - start_ms)

        # No start/end times = use duration (bumps)
        if duration_ms is not None and duration_ms > 0:
            return duration_ms

        raise ValueError(
            f"Unable to determine duration for lineup item '{item.get('title', 'Unknown')}'"
        )

    def _prime_initial_breaks(self, window_ms: int = 60 * 60 * 1000):
        if not self._pending_breaks:
            return

        self.break_renderer.pre_render_window(self._pending_breaks, window_ms)

    def _assign_block_ids(self, lineup_data):
        """Simple BLOCK_ID assignment: items without BLOCK_ID get the next one found."""
        print(f"[LOADING_DOCK] Assigning BLOCK_IDs to items without them...")

        result = []

        for i, item in enumerate(lineup_data):
            item_copy = item.copy()

            # Does it have a BLOCK_ID? Skip it.
            if item.get('block_id'):
                pass  # Keep existing BLOCK_ID
            else:
                # No BLOCK_ID? Look ahead until you find the next one that has one.
                next_block_id = self._find_next_block_id(lineup_data, i)
                item_copy['block_id'] = next_block_id or 'Unknown'
                if next_block_id:
                    print(f"[LOADING_DOCK] '{item.get('title', 'Unknown')}' assigned BLOCK_ID: {next_block_id}")

            result.append(item_copy)

        return result

    def _find_next_block_id(self, lineup_data, current_index):
        """Look ahead until you find the next item that has a BLOCK_ID."""
        for i in range(current_index + 1, len(lineup_data)):
            item = lineup_data[i]
            block_id = item.get('block_id')
            if block_id:
                return block_id
        return None

    @staticmethod
    def _coerce_ms(value):
        if value in (None, ""):
            return None
        try:
            if isinstance(value, (int, float)):
                return int(value)
            return int(float(str(value)))
        except (TypeError, ValueError):
            return None

    def _format_for_streaming(self, lineup_data, channel_number, network_name):
        """Data Formatting Machine - Convert to streaming format."""
        print(f"[LOADING_DOCK] Formatting {len(lineup_data)} items for streaming...")

        # First pass: Assign proper BLOCK_IDs with forward propagation
        lineup_with_block_ids = self._assign_block_ids(lineup_data)

        # Calculate timing
        total_duration = 0
        start_time = datetime.now(timezone.utc).replace(microsecond=0)
        programs = []

        for item in lineup_with_block_ids:
            file_path = item.get('file_path', '') or item.get('file', '')
            start_ms = self._coerce_ms(item.get('start_time')) or 0
            end_ms = self._coerce_ms(item.get('end_time'))
            duration_ms = self._coerce_ms(item.get('duration'))

            if duration_ms is not None and duration_ms <= 0:
                duration_ms = None

            # Handle different start/end time scenarios
            if end_ms is not None:
                # We have an end time - calculate duration from it
                duration_ms = max(0, end_ms - start_ms)
            elif duration_ms is not None:
                # No end time but we have duration
                if start_ms > 0:
                    # Calculate remaining duration from start time to end of file
                    remaining_duration = max(0, duration_ms - start_ms)
                    if remaining_duration > 0:
                        duration_ms = remaining_duration
                        end_ms = start_ms + duration_ms
                    else:
                        # Fallback if calculation results in zero/negative
                        duration_ms = max(1000, duration_ms)  # At least 1 second
                        end_ms = start_ms + duration_ms
                else:
                    # Use full duration (bumps or items starting from beginning)
                    end_ms = start_ms + duration_ms
            else:
                # Neither end time nor duration available
                raise ValueError(
                    f"Missing both end_time and duration for lineup item '{item.get('title', 'Unknown')}'"
                )

            if duration_ms is None or duration_ms <= 0:
                raise ValueError(
                    f"Invalid calculated duration for lineup item '{item.get('title', 'Unknown')}'"
                )

            # Create program
            program_start = start_time + timedelta(milliseconds=total_duration)
            program_end = program_start + timedelta(milliseconds=duration_ms)

            programs.append({
                'title': item.get('title', 'Unknown'),
                'block_id': item.get('block_id', 'Unknown'),  # Use assigned BLOCK_ID
                'file': file_path,
                'duration': duration_ms,
                'seekPosition': start_ms,
                'endPosition': end_ms,
                'start': program_start.isoformat(),
                'stop': program_end.isoformat()
            })

            total_duration += duration_ms

        # Create channel data
        return {
            'number': channel_number,
            'name': network_name,
            'startTime': start_time.isoformat(),
            'duration': total_duration,
            'programs': programs
        }
