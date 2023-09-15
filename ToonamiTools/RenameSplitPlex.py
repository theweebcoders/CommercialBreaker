import re
from plexapi.server import PlexServer

class PlexLibraryUpdater:
    def __init__(self, plex_url, plex_token, library_name):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.library_name = library_name
        self.pattern = r'\/([^\/]+)\.mp4$'
        self.plex = PlexServer(self.plex_url, self.plex_token)
        self.library = self.plex.library.section(self.library_name)

    def update_titles(self):
        # Iterate through all the videos in the library
        for video in self.library.all():
            file_path = video.media[0].parts[0].file
            
            # Apply the regex pattern to extract the file name
            match = re.search(self.pattern, file_path)
            if match:
                new_title = match.group(1)
                
                # Check if the title already matches the target title
                if video.title == new_title:
                    print(f"Title already matches for file: {file_path}. Skipping.")
                    continue
                
                # Rename the video title
                video.edit(**{'title.value': new_title, 'title.locked': 1})
                print(f"Title updated to: {new_title}")
            else:
                print(f"Pattern did not match for file: {file_path}")

        print("All titles updated successfully.")