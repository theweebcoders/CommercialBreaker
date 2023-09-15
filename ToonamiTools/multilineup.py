import pandas as pd
import sqlite3
import random

class Multilineup:
    def __init__(self):
        db_path = 'toonami.db'
        self.conn = sqlite3.connect(db_path)
        
    def get_next_row(self, df, conditions, recent_shows):
        original_index = df.index  # Capture original index
        df = df.reset_index(drop=True)  # Reset index for alignment
        mask = pd.Series([True] * len(df))
        
        for key, value in conditions.items():
            if key == "PLACEMENT_2":
                mask &= df[key].apply(lambda x: str(x).lower() if x is not None else x) == value.lower()
            else:
                mask &= df[key] == value

        df_subset = df.loc[mask]
        
        if not df_subset.empty:
            # Select a row based on the recent_shows for weighting
            selected_row = self.weighted_selection(df_subset, recent_shows)
            return selected_row, original_index[df_subset.index[df_subset["SHOW_NAME_1"] == selected_row["SHOW_NAME_1"]][0]]
        
        return None, None
    
    def weighted_selection(self, df_subset, recent_shows):
        # Assigning weights
        weights = []
        rows_list = list(df_subset.iterrows())
        for _, row in rows_list:
            if row["SHOW_NAME_1"] in recent_shows or row["SHOW_NAME_2"] in recent_shows:
                weights.append(0.5)  # Lower weight if show is in recent_shows
            else:
                weights.append(1)

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        return random.choices(rows_list, weights=normalized_weights, k=1)[0][1]

    def reorder_table(self, table_name):
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)

        reordered_rows = []
        used_rows = []
        recent_shows = []  # To keep track of recently used shows

        # Initialize first show
        SHOW_C = None

        while len(used_rows) < len(df):
            next_row, original_row_index = self.get_next_row(df.drop(used_rows), {"PLACEMENT_2": "next", "SHOW_NAME_1": SHOW_C}, recent_shows)

            if next_row is None:
                next_row, original_row_index = self.get_next_row(df.drop(used_rows), {"SHOW_NAME_2": SHOW_C, "PLACEMENT_2": "next from"}, recent_shows)

            if next_row is None:
                next_row, original_row_index = self.get_next_row(df.drop(used_rows), {"SHOW_NAME_2": SHOW_C, "PLACEMENT_2": "from"}, recent_shows)

            if next_row is None:
                # Randomly select an unused row
                next_row, original_row_index = self.get_next_row(df.drop(used_rows).sample(n=1), {}, recent_shows)
                SHOW_C = next_row["SHOW_NAME_1"]

            # Append matched row and update recent shows
            reordered_rows.append(next_row)
            used_rows.append(original_row_index)
            recent_shows.append(SHOW_C)
            if len(recent_shows) > 5:  # Limit the recent shows to last 5
                recent_shows.pop(0)

            if next_row["PLACEMENT_2"] == "next":
                SHOW_C = next_row["SHOW_NAME_3"]
            elif next_row["PLACEMENT_2"] in ["next from", "from"]:
                SHOW_C = next_row["SHOW_NAME_1"]

        # Create and write reordered DataFrame
        reordered_df = pd.DataFrame(reordered_rows)
        reordered_df.to_sql(table_name + "_reordered", self.conn, index=False, if_exists='replace')

    def reorder_all_tables(self):
        versions = [2, 3, 8, 9]
        for ver in versions:
            table_name = f"multibumps_v{ver}_data"
            print(f"Processing table: {table_name}")
            self.reorder_table(table_name)
            print(f"Finished processing table: {table_name}")