from collections import defaultdict
from API.utils import get_db_manager
from API.utils.ErrorManager import get_error_manager
import config
from .utils import show_name_mapper


class PostCutBumpFilter:
    """
    Filters multi-show bump data after the cut pipeline finishes so only shows with
    available episode blocks remain in downstream tables.
    """

    def __init__(self):
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        self.episode_table = "commercial_injector_prep"
        self.generic_names = self._normalize_name_set(config.generic_bumps)

    def _normalize_name_set(self, names):
        normalized = set()
        if not names:
            return normalized
        for name in names:
            cleaned = self._normalize_show_name(name)
            if cleaned:
                normalized.add(cleaned)
        return normalized

    def _normalize_show_name(self, show):
        if not show:
            return None
        mapped = show_name_mapper.map(str(show), strategy='all')
        return show_name_mapper.clean(mapped, mode='matching')

    def _collect_allowed_shows(self):
        if not self.db_manager.table_exists(self.episode_table):
            self.error_manager.send_error_level(
                source="PostCutBumpFilter",
                operation="run",
                message=f"Episode table '{self.episode_table}' is missing",
                details="Expected episode data produced by CommercialBreaker is not available.",
                suggestion="Ensure CommercialBreaker completed successfully before preparing the lineup."
            )
            raise RuntimeError(f"Required table '{self.episode_table}' not found.")

        rows = self.db_manager.fetchall_as_dicts(f"SELECT * FROM {self.episode_table}")
        if not rows:
            self.error_manager.send_error_level(
                source="PostCutBumpFilter",
                operation="run",
                message=f"Episode table '{self.episode_table}' is empty",
                details="No episode blocks were generated for the current run.",
                suggestion="Verify CommercialBreaker produced episode cuts before continuing."
            )
            raise RuntimeError(f"Table '{self.episode_table}' has no data.")

        allowed = set()
        for row in rows:
            raw_show = None
            if row.get("show_name"):
                raw_show = row.get("show_name")
            elif row.get("BLOCK_ID"):
                raw_show = row["BLOCK_ID"].rsplit("_S", 1)[0].replace("_", " ")
            elif row.get("SHOW_NAME_1"):
                raw_show = row.get("SHOW_NAME_1")

            normalized = self._normalize_show_name(raw_show)
            if normalized:
                allowed.add(normalized)

        return allowed

    def _missing_shows(self, row, allowed_shows):
        missing = set()
        for key in ("SHOW_NAME_1", "SHOW_NAME_2", "SHOW_NAME_3"):
            raw_show = row.get(key)
            if not raw_show:
                continue
            normalized = self._normalize_show_name(raw_show)
            if not normalized or normalized in self.generic_names:
                continue
            if normalized not in allowed_shows:
                missing.add(normalized)
        return missing

    def _filter_lineup_table(self, allowed_shows):
        if not self.db_manager.table_exists("lineup_prep_out"):
            self.error_manager.send_error_level(
                source="PostCutBumpFilter",
                operation="_filter_lineup_table",
                message="Missing lineup prep data",
                details="Expected table 'lineup_prep_out' was not found.",
                suggestion="Run Prepare Content before attempting to prepare the lineup."
            )
            raise RuntimeError("Required table 'lineup_prep_out' not found.")

        rows = self.db_manager.fetchall_as_dicts("SELECT * FROM lineup_prep_out")
        filtered_rows = []
        removed_counts = defaultdict(int)

        for row in rows:
            missing = self._missing_shows(row, allowed_shows)
            if missing:
                for show in missing:
                    removed_counts[show] += 1
                continue
            filtered_rows.append(row)

        target_table = "lineup_prep_out_postcut"
        if filtered_rows:
            self.db_manager.replace_table_data(target_table, filtered_rows)
        else:
            self.db_manager.drop_table(target_table)

        return removed_counts

    def _filter_multibump_tables(self, allowed_shows):
        removed_counts = defaultdict(int)

        for i in range(10):
            base_table = f"multibumps_v{i}_data"
            if not self.db_manager.table_exists(base_table):
                continue

            rows = self.db_manager.fetchall_as_dicts(f"SELECT * FROM {base_table}")
            filtered_rows = []

            for row in rows:
                missing = self._missing_shows(row, allowed_shows)
                if missing:
                    for show in missing:
                        removed_counts[show] += 1
                    continue
                filtered_rows.append(row)

            target_table = f"{base_table}_postcut"
            if filtered_rows:
                self.db_manager.replace_table_data(target_table, filtered_rows)
            else:
                self.db_manager.drop_table(target_table)

            # Always reset the reordered post-cut table so it can be rebuilt fresh.
            reordered_target = f"{base_table}_reordered_postcut"
            if self.db_manager.table_exists(reordered_target):
                self.db_manager.drop_table(reordered_target)

        return removed_counts

    def run(self):
        allowed_shows = self._collect_allowed_shows()
        removed_tracker = defaultdict(int)

        # Filter lineup and multibump tables
        lineup_removed = self._filter_lineup_table(allowed_shows)
        multibump_removed = self._filter_multibump_tables(allowed_shows)

        for show, count in lineup_removed.items():
            removed_tracker[show] += count
        for show, count in multibump_removed.items():
            removed_tracker[show] += count

        if removed_tracker:
            impacted = sorted(removed_tracker.items(), key=lambda item: item[1], reverse=True)
            top_entries = ", ".join(f"{show} ({count})" for show, count in impacted[:5])
            remaining = len(impacted) - 5
            extra = f", +{remaining} more" if remaining > 0 else ""
            self.error_manager.send_warning(
                source="PostCutBumpFilter",
                operation="run",
                message=f"Filtered {sum(removed_tracker.values())} multi-show bumps missing episode data",
                details=f"Top impacted shows: {top_entries}{extra}",
                suggestion="Add episode cuts for these shows or remove their multi-show bumps to avoid this warning."
            )
