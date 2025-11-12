"""
BlockMaker Validator

Validates the output of the BlockMaker (BlockIDCreator) step, which assigns
BLOCK_IDs to group episode parts and their associated bumps together.

Tables Validated:
- commercial_injector_final: Final lineup with BLOCK_IDs assigned

BLOCK_ID Format: [SHOW_NAME]_SXXEXX (uppercase, special chars as underscores)
Example: MY_HERO_ACADEMIA_S01E05

Key Business Rules:
- BLOCK_IDs are created from episode files (files with SxxExx pattern)
- Bumps get BLOCK_IDs through backward fill (from the next episode)
- All files in the same block (episode parts + bumps) have the same BLOCK_ID
- SHOW_NAME_1 and "Season and Episode" columns should be dropped
"""

import re
from typing import Dict, List, Any
from collections import defaultdict

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel
from API.validators.utils import (
    BLOCK_ID_PATTERN,
    BLOCK_ID_DESCRIPTION,
    is_valid_block_id
)


class BlockMakerValidator(BaseValidator):
    """Validates BlockMaker step output"""

    @property
    def step_name(self) -> str:
        return "BlockMaker"

    @property
    def required_tables(self) -> list:
        return ["commercial_injector_final"]

    @property
    def optional_tables(self) -> list:
        return []

    @property
    def pipeline_order(self) -> int:
        return 14  # Fourteenth step in pipeline

    def validate(self) -> ValidationResult:
        """
        Validate BlockMaker output.

        Checks:
        1. commercial_injector_final table exists
        2. Required columns present (BLOCK_ID, FULL_FILE_PATH)
        3. Dropped columns removed (SHOW_NAME_1, Season and Episode)
        4. BLOCK_ID format is correct (uppercase, underscore-separated)
        5. BLOCK_IDs match SxxExx pattern
        6. No or minimal NULL BLOCK_IDs
        7. Episode files have BLOCK_IDs
        8. Backward fill worked (bumps have BLOCK_IDs)
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check table exists
        if not self.check_table_exists("commercial_injector_final"):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "BlockMaker not run",
                "commercial_injector_final table not found",
                "Run BlockMaker to assign BLOCK_IDs"
            )
            return result

        result.is_completed = True

        # Validate table structure
        if not self.validate_table_structure(
            result,
            "commercial_injector_final",
            required_columns=["BLOCK_ID", "FULL_FILE_PATH"],
            min_rows=1
        ):
            return result

        # Check that dropped columns are gone
        all_columns = self.get_column_names("commercial_injector_final")

        if "SHOW_NAME_1" in all_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "SHOW_NAME_1 column not dropped",
                "BlockMaker should remove SHOW_NAME_1 column",
                "Re-run BlockMaker to properly clean up columns",
                table="commercial_injector_final"
            )
            result.is_valid = False

        if "Season and Episode" in all_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "'Season and Episode' column not dropped",
                "BlockMaker should remove 'Season and Episode' column",
                "Re-run BlockMaker to properly clean up columns",
                table="commercial_injector_final"
            )
            result.is_valid = False

        # Get all data
        lineup_data = self.get_all_rows("commercial_injector_final")

        if not lineup_data:
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "Final lineup is empty",
                "commercial_injector_final has no data",
                "This shouldn't happen - re-run 'Prepare Cut Anime for Lineup'",
                table="commercial_injector_final"
            )
            result.is_valid = False
            return result

        # Validate BLOCK_IDs
        self._validate_block_ids(result, lineup_data)

        # Enhanced BLOCK_ID validations
        self._validate_block_id_format_strict(result, lineup_data)
        self._validate_block_id_consistency(result, lineup_data)

        return result

    def _validate_block_ids(self, result: ValidationResult, lineup_data: list):
        """
        Validate BLOCK_ID format and assignment.

        Args:
            result: ValidationResult to add issues to
            lineup_data: List of lineup entries
        """
        total_rows = len(lineup_data)
        null_block_ids = 0
        invalid_format = 0
        episode_files_without_block_id = 0
        bump_files_without_block_id = 0
        valid_block_ids = set()

        # BLOCK_ID pattern: Allow any characters (including Unicode), ending with _SXXEXX
        # Note: BlockIDCreator uses .upper() which preserves Unicode characters
        block_id_pattern = re.compile(r'^.+_S\d{2}E\d{2}$')

        for entry in lineup_data:
            block_id = entry.get("BLOCK_ID")
            file_path = entry.get("FULL_FILE_PATH", "")

            # Check for NULL BLOCK_IDs
            if block_id is None or block_id == "":
                null_block_ids += 1

                # Categorize what type of file is missing BLOCK_ID
                if self.is_anime(file_path):
                    episode_files_without_block_id += 1
                else:
                    bump_files_without_block_id += 1

                continue

            # Validate BLOCK_ID format
            if not block_id_pattern.match(block_id):
                invalid_format += 1
            else:
                valid_block_ids.add(block_id)

        # Report issues
        if null_block_ids > 0:
            percentage = (null_block_ids / total_rows) * 100

            if null_block_ids == total_rows:
                # Everything is NULL - critical failure
                self.add_issue(
                    result,
                    ValidationLevel.CRITICAL,
                    "No BLOCK_IDs assigned",
                    f"All {total_rows} entries have NULL BLOCK_IDs",
                    "Check that episode files have SxxExx pattern in filenames. Re-run BlockMaker",
                    table="commercial_injector_final"
                )
                result.is_valid = False
            elif percentage > 50:
                # More than half are NULL - serious problem
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    f"{null_block_ids} entries missing BLOCK_IDs ({percentage:.1f}%)",
                    f"Many files couldn't be grouped: {episode_files_without_block_id} episodes, {bump_files_without_block_id} bumps",
                    "Check file naming follows SxxExx format. Re-run BlockMaker",
                    table="commercial_injector_final"
                )
                result.is_valid = False
            else:
                # Small number of NULLs - warning
                self.add_issue(
                    result,
                    ValidationLevel.WARNING,
                    f"{null_block_ids} entries missing BLOCK_IDs ({percentage:.1f}%)",
                    f"Some files couldn't be grouped: {episode_files_without_block_id} episodes, {bump_files_without_block_id} bumps",
                    "This is usually okay if these are edge case files",
                    table="commercial_injector_final"
                )

        if episode_files_without_block_id > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{episode_files_without_block_id} episode files missing BLOCK_IDs",
                "Episode files (with SxxExx pattern) should always have BLOCK_IDs",
                "Check that episode filenames contain SxxExx pattern. Re-run BlockMaker",
                table="commercial_injector_final"
            )
            result.is_valid = False

        if invalid_format > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{invalid_format} BLOCK_IDs have invalid format",
                "Expected format: [SHOW_NAME]_SXXEXX (uppercase, underscores)",
                "Re-run BlockMaker to regenerate BLOCK_IDs",
                table="commercial_injector_final"
            )
            result.is_valid = False

        # Store metadata
        result.metadata["total_entries"] = total_rows
        result.metadata["unique_block_ids"] = len(valid_block_ids)
        result.metadata["null_block_ids"] = null_block_ids
        result.metadata["invalid_format"] = invalid_format
        result.metadata["episodes_without_id"] = episode_files_without_block_id
        result.metadata["bumps_without_id"] = bump_files_without_block_id

        # Success message if everything looks good
        if null_block_ids == 0 and invalid_format == 0:
            result.metadata["validation_message"] = (
                f"All {total_rows} entries have valid BLOCK_IDs "
                f"({len(valid_block_ids)} unique blocks)"
            )

    def _validate_block_id_format_strict(self, result: ValidationResult, lineup_data: List[Dict[str, Any]]):
        """
        Validate BLOCK_ID format using strict pattern matching.

        Checks that BLOCK_IDs match the expected pattern:
        SHOW_NAME_SXXEXX (uppercase alphanumeric + underscores only)

        Args:
            result: ValidationResult to add issues to
            lineup_data: List of lineup entries
        """
        invalid_formats = []

        for idx, entry in enumerate(lineup_data):
            block_id = entry.get("BLOCK_ID")

            # Skip NULL/empty BLOCK_IDs (already checked by _validate_block_ids)
            if not block_id:
                continue

            # Validate using strict pattern
            if not is_valid_block_id(block_id):
                invalid_formats.append({
                    'row': idx,
                    'block_id': block_id,
                    'path': entry.get('FULL_FILE_PATH', '')
                })

        # Report issues
        if invalid_formats:
            # Show first few examples
            examples = invalid_formats[:3]
            example_str = "; ".join([f"'{e['block_id']}'" for e in examples])

            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{len(invalid_formats)} BLOCK_ID(s) with malformed format",
                f"BLOCK_IDs must match pattern: {BLOCK_ID_DESCRIPTION}. Examples: {example_str}",
                "Re-run BlockMaker to regenerate BLOCK_IDs with correct format",
                table="commercial_injector_final",
                row_index=invalid_formats[0]['row']
            )
            result.is_valid = False

        result.metadata["strict_format_violations"] = len(invalid_formats)

    def _validate_block_id_consistency(self, result: ValidationResult, lineup_data: List[Dict[str, Any]]):
        """
        Validate that all parts of an episode have the same BLOCK_ID.

        Groups entries by extracting the episode identifier (SXXEXX) from
        file paths and verifies that all parts/segments of the same episode
        share the same BLOCK_ID.

        Args:
            result: ValidationResult to add issues to
            lineup_data: List of lineup entries
        """
        # Group anime files by episode identifier
        episode_groups: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: defaultdict(list))

        for idx, entry in enumerate(lineup_data):
            path = entry.get('FULL_FILE_PATH', '')
            block_id = entry.get('BLOCK_ID')

            # Only check anime episode files (skip bumps)
            if self.is_bump(path):
                continue

            # Skip entries without BLOCK_IDs (already reported)
            if not block_id:
                continue

            # Extract episode info
            episode_info = self.extract_episode_info(path)
            if not episode_info:
                continue

            # Create episode key (Season + Episode)
            episode_key = f"S{episode_info['season']}E{episode_info['episode']}"

            # Try to extract show name from path or BLOCK_ID
            # BLOCK_ID format is SHOW_NAME_SXXEXX, so we can extract show
            if '_S' in block_id:
                show_name = block_id.rsplit('_S', 1)[0]
            else:
                # Fallback: use first part of filename
                show_name = path.split('/')[-1].split(' -')[0] if ' -' in path else "UNKNOWN"

            # Create full identifier: SHOW_EPISODE
            full_key = f"{show_name}_{episode_key}"

            # Track BLOCK_IDs for this episode
            episode_groups[full_key]['block_ids'].append(block_id)
            episode_groups[full_key]['paths'].append(path)
            episode_groups[full_key]['rows'].append(idx)

        # Find inconsistencies
        inconsistent_episodes = []

        for episode_id, data in episode_groups.items():
            unique_block_ids = set(data['block_ids'])

            # If this episode has multiple different BLOCK_IDs, it's inconsistent
            if len(unique_block_ids) > 1:
                inconsistent_episodes.append({
                    'episode': episode_id,
                    'block_ids': list(unique_block_ids),
                    'part_count': len(data['block_ids']),
                    'sample_path': data['paths'][0],
                    'row': data['rows'][0]
                })

        # Report issues
        if inconsistent_episodes:
            # Show first example in detail
            first = inconsistent_episodes[0]
            block_id_list = ', '.join([f"'{bid}'" for bid in first['block_ids']])

            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{len(inconsistent_episodes)} episode(s) have inconsistent BLOCK_IDs across parts",
                f"Episode {first['episode']} has {first['part_count']} parts with different BLOCK_IDs: {block_id_list}",
                "Re-run BlockMaker to ensure all parts of an episode get the same BLOCK_ID",
                table="commercial_injector_final",
                row_index=first['row']
            )
            result.is_valid = False

        result.metadata["inconsistent_episodes"] = len(inconsistent_episodes)
