import pandas as pd
import sqlite3
import re
from plexapi.server import PlexServer
from dizqueTV import API



class PlexToDizqueTVSimplified:
    def __init__(self, plex_url, plex_token, library_name, table, dizquetv_url, channel_number):
        print("Initializing the connection to Plex and dizqueTV...")
        self.plex = PlexServer(plex_url, plex_token)
        self.library_name = library_name
        self.dtv = API(url=dizquetv_url)
        self.channel_number = channel_number
        toonami_db = sqlite3.connect('toonami.db')
        print(f"Connected to SQLite database 'toonami.db', focusing on the table '{table}'.")
        self.table = table
        self.df = pd.read_sql_query(f"SELECT * FROM {self.table}", toonami_db)

    def get_filename_from_path(self, path):
        return re.split(r'[\\/]', path)[-1]

    def run(self):
        print("Fetching media items from Plex and SQLite DB...")

        # Step 1: Fetch media items from Plex and SQLite DB
        df = self.df
        all_media = self.plex.library.section(self.library_name).all()

        media_dict = {self.get_filename_from_path(media.media[0].parts[0].file): media for media in all_media}
        file_paths = df['FULL_FILE_PATH'].tolist()
        file_names = [self.get_filename_from_path(path) for path in file_paths]

        playlist_media = [media_dict[file_name] for file_name in file_names if file_name in media_dict]

        print(f"Identified {len(playlist_media)} media items to add to the dizqueTV channel.")

        print("Checking and updating the dizqueTV channel...")
        # Step 2: Add those media items to dizqueTV channel
        channel = self.dtv.get_channel(self.channel_number)
        if not channel:
            print("Channel not found. Creating a new one...")
            channel = self.dtv.add_channel(programs=[], name=self.library_name, number=self.channel_number)

        to_add = []
        for item in playlist_media:
            print(f"Converting Plex item: {item.title}")
            program = self.dtv.convert_plex_item_to_program(plex_item=item, plex_server=self.plex)
            if program:
                to_add.append(program)

        print("Deleting old programs from the channel...")
        if channel.delete_all_programs():
            print("Adding new programs to the channel...")
            self.dtv.add_programs_to_channels(programs=to_add, channels=[channel])
        print("Operation complete.")
