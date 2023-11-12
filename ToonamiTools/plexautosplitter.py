import uuid
from plexapi.server import PlexServer


class PlexAutoSplitter:
    def __init__(self, plex_url, plex_token, library_name):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.library_name = library_name
        self.plex = PlexServer(self.plex_url, self.plex_token)

    def split_merged_item(self, rating_key):
        client_identifier = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        URL = f'/library/metadata/{rating_key}/split'
        PARAMS = {
            'X-Plex-Product': 'Plex Web',
            'X-Plex-Version': '4.108.0',
            'X-Plex-Client-Identifier': client_identifier,
            'X-Plex-Platform': 'Firefox',
            'X-Plex-Platform-Version': '116.0',
            'X-Plex-Features': 'external-media,indirect-media,hub-style-list',
            'X-Plex-Model': 'bundled',
            'X-Plex-Device': 'Windows',
            'X-Plex-Device-Name': 'Firefox',
            'X-Plex-Device-Screen-Resolution': '1718x847,3440x1440',
            'X-Plex-Token': self.plex_token,
            'X-Plex-Language': 'en',
            'X-Plex-Session-Id': session_id,
        }
        response = self.plex._session.put(self.plex_url + URL, params=PARAMS)
        if response.status_code == 200:
            print(f"Successfully split item with ratingKey: {rating_key}")
        else:
            print(f"Failed to split item with ratingKey: {rating_key}: {response.text}")

    def split_merged_items(self):
        library = self.plex.library.section(self.library_name)
        merged_items_found = True
        while merged_items_found:
            merged_items_found = False
            for item in library.all():
                if len(item.media) > 1:
                    print(f"Found merged item with ratingKey: {item.ratingKey}")
                    merged_items_found = True
                    self.split_merged_item(item.ratingKey)
        print("All merged items have been successfully split.")