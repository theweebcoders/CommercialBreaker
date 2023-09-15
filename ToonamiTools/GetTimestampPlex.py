from plexapi.server import PlexServer
import os

class GetPlexTimestamps:
    def __init__(self, plex_url, plex_token, library_name, save_dir):
        self.plex = PlexServer(plex_url, plex_token)
        self.library_name = library_name
        self.save_dir = save_dir

    def run(self):
        # Get all the media in the library
        section = self.plex.library.section(self.library_name)
        all_media = section.all()
        print(f'Loaded {len(all_media)} media items from the Plex library.')

        # Create the save directory if it doesn't exist
        os.makedirs(self.save_dir, exist_ok=True)

        # Open a text file in the specified directory to write the output
        with open(os.path.join(self.save_dir, 'intros.txt'), 'w', encoding='utf-8') as file:
            for media_item in all_media:
                print(f'Processing: {media_item.title}')
                episodes = media_item.episodes()
                for episode in episodes:
                    item = self.plex.fetchItem(f'/library/metadata/{episode.ratingKey}')
                    if hasattr(item, 'markers'):
                        for marker in item.markers:
                            if marker.type == 'intro':
                                start_time_offset = marker.start
                                end_time_offset = marker.end
                                start_time_converted = start_time_offset/1000
                                end_time_converted = end_time_offset/1000
                                file_path = item.media[0].parts[0].file
                                # Get the file name from the file path by splitting on the last slash
                                file_name = file_path.split('/')[-1]
                                print(f'Found intro for {file_name} at {start_time_converted} to {end_time_converted}.')
                                #intro_line = f'{file_name} = "intro" Start of intro is "{start_time_converted}" End of intro is "{end_time_converted}"\n'
                                cut_line = f'{file_name} = {end_time_converted}\n'
                                #file.write(intro_line)
                                file.write(cut_line)

        print(f'Intros written to {os.path.join(self.save_dir, "plex_timestamps.txt")}.')