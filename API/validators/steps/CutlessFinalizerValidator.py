"""
CutlessFinalizer Validator

Validates the output of the CutlessFinalizer step, which converts virtual cut data
into the final format with timestamps for DizqueTV cutless mode.

Tables Validated:
- lineup_vX_cutless: Final cutless lineups with timestamps
- bump_durations: Bump duration data (required for ComBreakDirect)

Note: This validator only runs if cutless mode is detected.
"""

from typing import Dict, List, Any
from collections import defaultdict

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel
from API.validators.utils import (
    TIMESTAMP_TOLERANCE_SEC,
    is_timestamp_equal
)


class CutlessFinalizerValidator(BaseValidator):
    """Validates CutlessFinalizer step output"""

    @property
    def step_name(self) -> str:
        return "CutlessFinalizer"

    @property
    def required_tables(self) -> list:
        return []  # Check dynamically for cutless tables

    @property
    def optional_tables(self) -> list:
        tables = ["bump_durations"]
        for version in range(10):
            tables.append(f"lineup_v{version}_cutless")
        return tables

    @property
    def pipeline_order(self) -> int:
        return 16  # Sixteenth step in pipeline

    def has_completed(self) -> bool:
        """
        Check if CutlessFinalizer has completed.

        Returns True if:
        - Cutless mode is active AND
        - At least one lineup_vX_cutless table exists with data

        Returns False if cutless mode is active but no data could be found.
        """
        meta = self.get_processing_metadata()
        if not meta['is_cutless']:
            return True  # Not using cutless mode, step not required

        # Check for at least one cutless lineup table with data
        for version in range(10):
            table_name = f"lineup_v{version}_cutless"
            if self.check_table_exists(table_name) and self.get_row_count(table_name) > 0:
                return True

        return False

    def _get_platform(self) -> str:
        """
        Get selected platform from app_data.

        Returns:
            Platform name or 'unknown'
        """
        if not self.table_exists('app_data'):
            return 'unknown'

        row = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'platform_type'"
        )

        if not row:
            return 'unknown'

        return row['value'] if hasattr(row, 'keys') else row[0]

    def validate(self) -> ValidationResult:
        """
        Validate CutlessFinalizer output.

        Checks:
        1. At least one lineup_vX_cutless table exists (if cutless mode)
        2. Cutless tables have timestamp columns
        3. Timestamps are properly populated
        4. Duration consistency (from test suite)
        5. Anime episodes have timing data
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check if cutless mode is being used
        metadata = self.get_processing_metadata()
        if not metadata['is_cutless']:
            # Not using cutless mode, this step doesn't apply
            result.is_completed = True
            self.add_issue(
                result,
                ValidationLevel.INFO,
                "Cutless mode not detected",
                "CutlessFinalizer only runs in cutless mode",
                "This is normal if using traditional cutting mode"
            )
            return result

        # Find cutless lineup tables
        cutless_tables = []
        for version in range(10):
            table_name = f"lineup_v{version}_cutless"
            if self.check_table_exists(table_name):
                cutless_tables.append((version, table_name))

        if not cutless_tables:
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "No cutless lineup tables found",
                "Expected at least one lineup_vX_cutless table in cutless mode",
                "Run CutlessFinalizer to create cutless lineups"
            )
            return result

        platform = metadata['platform']
        requires_bump_durations = metadata['requires_bump_calculator']
        result.metadata["platform"] = platform
        result.metadata["requires_bump_durations"] = requires_bump_durations

        result.is_completed = True

        # Validate each cutless table
        for version, table_name in cutless_tables:
            self._validate_cutless_table(
                result,
                version,
                table_name,
                requires_bump_durations
            )

        # Check bump_durations if exists (required for ComBreakDirect)
        if self.check_table_exists("bump_durations"):
            self._validate_bump_durations(result)

        result.metadata["cutless_versions"] = [v for v, _ in cutless_tables]

        return result

    def _validate_cutless_table(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        requires_bump_durations: bool
    ):
        """
        Validate a specific cutless lineup table.

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the cutless table
        """
        row_count = self.get_row_count(table_name)

        if row_count == 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version} cutless lineup is empty",
                f"Table {table_name} has no data",
                f"This may indicate no content for version {version}",
                table=table_name
            )
            return

        # Check for timing columns
        required_columns = ["FULL_FILE_PATH", "BLOCK_ID", "startTime", "endTime", "duration"]
        missing_columns = self.check_required_columns(table_name, required_columns)

        if missing_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version} cutless lineup missing timing columns",
                f"Missing columns: {', '.join(missing_columns)}",
                "Re-run CutlessFinalizer to add timing data",
                table=table_name
            )
            return

        # Validate timestamp data
        cutless_data = self.get_all_rows(table_name)

        # Count anime episodes
        anime_entries = [e for e in cutless_data if self.is_anime(e.get("FULL_FILE_PATH", ""))]

        # Per test suite: anime episodes must have at least startTime OR endTime
        anime_without_timestamps = 0
        for entry in anime_entries:
            if entry.get("startTime") is None and entry.get("endTime") is None:
                anime_without_timestamps += 1

        if anime_without_timestamps > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version}: {anime_without_timestamps} anime episode(s) missing timestamps",
                f"Found {anime_without_timestamps}/{len(anime_entries)} anime entries without startTime or endTime",
                "Re-run CutlessFinalizer to populate timestamps",
                table=table_name
            )

        # Check duration consistency (from test suite)
        entries_with_timing = [e for e in cutless_data if e.get("startTime") is not None or e.get("endTime") is not None]
        entries_without_duration = sum(1 for e in entries_with_timing if not e.get("duration"))

        if entries_without_duration > 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version}: {entries_without_duration} entry/entries with timing but no duration",
                "Entries with startTime/endTime should also have duration",
                "Check duration calculation logic",
                table=table_name
            )

        result.metadata[f"v{version}_cutless_total"] = row_count
        result.metadata[f"v{version}_cutless_anime"] = len(anime_entries)
        result.metadata[f"v{version}_cutless_with_timestamps"] = len(anime_entries) - anime_without_timestamps

        # Enhanced timestamp validation
        self._validate_bump_timestamps(result, version, table_name, cutless_data)
        self._validate_anime_timeline_pattern(result, version, table_name, cutless_data)
        self._validate_timestamp_continuity(result, version, table_name, cutless_data)
        self._validate_duration_math(result, version, table_name, cutless_data)
        self._validate_bump_duration_requirements(
            result,
            version,
            table_name,
            cutless_data,
            requires_bump_durations
        )

    def _validate_bump_durations(self, result: ValidationResult):
        """
        Validate bump_durations table (required for ComBreakDirect).

        Args:
            result: ValidationResult to add issues to
        """
        if not self.validate_table_structure(
            result,
            "bump_durations",
            required_columns=["FULL_FILE_PATH", "duration"],
            min_rows=1
        ):
            return

        durations = self.get_all_rows("bump_durations")

        # Check for missing durations
        missing_durations = sum(1 for d in durations if not d.get("duration"))

        if missing_durations > 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{missing_durations} bump(s) missing duration",
                f"Found {missing_durations}/{len(durations)} entries without duration",
                "Re-run BumpCalculator to calculate durations",
                table="bump_durations"
            )

        result.metadata["bump_durations_count"] = len(durations)

    def _group_continuous_sequences(
        self,
        cutless_data: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group anime entries into continuous sequences based on BLOCK_ID changes.

        When the same episode appears multiple times in the lineup (e.g., when shows loop),
        each occurrence is a separate sequence to validate independently.

        Args:
            cutless_data: List of cutless lineup entries

        Returns:
            List of continuous sequences, where each sequence is a list of parts
            belonging to the same episode instance
        """
        # Filter anime entries only, preserving order
        anime_entries = [
            e for e in cutless_data
            if self.is_anime(e.get("FULL_FILE_PATH", ""))
        ]

        if not anime_entries:
            return []

        sequences = []
        current_sequence = [anime_entries[0]]
        current_block_id = anime_entries[0].get("BLOCK_ID")

        for entry in anime_entries[1:]:
            block_id = entry.get("BLOCK_ID")

            if block_id == current_block_id:
                # Same episode, add to current sequence
                current_sequence.append(entry)
            else:
                # Different episode, start new sequence
                sequences.append(current_sequence)
                current_sequence = [entry]
                current_block_id = block_id

        # Don't forget the last sequence
        if current_sequence:
            sequences.append(current_sequence)

        return sequences

    def _detect_duplicate_episodes(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        sequences: List[List[Dict[str, Any]]]
    ):
        """
        Detect and report episodes that appear multiple times in the lineup.

        This is not an error - it's expected when shows loop back to the beginning.
        Reported as INFO for user awareness.

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the cutless table
            sequences: List of continuous episode sequences
        """
        # Count occurrences of each BLOCK_ID
        block_counts = defaultdict(int)
        for sequence in sequences:
            if sequence:
                block_id = sequence[0].get("BLOCK_ID")
                if block_id:
                    block_counts[block_id] += 1

        # Find duplicates (appear more than once)
        duplicates = {bid: count for bid, count in block_counts.items() if count > 1}

        if duplicates:
            # Format message
            duplicate_list = [f"{bid} appears {count} times" for bid, count in sorted(duplicates.items())]
            details = f"Episodes repeated in {table_name}:\n" + "\n".join(f"  • {item}" for item in duplicate_list)

            self.add_issue(
                result,
                ValidationLevel.INFO,
                f"Version {version}: {len(duplicates)} episode(s) repeated in lineup",
                details,
                "This is normal when shows loop back to the beginning. No action needed unless this is unexpected.",
                table=table_name
            )

        result.metadata[f"v{version}_duplicate_episodes"] = len(duplicates)

    def _validate_timestamp_continuity(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        cutless_data: List[Dict[str, Any]]
    ):
        """
        Validate cutless timestamp continuity and consistency.

        Checks:
        1. No gaps between parts of the same episode
        2. Duration math: endTime - startTime = duration (within tolerance)
        3. First part has endTime, last part has startTime
        4. Timeline forms continuous playback

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the cutless table
            cutless_data: List of cutless lineup entries
        """
        # Group into continuous sequences (handles duplicate episodes correctly)
        sequences = self._group_continuous_sequences(cutless_data)

        if not sequences:
            return

        timeline_gaps = []
        duration_mismatches = []
        incomplete_parts = []

        # Validate each continuous sequence independently
        for parts in sequences:
            if not parts:
                continue

            block_id = parts[0].get('BLOCK_ID')

            # Check first part
            first_part = parts[0]
            if first_part.get('endTime') is None:
                incomplete_parts.append({
                    'block_id': block_id,
                    'part_index': 0,
                    'issue': 'Missing endTime',
                    'path': first_part.get('FULL_FILE_PATH', '')
                })

            # Check last part
            last_part = parts[-1]
            if last_part.get('startTime') is None:
                incomplete_parts.append({
                    'block_id': block_id,
                    'part_index': len(parts) - 1,
                    'issue': 'Missing startTime',
                    'path': last_part.get('FULL_FILE_PATH', '')
                })

            # Check duration consistency across parts (duration stores total episode length)
            # For ComBreakDirect: duration field is the same for all parts of an episode
            # Last part calculates its play time as: duration - startTime
            durations_in_block = [p.get('duration') for p in parts if p.get('duration') is not None]

            if len(durations_in_block) > 1:
                # Check if all parts have the same duration value
                first_duration = durations_in_block[0]
                for i, part in enumerate(parts):
                    part_duration = part.get('duration')
                    if part_duration is not None and not is_timestamp_equal(part_duration, first_duration, TIMESTAMP_TOLERANCE_SEC):
                        duration_mismatches.append({
                            'block_id': block_id,
                            'part_index': i,
                            'stored_duration': part_duration,
                            'expected_duration': first_duration,
                            'diff': abs(part_duration - first_duration),
                            'path': part.get('FULL_FILE_PATH', ''),
                            'issue': 'Duration field should be consistent across all parts (stores total episode length)'
                        })

            # Check for gaps between parts
            # NOTE: All timestamps are in milliseconds
            for i in range(len(parts) - 1):
                current_end = parts[i].get('endTime')
                next_start = parts[i + 1].get('startTime')

                if current_end is not None and next_start is not None:
                    tolerance_ms = TIMESTAMP_TOLERANCE_SEC * 1000  # Convert 0.1s to 100ms
                    if not is_timestamp_equal(current_end, next_start, tolerance_ms):
                        gap_ms = next_start - current_end
                        timeline_gaps.append({
                            'block_id': block_id,
                            'gap_after_part': i,
                            'gap_size_ms': gap_ms,
                            'current_end_ms': current_end,
                            'next_start_ms': next_start,
                            'current_path': parts[i].get('FULL_FILE_PATH', ''),
                            'next_path': parts[i + 1].get('FULL_FILE_PATH', '')
                        })

        # Report issues
        if timeline_gaps:
            # Group by BLOCK_ID
            gaps_by_block = {}
            for gap in timeline_gaps:
                block_id = gap['block_id']
                if block_id not in gaps_by_block:
                    gaps_by_block[block_id] = []
                gap_sec = gap['gap_size_ms'] / 1000.0
                gaps_by_block[block_id].append(f"Gap after part {gap['gap_after_part']+1}: {gap_sec:.1f}s")

            # Format details with all affected BLOCK_IDs
            details_lines = [f"Affected episodes in {table_name}:"]
            for block_id in sorted(gaps_by_block.keys()):
                gaps_for_block = gaps_by_block[block_id]
                details_lines.append(f"  • {block_id}: {'; '.join(gaps_for_block)}")

            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version}: {len(timeline_gaps)} timeline gap(s) detected",
                "\n".join(details_lines),
                "Re-run CutlessFinalizer to recalculate timestamps for continuous playback",
                table=table_name
            )
            result.is_valid = False

        if duration_mismatches:
            # Group by BLOCK_ID
            mismatches_by_block = {}
            for m in duration_mismatches:
                block_id = m['block_id']
                if block_id not in mismatches_by_block:
                    mismatches_by_block[block_id] = []
                stored_sec = m['stored_duration'] / 1000.0
                expected_sec = m['expected_duration'] / 1000.0
                diff_sec = m['diff'] / 1000.0
                mismatches_by_block[block_id].append(f"Part {m['part_index']+1}: {stored_sec:.1f}s (expected {expected_sec:.1f}s, diff {diff_sec:.1f}s)")

            # Format details with all affected BLOCK_IDs
            details_lines = [f"Affected episodes in {table_name}:"]
            for block_id in sorted(mismatches_by_block.keys()):
                issues_for_block = mismatches_by_block[block_id]
                details_lines.append(f"  • {block_id}: {'; '.join(issues_for_block)}")

            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version}: {len(duration_mismatches)} duration inconsistency issue(s)",
                "\n".join(details_lines),
                "Re-run CutlessFinalizer to ensure all parts of each episode have the same duration value (total episode length)",
                table=table_name
            )

        if incomplete_parts:
            # Group by BLOCK_ID
            incomplete_by_block = {}
            for p in incomplete_parts:
                block_id = p['block_id']
                if block_id not in incomplete_by_block:
                    incomplete_by_block[block_id] = []
                incomplete_by_block[block_id].append(f"Part {p['part_index']+1}: {p['issue']}")

            # Format details with all affected BLOCK_IDs
            details_lines = [f"Affected episodes in {table_name}:"]
            for block_id in sorted(incomplete_by_block.keys()):
                issues_for_block = incomplete_by_block[block_id]
                details_lines.append(f"  • {block_id}: {'; '.join(issues_for_block)}")

            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version}: {len(incomplete_parts)} incomplete part(s)",
                "\n".join(details_lines),
                "Re-run CutlessFinalizer to populate missing timestamps",
                table=table_name
            )
            result.is_valid = False

        result.metadata[f"v{version}_timeline_gaps"] = len(timeline_gaps)
        result.metadata[f"v{version}_duration_mismatches"] = len(duration_mismatches)
        result.metadata[f"v{version}_incomplete_parts"] = len(incomplete_parts)

    def _validate_bump_timestamps(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        cutless_data: List[Dict[str, Any]]
    ):
        """
        Validate that bumps have NULL timestamps.

        Bumps should have:
        - startTime = NULL
        - endTime = NULL
        - duration = value (milliseconds)

        Anime parts should have at least one timestamp (checked elsewhere).

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the cutless table
            cutless_data: List of cutless lineup entries
        """
        # Filter bump entries (non-anime files)
        bump_entries = [
            e for e in cutless_data
            if self.is_bump(e.get("FULL_FILE_PATH", ""))
        ]

        if not bump_entries:
            return

        # Check for bumps with invalid timestamps
        invalid_bumps = []
        for idx, entry in enumerate(bump_entries):
            start = entry.get("startTime")
            end = entry.get("endTime")

            # Bumps must have BOTH timestamps as NULL
            if start is not None or end is not None:
                invalid_bumps.append({
                    'path': entry.get('FULL_FILE_PATH', ''),
                    'startTime': start,
                    'endTime': end,
                    'block_id': entry.get('BLOCK_ID', 'unknown'),
                    'index': idx
                })

        # Report issues
        if invalid_bumps:
            first = invalid_bumps[0]
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version}: {len(invalid_bumps)} bump(s) with invalid timestamps",
                f"Bumps should have startTime=NULL and endTime=NULL (only duration populated). Example: BLOCK_ID '{first['block_id']}' has startTime={first['startTime']}, endTime={first['endTime']}",
                "Re-run CutlessFinalizer to fix bump timestamp data. Bumps should not have timing data.",
                table=table_name
            )
            result.is_valid = False

        result.metadata[f"v{version}_invalid_bump_timestamps"] = len(invalid_bumps)

    def _validate_anime_timeline_pattern(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        cutless_data: List[Dict[str, Any]]
    ):
        """
        Validate anime parts follow the expected timeline pattern.

        Expected pattern for anime parts within a BLOCK_ID:
        - First part: startTime=NULL, endTime=value
        - Middle parts: startTime=value, endTime=value
        - Last part: startTime=value, endTime=NULL

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the cutless table
            cutless_data: List of cutless lineup entries
        """
        # Group into continuous sequences (handles duplicate episodes correctly)
        sequences = self._group_continuous_sequences(cutless_data)

        if not sequences:
            return

        # Detect and report duplicate episodes as INFO
        self._detect_duplicate_episodes(result, version, table_name, sequences)

        pattern_violations = []

        # Validate each continuous sequence independently
        for parts in sequences:
            if len(parts) == 0:
                continue

            block_id = parts[0].get('BLOCK_ID')

            # Check first part: startTime=NULL, endTime=value
            first = parts[0]
            if first.get('startTime') is not None:
                pattern_violations.append({
                    'block_id': block_id,
                    'part': 1,
                    'issue': f"First part should have startTime=NULL, got {first.get('startTime')}",
                    'path': first.get('FULL_FILE_PATH', '')
                })
            if first.get('endTime') is None:
                pattern_violations.append({
                    'block_id': block_id,
                    'part': 1,
                    'issue': f"First part should have endTime=value, got NULL",
                    'path': first.get('FULL_FILE_PATH', '')
                })

            # Check middle parts: startTime=value, endTime=value
            for i in range(1, len(parts) - 1):
                part = parts[i]
                if part.get('startTime') is None:
                    pattern_violations.append({
                        'block_id': block_id,
                        'part': i + 1,
                        'issue': f"Middle part should have startTime=value, got NULL",
                        'path': part.get('FULL_FILE_PATH', '')
                    })
                if part.get('endTime') is None:
                    pattern_violations.append({
                        'block_id': block_id,
                        'part': i + 1,
                        'issue': f"Middle part should have endTime=value, got NULL",
                        'path': part.get('FULL_FILE_PATH', '')
                    })

            # Check last part: startTime=value, endTime=NULL (only if >1 part)
            if len(parts) > 1:
                last = parts[-1]
                if last.get('startTime') is None:
                    pattern_violations.append({
                        'block_id': block_id,
                        'part': len(parts),
                        'issue': f"Last part should have startTime=value, got NULL",
                        'path': last.get('FULL_FILE_PATH', '')
                    })
                if last.get('endTime') is not None:
                    pattern_violations.append({
                        'block_id': block_id,
                        'part': len(parts),
                        'issue': f"Last part should have endTime=NULL, got {last.get('endTime')}",
                        'path': last.get('FULL_FILE_PATH', '')
                    })

        # Report violations
        if pattern_violations:
            # Group by BLOCK_ID to show which episodes are affected
            affected_blocks = {}
            for v in pattern_violations:
                block_id = v['block_id']
                if block_id not in affected_blocks:
                    affected_blocks[block_id] = []
                affected_blocks[block_id].append(f"Part {v['part']}: {v['issue']}")

            # Format details with all affected BLOCK_IDs
            details_lines = [f"Affected episodes in {table_name}:"]
            for block_id in sorted(affected_blocks.keys()):
                issues_for_block = affected_blocks[block_id]
                details_lines.append(f"  • {block_id}: {'; '.join(issues_for_block)}")

            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version}: {len(pattern_violations)} anime timeline pattern violation(s)",
                "\n".join(details_lines),
                "Re-run CutlessFinalizer to correct anime timeline pattern. This is required for proper cutless playback.",
                table=table_name
            )
            result.is_valid = False

        result.metadata[f"v{version}_timeline_pattern_violations"] = len(pattern_violations)

    def _validate_duration_math(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        cutless_data: List[Dict[str, Any]]
    ):
        """
        Validate duration math for anime episodes.

        Checks that the sum of all segment durations equals the stored duration field:
        - Segment duration = endTime - startTime
        - NULL startTime is treated as 0
        - NULL endTime is treated as total duration
        - Sum of all segments should equal stored duration

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the cutless table
            cutless_data: List of cutless lineup entries
        """
        # Group into continuous sequences (handles duplicate episodes correctly)
        sequences = self._group_continuous_sequences(cutless_data)

        if not sequences:
            return

        math_violations = []

        # Validate each continuous sequence independently
        for parts in sequences:
            if len(parts) == 0:
                continue

            block_id = parts[0].get('BLOCK_ID')

            # Get total duration (should be same for all parts)
            total_duration = parts[0].get('duration')
            if not total_duration:
                continue  # Already caught by other validators

            # Calculate sum of segments
            segment_sum = 0
            for part in parts:
                start = part.get('startTime') or 0  # NULL means 0
                end = part.get('endTime')

                # NULL endTime means it plays to end of episode
                if end is None:
                    end = total_duration

                segment_duration = end - start
                segment_sum += segment_duration

            # Check if sum matches total (with 10x tolerance for accumulated rounding)
            # NOTE: All durations and timestamps are in milliseconds
            tolerance_ms = TIMESTAMP_TOLERANCE_SEC * 1000 * 10  # Convert 0.1s to 100ms, then 10x = 1000ms
            if not is_timestamp_equal(segment_sum, total_duration, tolerance_ms):
                math_violations.append({
                    'block_id': block_id,
                    'expected_duration_ms': total_duration,
                    'calculated_sum_ms': segment_sum,
                    'difference_ms': abs(segment_sum - total_duration),
                    'part_count': len(parts)
                })

        # Report violations
        if math_violations:
            # Format details with all affected BLOCK_IDs
            details_lines = [f"Affected episodes in {table_name}:"]
            for v in sorted(math_violations, key=lambda x: x['block_id']):
                expected_sec = v['expected_duration_ms'] / 1000.0
                calculated_sec = v['calculated_sum_ms'] / 1000.0
                diff_sec = v['difference_ms'] / 1000.0
                details_lines.append(
                    f"  • {v['block_id']} ({v['part_count']} parts): "
                    f"duration={expected_sec:.1f}s, segments sum={calculated_sec:.1f}s, diff={diff_sec:.1f}s"
                )

            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version}: {len(math_violations)} episode(s) with duration math mismatch",
                "\n".join(details_lines),
                "This may indicate rounding issues or incorrect timestamp calculations. Verify CutlessFinalizer duration math.",
                table=table_name
            )

        result.metadata[f"v{version}_duration_math_mismatches"] = len(math_violations)

    def _validate_bump_duration_requirements(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        cutless_data: List[Dict[str, Any]],
        requires_bump_durations: bool
    ):
        """
        Ensure bump entries in cutless lineups have duration values when required.

        ComBreakDirect depends on BumpCalculator writing duration values back
        into the cutless lineup tables. Other platforms can skip this check.
        """
        if not requires_bump_durations:
            return

        bump_entries = [
            entry for entry in cutless_data
            if self.is_bump(entry.get("FULL_FILE_PATH", ""))
        ]

        if not bump_entries:
            return

        missing = []
        for entry in bump_entries:
            duration = entry.get("duration")
            if duration is None or duration <= 0:
                missing.append(entry)

        if len(missing) == len(bump_entries):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                f"Version {version}: bump durations missing for all {len(bump_entries)} bump(s)",
                "BumpCalculator was not run after CutlessFinalizer. "
                "ComBreakDirect requires bump durations to be populated in lineup_vX_cutless.",
                "Run BumpCalculator (ComBreakDirect requirement) before exporting.",
                table=table_name
            )
            result.is_valid = False
            return

        if missing:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version}: {len(missing)} bump(s) missing duration values",
                "Some bump files lack duration data needed for ComBreakDirect timing.",
                "Re-run BumpCalculator to measure the remaining bump files.",
                table=table_name
            )
            result.is_valid = False

        result.metadata[f"v{version}_bump_duration_missing"] = len(missing)
