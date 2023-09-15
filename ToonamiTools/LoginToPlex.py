import asyncio
from plexauth import PlexAuth
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import webbrowser 

class PlexServerList:
    def __init__(self):
        self.plex_servers = []
        self.plex_token = None

    def GetPlexToken(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch_token():
            PAYLOAD = {
                'X-Plex-Product': 'Commercial Breaker',
                'X-Plex-Version': '0.0.1',
                'X-Plex-Device': 'Test Device',
                'X-Plex-Platform': 'Test Platform',
                'X-Plex-Device-Name': 'Test Device Name',
                'X-Plex-Device-Vendor': 'Test Vendor',
                'X-Plex-Model': 'Test Model',
                'X-Plex-Client-Platform': 'Test Client Platform'
            }
            async with PlexAuth(PAYLOAD) as plexauth:
                await plexauth.initiate_auth()
                print("Complete auth at URL: {}".format(plexauth.auth_url()))
                webbrowser.open(plexauth.auth_url())  # Open the URL in a web browser
                return await plexauth.token()

        self.plex_token = loop.run_until_complete(fetch_token())
        loop.close()

    def GetPlexServerList(self):
        self.GetPlexToken()
        try:
            account = MyPlexAccount(token=self.plex_token)
            resources = account.resources()
            self.plex_servers = [resource.name for resource in resources]
        except Exception as e:
            print(f"An error occurred: {e}")

    def run(self):
        self.GetPlexServerList()

class PlexLibraryManager:
    def __init__(self, selected_server, plex_token):
        self.selected_server = selected_server
        self.plex_token = plex_token  # Storing the token
        self.plex_url = None

    def GetPlexDetails(self):
        account = MyPlexAccount(token=self.plex_token)
        selected_resource = next(resource for resource in account.resources() if resource.name == self.selected_server)
        plex = selected_resource.connect()
        self.plex_url = plex._baseurl  # Storing the URL

    def run(self):
        self.GetPlexDetails()

class PlexLibraryFetcher:
    def __init__(self, plex_url, plex_token):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.libraries = []

    def GetPlexLibraries(self):
        server = PlexServer(self.plex_url, self.plex_token)
        libraries = server.library.sections()
        self.libraries = [library.title for library in libraries]

    def run(self):
        self.GetPlexLibraries()