import asyncio
import webbrowser
import sys
from plexauth import PlexAuth
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer



class PlexServerList:

    def __init__(self):
        self.plex_servers = []
        self.plex_token = None
        self.auth_url_callback = None  # New callback for auth URL
        self.auth_url = None  # Store the auth URL as an instance attribute

    def set_auth_url_callback(self, callback):
        """Allow setting a callback function to handle the auth URL"""
        self.auth_url_callback = callback

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
                auth_url = plexauth.auth_url()
                self.auth_url = auth_url  # Store the auth URL in the instance
                
                # Use the callback if provided, otherwise fall back to default behavior
                if self.auth_url_callback and callable(self.auth_url_callback):
                    self.auth_url_callback(auth_url)
                else:
                    # Fallback for non-web UI
                    webbrowser.open(auth_url)
                    print("Please open the following URL in your browser to authenticate with Plex: \n" + auth_url)
                
                return await plexauth.token()

        self.plex_token = loop.run_until_complete(fetch_token())
        loop.close()

    def GetPlexServerList(self):
        """
        Fetches and stores the list of Plex servers associated with the user's Plex account. It obtains the Plex token and uses it to authenticate with the Plex account.
        Allowing the program to interact with the user's Plex servers and provide the user with a list of their Plex servers.
        """
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
    """
    This class is responsible for managing the Plex library. It fetches and stores the details of a selected Plex server.
    This is important to the program as it allows the user to select a Plex server and use the libraries on that server in the program.
    """
    def __init__(self, selected_server, plex_token):
        self.selected_server = selected_server
        self.plex_token = plex_token  # Storing the token
        self.plex_url = None
        """
        Takes the selected Plex server and the Plex token as arguements.
        """

    def GetPlexDetails(self):
        """
        Fetches and stores the details of the selected Plex server. It uses the Plex token to authenticate with the Plex account and connect to the selected server. The base URL of the server is then stored for future use. 
        This is important to retain user's selection so it can be stored for future use.
        """
        account = MyPlexAccount(token=self.plex_token)
        selected_resource = next(resource for resource in account.resources() if resource.name == self.selected_server)
        plex = selected_resource.connect()
        self.plex_url = plex._baseurl  # Storing the URL

    def run(self):
        self.GetPlexDetails()
        return self.plex_url


class PlexLibraryFetcher:
    """
    This class is responsible for fetching and storing the libraries from a selected Plex server.
    It uses the Plex token to authenticate with the Plex account and connect to the server using its base URL.
    The libraries are then fetched and stored for future use.
    """
    def __init__(self, plex_url, plex_token):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.libraries = []

    """
    Takes the base URL of the selected Plex server and the Plex token as arguements.
    """

    def GetPlexLibraries(self):
        server = PlexServer(self.plex_url, self.plex_token)
        libraries = server.library.sections()
        self.libraries = [library.title for library in libraries]

    def run(self):
        self.GetPlexLibraries()
