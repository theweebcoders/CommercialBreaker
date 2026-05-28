"""
CommercialInjector Validator

Validates the output of the CommercialInjector and BlockMaker steps, which
insert bumps between episode segments and assign BLOCK_IDs to keep related content together.

Tables Validated:
- commercial_injector: Episodes with injected bumps
- commercial_injector_final: Final output with BLOCK_IDs
"""

from typing import Dict, List, Any
from collections import defaultdict

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel
from API.validators.utils import is_generic_bump


class CommercialInjectorValidator(BaseValidator):
    """Validates CommercialInjector and BlockMaker step output"""

    @property
    def step_name(self) -> str:
        return "CommercialInjector/BlockMaker"

    @property
    def required_tables(self) -> list:
        return ["commercial_injector_final"]

    @property
    def optional_tables(self) -> list:
        return ["commercial_injector"]

    @property
    def pipeline_order(self) -> int:
        return 13  # Thirteenth/fourteenth step in pipeline

    def validate(self) -> ValidationResult:
        """
        Validate CommercialInjector/BlockMaker output.

        Checks:
        1. commercial_injector_final exists and has data
        2. BLOCK_ID column is present and populated
        3. Episodes and bumps are properly interleaved
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check final table
        if not self.validate_table_structure(
            result,
            "commercial_injector_final",
            required_columns=["FULL_FILE_PATH", "BLOCK_ID"],
            min_rows=1
        ):
            return result

        result.is_completed = True

        # Validate final data
        self._validate_final_data(result)

        # Validate interleaving pattern
        self._validate_interleaving_pattern(result)

        # Check intermediate table if it exists
        if self.check_table_exists("commercial_injector"):
            self._validate_intermediate_data(result)

        return result

    def _validate_final_data(self, result: ValidationResult):
        """
        Validate commercial_injector_final data.

        Args:
            result: ValidationResult to add issues to
        """
        final_data = self.get_all_rows("commercial_injector_final")

        missing_paths = 0
        missing_block_ids = 0

        for entry in final_data:
            if not entry.get("FULL_FILE_PATH"):
                missing_paths += 1
            if not entry.get("BLOCK_ID"):
                missing_block_ids += 1

        if missing_paths > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_paths} entry/entries missing file path",
                f"Found {missing_paths}/{len(final_data)} entries without FULL_FILE_PATH",
                "Re-run CommercialInjector/BlockMaker",
                table="commercial_injector_final"
            )

        if missing_block_ids > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_block_ids} entry/entries missing BLOCK_ID",
                f"Found {missing_block_ids}/{len(final_data)} entries without BLOCK_ID",
                "Re-run BlockMaker to assign BLOCK_IDs",
                table="commercial_injector_final"
            )

        # Count anime episodes vs bumps
        anime_count = sum(1 for e in final_data if e.get("FULL_FILE_PATH") and self.is_anime(e.get("FULL_FILE_PATH")))
        bump_count = len(final_data) - anime_count

        result.metadata["total_entries"] = len(final_data)
        result.metadata["anime_segments"] = anime_count
        result.metadata["bumps"] = bump_count
        result.metadata["unique_block_ids"] = len(set(e.get("BLOCK_ID") for e in final_data if e.get("BLOCK_ID")))

    def _validate_intermediate_data(self, result: ValidationResult):
        """
        Validate commercial_injector intermediate data (if exists).

        Args:
            result: ValidationResult to add issues to
        """
        injector_data = self.get_all_rows("commercial_injector")
        result.metadata["intermediate_entries"] = len(injector_data)

        if len(injector_data) == 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                "Intermediate commercial_injector table is empty",
                "This table should contain data from bump injection",
                "This is unusual but may not affect final output",
                table="commercial_injector"
            )

    def _validate_interleaving_pattern(self, result: ValidationResult):
        """
        Validate bump/anime interleaving pattern in commercial_injector_final.

        Expected pattern for each BLOCK_ID:
        - Intro bump (optional, starts episode)
        - Anime part 1
        - To Ads bump (if not last part)
        - Back bump (if not last part)
        - Anime part 2
        - ...continues for each part

        Generic bumps (with keywords like 'generic', 'clydes', 'robot') are
        allowed anywhere and don't violate the pattern.

        Args:
            result: ValidationResult to add issues to
        """
        final_data = self.get_all_rows("commercial_injector_final")

        if not final_data:
            return

        # Group by BLOCK_ID to validate each episode separately
        blocks: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for idx, entry in enumerate(final_data):
            block_id = entry.get("BLOCK_ID")
            if block_id:
                entry['_index'] = idx  # Track original index for error reporting
                blocks[block_id].append(entry)

        violations = []

        for block_id, entries in blocks.items():
            # Identify anime parts and their positions
            anime_positions = []
            bump_positions = []

            for i, entry in enumerate(entries):
                path = entry.get('FULL_FILE_PATH', '')
                if self.is_anime(path):
                    anime_positions.append({'pos': i, 'path': path, 'index': entry['_index']})
                else:
                    bump_positions.append({'pos': i, 'path': path, 'index': entry['_index']})

            # Skip blocks with no anime (already caught by ReferentialIntegrityValidator)
            if not anime_positions:
                continue

            # Check pattern for each anime part
            for i, anime_info in enumerate(anime_positions):
                anime_pos = anime_info['pos']
                is_first_part = (i == 0)
                is_last_part = (i == len(anime_positions) - 1)

                # Check if preceded by appropriate bump (unless it's the first entry)
                if anime_pos > 0:
                    prev_entry = entries[anime_pos - 1]
                    prev_path = prev_entry.get('FULL_FILE_PATH', '').lower()

                    # Skip check if it's a generic bump (allowed anywhere)
                    if not is_generic_bump(prev_path):
                        # For first anime part, expect intro bump
                        if is_first_part:
                            if 'intro' not in prev_path and 'now' not in prev_path:
                                violations.append({
                                    'block_id': block_id,
                                    'row': prev_entry['_index'],
                                    'issue': f'First anime part not preceded by intro bump',
                                    'path': prev_path,
                                    'severity': 'WARNING'  # Warning since show might not have intro bumps
                                })
                        else:
                            # For subsequent parts, expect "back" bump
                            if 'back' not in prev_path:
                                violations.append({
                                    'block_id': block_id,
                                    'row': prev_entry['_index'],
                                    'issue': f'Anime part {i+1} not preceded by "back" bump',
                                    'path': prev_path,
                                    'severity': 'WARNING'
                                })

                # Check if followed by appropriate bumps (unless last part)
                if not is_last_part and anime_pos < len(entries) - 1:
                    next_entry = entries[anime_pos + 1]
                    next_path = next_entry.get('FULL_FILE_PATH', '').lower()

                    # Skip check if it's another anime part (will be caught as missing bumps)
                    if self.is_anime(next_entry.get('FULL_FILE_PATH', '')):
                        violations.append({
                            'block_id': block_id,
                            'row': anime_info['index'],
                            'issue': f'Anime part {i+1} directly followed by another anime part (missing bumps)',
                            'path': anime_info['path'],
                            'severity': 'ERROR'
                        })
                    # Skip check if it's a generic bump
                    elif not is_generic_bump(next_path):
                        # Expect "to ads" bump
                        if 'to ads' not in next_path and 'to ad' not in next_path:
                            violations.append({
                                'block_id': block_id,
                                'row': next_entry['_index'],
                                'issue': f'Anime part {i+1} not followed by "to ads" bump',
                                'path': next_path,
                                'severity': 'WARNING'
                            })

        # Report violations
        if violations:
            # Separate by severity
            errors = [v for v in violations if v['severity'] == 'ERROR']
            warnings = [v for v in violations if v['severity'] == 'WARNING']

            if errors:
                first = errors[0]
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    f"{len(errors)} critical interleaving pattern violation(s)",
                    f"Example: {first['issue']} in BLOCK_ID '{first['block_id']}'",
                    "Re-run CommercialInjector to properly interleave bumps between anime segments",
                    table="commercial_injector_final",
                    row_index=first['row']
                )
                result.is_valid = False

            if warnings:
                first = warnings[0]
                self.add_issue(
                    result,
                    ValidationLevel.WARNING,
                    f"{len(warnings)} interleaving pattern irregularity/irregularities",
                    f"Example: {first['issue']} in BLOCK_ID '{first['block_id']}'",
                    "This may be normal if using generic bumps or if show lacks specific bump types. Verify bump placement is correct.",
                    table="commercial_injector_final",
                    row_index=first['row']
                )

        result.metadata["interleaving_errors"] = len([v for v in violations if v['severity'] == 'ERROR'])
        result.metadata["interleaving_warnings"] = len([v for v in violations if v['severity'] == 'WARNING'])
