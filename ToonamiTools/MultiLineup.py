import random
import config
from API.utils import get_db_manager
from API.utils.ErrorManager import get_error_manager


class Multilineup:
    def __init__(self, post_cut: bool = False):
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        self.next_show_name = None
        self.used_rows = set()
        self.recent_shows = []
        self.post_cut = post_cut
        self.source_suffix = '_postcut' if post_cut else ''
        self.reordered_suffix = '_reordered_postcut' if post_cut else '_reordered'

    def weighted_selection(self, data):
        """Select one row from data using weights based on recent shows"""
        if not data:
            return None

        weights = []
        for row in data:
            if row.get("SHOW_NAME_1") in self.recent_shows or row.get("SHOW_NAME_2") in self.recent_shows:
                weights.append(0.5)  # Lower weight if show is in recent_shows
            else:
                weights.append(1)

        # Use random.choices with weights
        selected = random.choices(data, weights=weights, k=1)[0]
        return selected

    def unused_bumps(self, table_name):
        """Get all rows from table that haven't been used yet"""
        all_data = self.db_manager.fetchall_as_dicts(f"SELECT rowid, * FROM {table_name}")

        # Filter out used rows (by rowid)
        unused = [row for row in all_data if row['rowid'] not in self.used_rows]
        return unused

    def get_next_row(self, table_name):
        """Get the next optimal bump based on show transitions"""
        data = self.unused_bumps(table_name)
        next_row = None
        last_resort_row = None

        if self.next_show_name:
            # Get all possible next rows
            possible_next_rows = [row for row in data
                                if row.get('PLACEMENT_2') == 'next' and
                                row.get('SHOW_NAME_1') == self.next_show_name]

            if possible_next_rows:
                # Count occurrences of each SHOW_NAME_3
                show_name_3_counts = {}
                for row in possible_next_rows:
                    sn3 = row.get('SHOW_NAME_3')
                    if sn3:
                        show_name_3_counts[sn3] = show_name_3_counts.get(sn3, 0) + 1

                if show_name_3_counts:
                    # Sort SHOW_NAME_3 by count (ascending)
                    sorted_show_name_3 = sorted(show_name_3_counts.keys(), key=lambda x: show_name_3_counts[x])

                    for show_name_3 in sorted_show_name_3:
                        # Check if there is at least one bump with SHOW_NAME_1 in the remaining bumps
                        has_follow_up = any(row.get('SHOW_NAME_1') == show_name_3 for row in data)

                        if has_follow_up:
                            candidates = [row for row in possible_next_rows if row.get('SHOW_NAME_3') == show_name_3]
                            if candidates:
                                next_row = self.weighted_selection(candidates)
                                break
                        elif last_resort_row is None:
                            # Store the first available bump as a last resort
                            candidates = [row for row in possible_next_rows if row.get('SHOW_NAME_3') == show_name_3]
                            if candidates:
                                last_resort_row = candidates[0]

            if next_row is None:
                possible_next_rows = [row for row in data
                                    if row.get('PLACEMENT_2') == 'next from' and
                                    row.get('SHOW_NAME_2') == self.next_show_name]
                if possible_next_rows:
                    next_row = self.weighted_selection(possible_next_rows)

            if next_row is None:
                possible_next_rows = [row for row in data
                                    if row.get('PLACEMENT_2') == 'from' and
                                    row.get('SHOW_NAME_2') == self.next_show_name]
                if possible_next_rows:
                    next_row = self.weighted_selection(possible_next_rows)

        if next_row is None:
            if last_resort_row is not None:
                # Use the last resort row if no better bump was found
                next_row = last_resort_row
            else:
                # Random selection as last resort
                if data:
                    next_row = self.weighted_selection(data)
                else:
                    return None, None

        rowid = next_row['rowid']

        if next_row.get('PLACEMENT_2') == 'next':
            self.next_show_name = next_row.get('SHOW_NAME_3')
        else:
            self.next_show_name = next_row.get('SHOW_NAME_1')

        self.used_rows.add(rowid)
        return next_row, rowid

    def write_to_table(self, next_row, table_name):
        """Write a bump row to the reordered table"""
        try:
            # Remove rowid before saving (it's just for tracking)
            row_to_save = {k: v for k, v in next_row.items() if k != 'rowid'}

            # Check if table exists, create if not
            if not self.db_manager.table_exists(table_name):
                # Create empty table with first row's structure
                self.db_manager.replace_table_data(table_name, [row_to_save])
            else:
                # Append the row using raw SQL (since replace_table_data would overwrite)
                with self.db_manager.transaction() as conn:
                    columns = list(row_to_save.keys())
                    placeholders = ','.join(['?' for _ in columns])
                    conn.execute(
                        f"INSERT INTO {table_name} VALUES ({placeholders})",
                        tuple(row_to_save[col] for col in columns)
                    )
        except Exception as e:
            self.error_manager.send_error_level(
                source="Multilineup",
                operation="write_to_table",
                message=f"Failed to save reordered bump to {table_name}",
                details=str(e),
                suggestion="There was an error while trying to save the bump to the database. Please check that the database still exists and is accessible."
            )
            raise

        if next_row.get('PLACEMENT_2') == 'next':
            self.next_show_name = next_row.get('SHOW_NAME_3')
        else:
            self.next_show_name = next_row.get('SHOW_NAME_1')

        self.recent_shows.append(self.next_show_name)
        if len(self.recent_shows) > 5:  # Limit the recent shows to last 5
            self.recent_shows.pop(0)

    def find_optimal_first_bump(self, data):
        """Find the best starting bump for the reordered sequence"""
        if not data:
            print("Warning: Empty data passed to find_optimal_first_bump")
            return None

        # Count occurrences of SHOW_NAME_1 and SHOW_NAME_3
        show_name_1_counts = {}
        show_name_3_counts = {}

        for row in data:
            sn1 = row.get('SHOW_NAME_1')
            sn3 = row.get('SHOW_NAME_3')

            if sn1:
                show_name_1_counts[sn1] = show_name_1_counts.get(sn1, 0) + 1
            if sn3:
                show_name_3_counts[sn3] = show_name_3_counts.get(sn3, 0) + 1

        optimal_first_bump = None

        # Situation 1: SHOW_NAME_1 is no other bump's SHOW_NAME_3 and SHOW_NAME_3 is another bump's SHOW_NAME_1
        for row in data:
            sn3 = row.get('SHOW_NAME_3')
            if sn3 is None:  # Skip rows where SHOW_NAME_3 is None
                continue

            sn1 = row.get('SHOW_NAME_1')
            if show_name_3_counts.get(sn1, 0) == 0 and show_name_1_counts.get(sn3, 0) > 0:
                optimal_first_bump = row
                break

        # Situation 2: SHOW_NAME_1 is one more than bumps with that SHOW_NAME_3 and SHOW_NAME_3 is another bump's SHOW_NAME_1
        if optimal_first_bump is None:
            for row in data:
                sn3 = row.get('SHOW_NAME_3')
                if sn3 is None:  # Skip rows where SHOW_NAME_3 is None
                    continue

                sn1 = row.get('SHOW_NAME_1')
                if (show_name_3_counts.get(sn1, 0) + 1 == show_name_1_counts.get(sn1, 0) and
                    show_name_1_counts.get(sn3, 0) > 0):
                    optimal_first_bump = row
                    break

        # Situation 3: No such bump as in situation 1 or 2 exists, but a bump where SHOW_NAME_1 is multiple other bump's SHOW_NAME_3
        if optimal_first_bump is None:
            for row in data:
                sn3 = row.get('SHOW_NAME_3')
                if sn3 is None:  # Skip rows where SHOW_NAME_3 is None
                    continue

                sn1 = row.get('SHOW_NAME_1')
                if show_name_3_counts.get(sn1, 0) > 1:
                    optimal_first_bump = row
                    break

        # If no optimal bump found, return the first one
        if optimal_first_bump is None:
            optimal_first_bump = data[0]

        return optimal_first_bump

    def reorder_table(self, base_table_name):
        """Reorder a table of bumps to create optimal show transitions"""
        self.used_rows = set()  # Resetting used rows for the new table
        source_table_name = base_table_name + self.source_suffix
        reordered_table_name = base_table_name + self.reordered_suffix

        if not self.db_manager.table_exists(source_table_name):
            print(f"Table {source_table_name} does not exist. Moving to the next table.")
            if self.db_manager.table_exists(reordered_table_name):
                self.db_manager.drop_table(reordered_table_name)
            return

        print(f"Starting reordering for {source_table_name}")

        unused_data = self.unused_bumps(source_table_name)
        first_bump = self.find_optimal_first_bump(unused_data)

        if first_bump is not None:
            self.write_to_table(first_bump, reordered_table_name)
            self.used_rows.add(first_bump['rowid'])
            unused_data = self.unused_bumps(source_table_name)  # Refresh unused rows

        while unused_data:
            next_row, rowid = self.get_next_row(source_table_name)
            if next_row is None:
                break
            self.write_to_table(next_row, reordered_table_name)
            unused_data = self.unused_bumps(source_table_name)  # Refresh unused rows

        print(f"Finished reordering for {source_table_name}")

    def reorder_all_tables(self):
        """Reorder all multibumps tables (v0 through v9)"""
        for i in range(10):
            table_name = 'multibumps_v' + str(i) + '_data'
            try:
                self.reorder_table(table_name)
            except Exception as e:
                print(f"Error reordering {table_name}: {e}. Moving to the next table.")
