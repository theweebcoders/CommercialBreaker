"""
LineupPrep Validator

Validates the output of the LineupPrep step, which processes bump files,
extracts metadata through regex parsing, and sorts them into usable and unusable categories.

Tables Validated:
- lineup_prep_out: Main processed bump data
- nice_list: Bumps that can be used
- naughty_list: Bumps that cannot be used
- no_match: Bumps that didn't match the naming scheme
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class LineupPrepValidator(BaseValidator):
    """Validates LineupPrep step output"""

    @property
    def step_name(self) -> str:
        return "LineupPrep"

    @property
    def required_tables(self) -> list:
        return ["lineup_prep_out"]

    @property
    def optional_tables(self) -> list:
        return ["nice_list", "naughty_list", "no_match"]

    @property
    def pipeline_order(self) -> int:
        return 4  # Fourth step in pipeline

    def validate(self) -> ValidationResult:
        """
        Validate LineupPrep output.

        Checks:
        1. lineup_prep_out exists and has data
        2. Required columns are present
        3. Bump metadata is properly parsed
        4. File paths are valid
        5. Show names are populated
        6. Optional sorting tables exist
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Required columns for lineup_prep_out
        required_columns = [
            "AD_VERSION",
            "COLOR",
            "FULL_FILE_PATH",
            "PLACEMENT_1",
            "PLACEMENT_2",
            "PLACEMENT_3",
            "PLACEMENT_4",
            "SHOW_NAME_1",
            "SHOW_NAME_2",
            "SHOW_NAME_3",
            "SPECIAL_SHOW_NAME",
            "TOONAMI_VERSION"
        ]

        # Check main table
        if not self.validate_table_structure(
            result,
            "lineup_prep_out",
            required_columns=required_columns,
            min_rows=1
        ):
            # Critical issues found
            return result

        # If we get here, table exists and has basic structure
        result.is_completed = True

        # Validate bump data quality
        self._validate_bump_data(result)

        # Check optional sorting tables
        self._validate_sorting_tables(result)

        return result

    def _validate_bump_data(self, result: ValidationResult):
        """
        Validate bump data quality in lineup_prep_out.

        Args:
            result: ValidationResult to add issues to
        """
        bumps = self.get_all_rows("lineup_prep_out")

        # Track issues
        missing_paths = 0
        missing_show_names = 0
        missing_versions = 0
        missing_placements = 0
        missing_placement_examples = []

        for i, bump in enumerate(bumps):
            file_path = bump.get("FULL_FILE_PATH", "")

            # Check file path
            if not file_path:
                missing_paths += 1

            # Check if at least one show name is populated
            has_show_name = any([
                bump.get("SHOW_NAME_1"),
                bump.get("SHOW_NAME_2"),
                bump.get("SHOW_NAME_3"),
                bump.get("SPECIAL_SHOW_NAME")
            ])
            if not has_show_name:
                missing_show_names += 1

            # Check version
            if not bump.get("TOONAMI_VERSION"):
                missing_versions += 1

            # Check if at least one placement is populated
            has_placement = any([
                bump.get("PLACEMENT_1"),
                bump.get("PLACEMENT_2"),
                bump.get("PLACEMENT_3"),
                bump.get("PLACEMENT_4")
            ])
            if not has_placement:
                missing_placements += 1
                # Track up to 5 examples
                if len(missing_placement_examples) < 5:
                    missing_placement_examples.append(file_path.split('/')[-1])

        # Report issues
        if missing_paths > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_paths} bump(s) missing file paths",
                f"Found {missing_paths}/{len(bumps)} bumps without FULL_FILE_PATH",
                "Re-run LineupPrep to rebuild bump data",
                table="lineup_prep_out"
            )

        if missing_show_names > 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{missing_show_names} bump(s) missing show names",
                f"Found {missing_show_names}/{len(bumps)} bumps without any show name",
                "These may be generic bumps or parsing may have failed",
                table="lineup_prep_out"
            )

        if missing_versions > 0:
            self.add_issue(
                result,
                ValidationLevel.INFO,
                f"{missing_versions} bump(s) missing Toonami version",
                f"Found {missing_versions}/{len(bumps)} bumps without TOONAMI_VERSION (these are OG/original bumps)",
                "This is normal for original Toonami bumps without version numbers",
                table="lineup_prep_out"
            )

        if missing_placements > 0:
            example_text = f"Examples: {', '.join(missing_placement_examples[:3])}" if missing_placement_examples else ""
            self.add_issue(
                result,
                ValidationLevel.INFO,
                f"{missing_placements} bump(s) missing PLACEMENT columns",
                f"Table: lineup_prep_out | Found {missing_placements}/{len(bumps)} bumps without PLACEMENT_1/2/3/4 data (likely generic filler bumps). {example_text}",
                "Generic bumps (Clydes, Robot) can be used as filler without specific placement",
                table="lineup_prep_out"
            )

        # Count bump types
        single_bumps = sum(1 for b in bumps if b.get("SHOW_NAME_1") and not b.get("SHOW_NAME_2"))
        double_bumps = sum(1 for b in bumps if b.get("SHOW_NAME_1") and b.get("SHOW_NAME_2") and not b.get("SHOW_NAME_3"))
        triple_bumps = sum(1 for b in bumps if b.get("SHOW_NAME_1") and b.get("SHOW_NAME_2") and b.get("SHOW_NAME_3"))

        # Add metadata
        result.metadata["total_bumps"] = len(bumps)
        result.metadata["single_bumps"] = single_bumps
        result.metadata["double_bumps"] = double_bumps
        result.metadata["triple_bumps"] = triple_bumps

    def _validate_sorting_tables(self, result: ValidationResult):
        """
        Validate optional sorting tables (nice_list, naughty_list, no_match).

        Args:
            result: ValidationResult to add issues to
        """
        # Check if sorting tables exist
        has_nice_list = self.check_table_exists("nice_list")
        has_naughty_list = self.check_table_exists("naughty_list")
        has_no_match = self.check_table_exists("no_match")

        if has_nice_list:
            nice_count = self.get_row_count("nice_list")
            result.metadata["nice_list_count"] = nice_count

            if nice_count == 0:
                self.add_issue(
                    result,
                    ValidationLevel.WARNING,
                    "Nice list is empty",
                    "No bumps were classified as usable",
                    "Check that bump files match shows in Toonami_Shows",
                    table="nice_list"
                )

        if has_naughty_list:
            naughty_count = self.get_row_count("naughty_list")
            result.metadata["naughty_list_count"] = naughty_count

            if naughty_count > 0:
                self.add_issue(
                    result,
                    ValidationLevel.INFO,
                    f"{naughty_count} bump(s) marked as unusable",
                    "These bumps reference shows not in your library or have other issues",
                    "This is normal if you don't have all Toonami shows",
                    table="naughty_list"
                )

        if has_no_match:
            no_match_count = self.get_row_count("no_match")
            result.metadata["no_match_count"] = no_match_count

            if no_match_count > 0:
                # Get examples of files that didn't match
                no_match_rows = self.get_all_rows("no_match", limit=5)
                examples = [row.get("FULL_FILE_PATH", "").split('/')[-1] for row in no_match_rows[:3]]
                example_text = f"Examples: {', '.join(examples)}" if examples else ""

                self.add_issue(
                    result,
                    ValidationLevel.INFO,
                    f"{no_match_count} bump(s) didn't match naming scheme",
                    f"These files may be in a non-standard format. {example_text}",
                    "Check File-Naming-Conventions.md for proper bump naming",
                    table="no_match"
                )

        # Info if sorting tables don't exist
        if not (has_nice_list or has_naughty_list or has_no_match):
            self.add_issue(
                result,
                ValidationLevel.INFO,
                "Optional sorting tables not found",
                "nice_list, naughty_list, and no_match tables don't exist",
                "These are optional - LineupPrep may not have created them"
            )
