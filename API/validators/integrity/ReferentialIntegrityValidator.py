"""
Referential Integrity Validator

Validates cross-table relationships and detects orphaned data.
This is a cross-cutting validator that runs after the pipeline completes
to ensure database consistency across multiple tables.
"""

from typing import List, Dict, Any, Set
from collections import defaultdict

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel
from API.validators.utils import ORPHAN_WARNING_THRESHOLD, ORPHAN_ERROR_THRESHOLD


class ReferentialIntegrityValidator(BaseValidator):
    """
    Validates referential integrity across pipeline tables.

    Checks:
    1. Episodes in final lineup exist in source tables
    2. BLOCK_IDs reference valid episodes
    3. BLOCK_IDs contain anime content
    4. Show name consistency (informational)
    """

    @property
    def step_name(self) -> str:
        return "ReferentialIntegrity"

    @property
    def required_tables(self) -> List[str]:
        # No specific required tables - dynamically checks what's available
        return []

    @property
    def pipeline_order(self) -> int:
        return 21  # After LineupIntegrity (final validation)

    def has_completed(self) -> bool:
        """
        Referential integrity validation can run once commercial_injector_final exists.

        Returns:
            True if commercial_injector_final exists with data
        """
        return (self.check_table_exists("commercial_injector_final") and
                self.get_row_count("commercial_injector_final") > 0)

    def validate(self) -> ValidationResult:
        """
        Validate referential integrity across tables.

        Returns:
            ValidationResult with cross-table relationship validation
        """
        result = self.create_result(is_completed=False, is_valid=True)

        if not self.has_completed():
            self.add_info(
                result,
                "Referential integrity validation not applicable yet - requires commercial_injector_final"
            )
            return result

        result.is_completed = True

        # Run cross-table checks
        self._validate_episode_references(result)
        self._validate_block_id_references(result)
        self._validate_show_consistency(result)

        return result

    def _validate_episode_references(self, result: ValidationResult):
        """
        Check that episodes in final lineup exist in source tables.

        Validates:
        1. Anime episodes in commercial_injector_final trace back to Toonami_Episodes
        2. Episodes have valid source paths (accounting for cutless vs traditional)
        """
        if not self.check_table_exists("Toonami_Episodes"):
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                "Cannot validate episode references",
                "Toonami_Episodes table not found - this is unusual",
                "ToonamiChecker should have created this table"
            )
            return

        # Get all anime episodes from final lineup
        final_data = self.get_all_rows("commercial_injector_final")
        anime_episodes = [
            entry for entry in final_data
            if self.is_anime(entry.get('FULL_FILE_PATH', ''))
        ]

        if not anime_episodes:
            # No anime in final lineup - might be early in pipeline
            result.metadata["orphaned_episodes"] = 0
            return

        # Get all source episodes
        source_episodes = self.get_all_rows("Toonami_Episodes")
        source_paths = {ep.get('Full_File_Path') for ep in source_episodes if ep.get('Full_File_Path')}

        # Build episode info index from source (for traditional mode matching)
        source_episode_info = set()
        for path in source_paths:
            info = self.extract_episode_info(path)
            if info:
                # Create a normalized key
                source_episode_info.add((info['season'], info['episode']))

        # Check for orphaned episodes
        orphaned = []
        for entry in anime_episodes:
            path = entry.get('FULL_FILE_PATH', '')
            is_orphaned = False

            # For cutless mode, check ORIGINAL_FILE_PATH if available
            if 'ORIGINAL_FILE_PATH' in entry:
                original_path = entry.get('ORIGINAL_FILE_PATH', '')
                if original_path and original_path not in source_paths:
                    is_orphaned = True
                    orphaned.append({
                        'path': path,
                        'original': original_path,
                        'block_id': entry.get('BLOCK_ID'),
                        'mode': 'cutless'
                    })
            else:
                # Traditional mode - extract episode info and match
                episode_info = self.extract_episode_info(path)
                if episode_info:
                    key = (episode_info['season'], episode_info['episode'])
                    if key not in source_episode_info:
                        is_orphaned = True
                        orphaned.append({
                            'path': path,
                            'episode_info': f"S{episode_info['season']}E{episode_info['episode']}",
                            'block_id': entry.get('BLOCK_ID'),
                            'mode': 'traditional'
                        })

        # Report findings
        if orphaned:
            orphan_ratio = len(orphaned) / len(anime_episodes)

            if orphan_ratio > ORPHAN_ERROR_THRESHOLD:
                level = ValidationLevel.ERROR
            elif orphan_ratio > ORPHAN_WARNING_THRESHOLD:
                level = ValidationLevel.WARNING
            else:
                level = ValidationLevel.INFO

            self.add_issue(
                result,
                level,
                f"{len(orphaned)} episode(s) in final lineup not found in source ({orphan_ratio:.1%})",
                f"Example: {orphaned[0].get('path', 'unknown')}",
                "This may indicate the source library changed after processing started"
            )

        result.metadata["orphaned_episodes"] = len(orphaned)
        result.metadata["total_final_episodes"] = len(anime_episodes)

    def _validate_block_id_references(self, result: ValidationResult):
        """
        Check that BLOCK_IDs reference actual episodes and contain anime content.

        Validates:
        1. All BLOCK_IDs contain at least one anime episode
        2. No BLOCK_IDs exist with only bumps
        """
        final_data = self.get_all_rows("commercial_injector_final")

        if not final_data:
            result.metadata["empty_block_ids"] = 0
            return

        # Group by BLOCK_ID
        blocks: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for entry in final_data:
            block_id = entry.get("BLOCK_ID")
            if block_id:
                blocks[block_id].append(entry)

        # Find BLOCK_IDs with no anime content
        empty_blocks = []
        for block_id, entries in blocks.items():
            has_anime = any(
                self.is_anime(e.get('FULL_FILE_PATH', ''))
                for e in entries
            )
            if not has_anime:
                empty_blocks.append({
                    'block_id': block_id,
                    'entry_count': len(entries),
                    'sample_path': entries[0].get('FULL_FILE_PATH', '') if entries else ''
                })

        if empty_blocks:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{len(empty_blocks)} BLOCK_ID(s) contain no anime content",
                f"BLOCK_IDs should represent episodes. Example: '{empty_blocks[0]['block_id']}' has {empty_blocks[0]['entry_count']} entries but no anime",
                "Re-run BlockMaker to fix BLOCK_ID assignments",
                table="commercial_injector_final"
            )

        result.metadata["empty_block_ids"] = len(empty_blocks)
        result.metadata["total_block_ids"] = len(blocks)

    def _validate_show_consistency(self, result: ValidationResult):
        """
        Check that show names are consistent across tables.

        Validates:
        1. Shows in lineup_prep_out exist in Toonami_Shows (informational)
        2. Show name mapping is working

        Note: This is INFO level because it's normal to have bumps for shows
        not yet in your library.
        """
        if not self.check_table_exists("lineup_prep_out"):
            result.metadata["orphaned_bump_shows"] = 0
            return

        if not self.check_table_exists("Toonami_Shows"):
            result.metadata["orphaned_bump_shows"] = 0
            return

        lineup_bumps = self.get_all_rows("lineup_prep_out")
        source_shows = self.get_all_rows("Toonami_Shows")

        # Extract unique show names from bumps
        # Import here to avoid circular dependencies
        try:
            from ToonamiTools.utils import show_name_mapper

            bump_shows: Set[str] = set()
            for bump in lineup_bumps:
                # Check all SHOW_NAME_X columns
                for i in range(1, 4):  # SHOW_NAME_1, SHOW_NAME_2, SHOW_NAME_3
                    show_name = bump.get(f'SHOW_NAME_{i}', '')
                    if show_name:
                        mapped = show_name_mapper.map(show_name, strategy='all')
                        cleaned = show_name_mapper.clean(mapped, mode='matching')
                        if cleaned:
                            bump_shows.add(cleaned)

            # Extract show names from source
            source_show_names: Set[str] = set()
            for show in source_shows:
                show_name = show.get('Show', '')
                if show_name:
                    mapped = show_name_mapper.map(show_name, strategy='all')
                    cleaned = show_name_mapper.clean(mapped, mode='matching')
                    if cleaned:
                        source_show_names.add(cleaned)

            # Find bumps for shows not in library
            orphaned_shows = bump_shows - source_show_names

            if orphaned_shows:
                # Truncate list if too long
                show_list = ', '.join(sorted(list(orphaned_shows))[:10])
                if len(orphaned_shows) > 10:
                    show_list += f" ... and {len(orphaned_shows) - 10} more"

                self.add_issue(
                    result,
                    ValidationLevel.INFO,
                    f"{len(orphaned_shows)} show(s) have bumps but no episodes",
                    f"Shows: {show_list}",
                    "This is normal if you have bumps for shows not yet in your library",
                    table="lineup_prep_out"
                )

            result.metadata["orphaned_bump_shows"] = len(orphaned_shows)
            result.metadata["bump_show_count"] = len(bump_shows)
            result.metadata["source_show_count"] = len(source_show_names)

        except ImportError:
            # show_name_mapper not available - skip this check
            result.metadata["orphaned_bump_shows"] = 0
