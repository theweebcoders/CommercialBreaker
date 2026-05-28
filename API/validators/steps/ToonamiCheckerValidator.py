"""
ToonamiChecker Validator

Validates the output of the ToonamiChecker step, which identifies Toonami shows
in the user's anime library and creates the foundational tables for processing.

Tables Validated:
- Toonami_Episodes: List of all episode files from selected shows
- Toonami_Shows: List of all shows selected for processing
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class ToonamiCheckerValidator(BaseValidator):
    """Validates ToonamiChecker step output"""

    @property
    def step_name(self) -> str:
        return "ToonamiChecker"

    @property
    def required_tables(self) -> list:
        return ["Toonami_Episodes", "Toonami_Shows"]

    @property
    def pipeline_order(self) -> int:
        return 3  # Third step in pipeline

    def validate(self) -> ValidationResult:
        """
        Validate ToonamiChecker output.

        Checks:
        1. Required tables exist
        2. Tables have data
        3. Episode files follow naming convention
        4. File paths are properly stored
        5. Show/episode relationship is valid
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check Toonami_Episodes table
        if not self.validate_table_structure(
            result,
            "Toonami_Episodes",
            required_columns=["Title", "Episode", "Full_File_Path"],
            min_rows=1
        ):
            # Critical issues found, mark as not completed
            return result

        # Check Toonami_Shows table
        if not self.validate_table_structure(
            result,
            "Toonami_Shows",
            required_columns=["Title"],
            min_rows=1
        ):
            # Critical issues found, mark as not completed
            return result

        # If we get here, tables exist and have basic structure
        result.is_completed = True

        # Validate episode data quality
        self._validate_episodes(result)

        # Validate show data quality
        self._validate_shows(result)

        # Cross-validate shows and episodes
        self._validate_show_episode_relationship(result)

        return result

    def _validate_episodes(self, result: ValidationResult):
        """
        Validate episode data quality.

        Args:
            result: ValidationResult to add issues to
        """
        episodes = self.get_all_rows("Toonami_Episodes")

        # Track issues
        missing_paths = 0
        invalid_patterns = 0
        missing_titles = 0

        for i, episode in enumerate(episodes):
            # Check for full file path
            file_path = episode.get("Full_File_Path", "")
            if not file_path:
                missing_paths += 1

            # Check if path is a bump (should only contain anime episodes)
            if file_path and self.is_bump(file_path):
                invalid_patterns += 1

            # Check for title
            title = episode.get("Title", "")
            if not title:
                missing_titles += 1

        # Report issues
        if missing_paths > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_paths} episode(s) missing file paths",
                f"Found {missing_paths}/{len(episodes)} episodes without Full_File_Path",
                "Re-run ToonamiChecker to rebuild episode list",
                table="Toonami_Episodes"
            )

        if invalid_patterns > 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{invalid_patterns} episode(s) have non-standard naming",
                f"Expected format: [SHOW] - S##E## - [title].ext",
                "Check file naming convention in anime library",
                table="Toonami_Episodes"
            )

        if missing_titles > 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{missing_titles} episode(s) missing show title",
                f"Found {missing_titles}/{len(episodes)} episodes without Title",
                "Re-run ToonamiChecker to rebuild episode list",
                table="Toonami_Episodes"
            )

        # Add metadata
        result.metadata["episodes_total"] = len(episodes)
        result.metadata["episodes_valid"] = len(episodes) - invalid_patterns

    def _validate_shows(self, result: ValidationResult):
        """
        Validate show data quality.

        Args:
            result: ValidationResult to add issues to
        """
        shows = self.get_all_rows("Toonami_Shows")

        missing_titles = sum(1 for show in shows if not show.get("Title", ""))

        if missing_titles > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_titles} show(s) missing title",
                f"Found {missing_titles}/{len(shows)} shows without Title",
                "Re-run ToonamiChecker to rebuild show list",
                table="Toonami_Shows"
            )

        # Add metadata
        result.metadata["shows_total"] = len(shows)

    def _validate_show_episode_relationship(self, result: ValidationResult):
        """
        Validate that all shows in Toonami_Shows have corresponding episodes.

        Args:
            result: ValidationResult to add issues to
        """
        shows = self.get_all_rows("Toonami_Shows")
        episodes = self.get_all_rows("Toonami_Episodes")

        # Build set of show titles from episodes
        episode_titles = set(ep.get("Title", "") for ep in episodes if ep.get("Title"))

        # Check if each show has episodes
        shows_without_episodes = []
        for show in shows:
            title = show.get("Title", "")
            if title and title not in episode_titles:
                shows_without_episodes.append(title)

        if shows_without_episodes:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{len(shows_without_episodes)} show(s) have no episodes",
                f"Shows without episodes: {', '.join(shows_without_episodes[:5])}{'...' if len(shows_without_episodes) > 5 else ''}",
                "This may indicate a problem with file naming or show matching",
                table="Toonami_Shows"
            )

        result.metadata["shows_with_episodes"] = len(shows) - len(shows_without_episodes)
