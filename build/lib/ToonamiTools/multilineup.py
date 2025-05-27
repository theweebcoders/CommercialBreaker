import pandas as pd
import sqlite3
import random
import config


class Multilineup:
    def __init__(self):
        db_path = f'{config.network}.db'
        self.conn = sqlite3.connect(db_path)
        self.next_show_name = None
        self.used_rows = set()
        self.recent_shows = []
        
    def weighted_selection(self, df):
        weights = []
        for _, row in df.iterrows():
            if row["SHOW_NAME_1"] in self.recent_shows or row["SHOW_NAME_2"] in self.recent_shows:
                weights.append(0.5)  # Lower weight if show is in recent_shows
            else:
                weights.append(1)

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        return df.sample(n=1, weights=normalized_weights)

    def unused_bumps(self, table_name):
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)

        unused_df = df.drop(self.used_rows, errors='ignore')
        return unused_df
    
    def get_next_row(self, table_name):
        df = self.unused_bumps(table_name)
        next_row = None
        last_resort_row = None
        if self.next_show_name:
            # Get all possible next rows
            possible_next_rows = df[(df['PLACEMENT_2'] == 'next') & (df['SHOW_NAME_1'] == self.next_show_name)]
            if not possible_next_rows.empty:
                # Get the count of SHOW_NAME_3 for each possible next row
                show_name_3_counts = possible_next_rows['SHOW_NAME_3'].value_counts()
                if not show_name_3_counts.empty:
                    # Sort SHOW_NAME_3 by count
                    sorted_show_name_3 = show_name_3_counts.sort_values().index.tolist()
                    for show_name_3 in sorted_show_name_3:
                        # Check if there is at least one bump with SHOW_NAME_1 in the remaining bumps
                        if df[df['SHOW_NAME_1'] == show_name_3].shape[0] > 0:
                            next_row = possible_next_rows[possible_next_rows['SHOW_NAME_3'] == show_name_3]
                            if not next_row.empty:
                                next_row = self.weighted_selection(next_row)
                                break
                        elif last_resort_row is None:
                            # Store the first available bump as a last resort
                            last_resort_row = pd.DataFrame(possible_next_rows[possible_next_rows['SHOW_NAME_3'] == show_name_3].iloc[0]).transpose()
            if next_row is None:
                possible_next_rows = df[(df['PLACEMENT_2'] == 'next from') & (df['SHOW_NAME_2'] == self.next_show_name)]
                if not possible_next_rows.empty:
                    next_row = self.weighted_selection(possible_next_rows)
            if next_row is None:
                possible_next_rows = df[(df['PLACEMENT_2'] == 'from') & (df['SHOW_NAME_2'] == self.next_show_name)]
                if not possible_next_rows.empty:
                    next_row = self.weighted_selection(possible_next_rows)
        if next_row is None or next_row.empty:
            if last_resort_row is not None:
                # Use the last resort row if no better bump was found
                next_row = last_resort_row

            else:
                next_row = self.weighted_selection(df.sample(n=1))
        index = next_row.index[0]
        if next_row['PLACEMENT_2'].values[0] == 'next':
            self.next_show_name = next_row['SHOW_NAME_3'].values[0]
        else:
            self.next_show_name = next_row['SHOW_NAME_1'].values[0]
        self.used_rows.add(index)
        return next_row, index

    def write_to_table(self, next_row, table_name):
        next_row.to_sql(table_name, self.conn, if_exists='append')

        if next_row['PLACEMENT_2'].values[0] == 'next':
            self.next_show_name = next_row['SHOW_NAME_3'].values[0]
        else:
            self.next_show_name = next_row['SHOW_NAME_1'].values[0]

        self.recent_shows.append(self.next_show_name)
        if len(self.recent_shows) > 5:  # Limit the recent shows to last 5
            self.recent_shows.pop(0)

    def find_optimal_first_bump(self, df):
        show_name_1_counts = df['SHOW_NAME_1'].value_counts()
        show_name_3_counts = df['SHOW_NAME_3'].value_counts()
        optimal_first_bump = None

        # Situation 1: SHOW_NAME_1 is no other bump's SHOW_NAME_3 and SHOW_NAME_3 is another bump's SHOW_NAME_1
        for _, row in df.iterrows():
            if pd.isna(row['SHOW_NAME_3']):  # Skip rows where SHOW_NAME_3 is None
                continue
            if show_name_3_counts.get(row['SHOW_NAME_1'], 0) == 0 and show_name_1_counts.get(row['SHOW_NAME_3'], 0) > 0:
                optimal_first_bump = df.loc[[row.name]]  # Get a DataFrame containing only this row
                break

        # Situation 2: SHOW_NAME_1 is one more than bumps with that SHOW_NAME_3 and SHOW_NAME_3 is another bump's SHOW_NAME_1
        if optimal_first_bump is None:
            for _, row in df.iterrows():
                if pd.isna(row['SHOW_NAME_3']):  # Skip rows where SHOW_NAME_3 is None
                    continue
                if show_name_3_counts.get(row['SHOW_NAME_1'], 0) + 1 == show_name_1_counts.get(row['SHOW_NAME_1'], 0) and show_name_1_counts.get(row['SHOW_NAME_3'], 0) > 0:
                    optimal_first_bump = df.loc[[row.name]]  # Get a DataFrame containing only this row
                    break

        # Situation 3: No such bump as in situation 1 or new situation exists, but a bump where SHOW_NAME_1 is multiple other bump's SHOW_NAME_3
        if optimal_first_bump is None:
            for _, row in df.iterrows():
                if pd.isna(row['SHOW_NAME_3']):  # Skip rows where SHOW_NAME_3 is None
                    continue
                if show_name_3_counts.get(row['SHOW_NAME_1'], 0) > 1:
                    optimal_first_bump = df.loc[[row.name]]  # Get a DataFrame containing only this row
                    break

        # If neither situation 1, situation 2 nor situation 3 is met, return the first bump
        if optimal_first_bump is None:
            optimal_first_bump = df.iloc[[0]]

        return optimal_first_bump

    def reorder_table(self, table_name):
        self.used_rows = set()  # Resetting used rows for the new table
        reordered_table_name = table_name + '_reordered'
        print(f"Starting reordering for {table_name}")
        unused_df = self.unused_bumps(table_name)
        first_bump = self.find_optimal_first_bump(unused_df)
        if first_bump is not None:
            self.write_to_table(first_bump, reordered_table_name)
            self.used_rows.add(first_bump.index[0]) 
            unused_df = self.unused_bumps(table_name)  # Refresh unused rows
        while not unused_df.empty:
            next_row, index = self.get_next_row(table_name)
            self.write_to_table(next_row, reordered_table_name)
            unused_df = self.unused_bumps(table_name)  # Refresh unused rows
        print(f"Finished reordering for {table_name}")

    def reorder_all_tables(self):
        for i in range(10):
            table_name = 'multibumps_v' + str(i) + '_data'
            try:
                self.reorder_table(table_name)
                print(f"Table {table_name} is getting reordered.")
            except pd.errors.DatabaseError:
                print(f"Table {table_name} does not exist. Moving to the next table.")