"""
PlexClient - Custom Plex authentication and account management.

Components:
- PlexAuthClient: OAuth PIN-based authentication flow
- PlexAccountClient: Server discovery and account operations
- PlexResource: Represents a Plex server resource
"""

import time
import uuid
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode

from API.utils.NetworkUtils import CurlHttpClient, RequestException, Timeout, ConnectionError as NetConnectionError


class PlexAuthError(Exception):
    """Exception raised for Plex authentication errors."""
    pass


class PlexResource:
    """Represents a Plex server resource."""

    def __init__(self, xml_element: ET.Element):
        """
        Initialize from XML element.

        Args:
            xml_element: XML element from Plex resources response
        """
        self._element = xml_element
        self.name = xml_element.get('name', '')
        self.clientIdentifier = xml_element.get('clientIdentifier', '')
        self.provides = xml_element.get('provides', '')
        self.owned = xml_element.get('owned', '1') == '1'
        self.accessToken = xml_element.get('accessToken', '')
        self.publicAddressMatches = xml_element.get('publicAddressMatches', '1') == '1'
        self.presence = xml_element.get('presence', '1') == '1'

        # Parse connections
        # The Plex API v2 structure is: <resource><connections><connection /></connections></resource>
        self._connections = []

        # Look for connections under the 'connections' parent element
        connections_elem = xml_element.find('connections')
        if connections_elem is not None:
            for conn in connections_elem.findall('connection'):
                self._connections.append({
                    'protocol': conn.get('protocol', 'http'),
                    'address': conn.get('address', ''),
                    'port': conn.get('port', '32400'),
                    'uri': conn.get('uri', ''),
                    'local': conn.get('local', '0') == '1',
                })

        # Fallback: Also try direct children (in case structure varies)
        if not self._connections:
            for conn in xml_element.findall('connection'):
                self._connections.append({
                    'protocol': conn.get('protocol', 'http'),
                    'address': conn.get('address', ''),
                    'port': conn.get('port', '32400'),
                    'uri': conn.get('uri', ''),
                    'local': conn.get('local', '0') == '1',
                })

    def connect(self, timeout: int = 15) -> 'PlexServerConnection':
        """
        Connect to this Plex server resource.

        Tries all available connections, preferring local connections first.

        Args:
            timeout: Maximum total timeout in seconds (divided among all connection attempts)

        Returns:
            PlexServerConnection object

        Raises:
            PlexAuthError: If connection to all endpoints fails
        """
        # Check if we have any connections
        if not self._connections:
            raise PlexAuthError(f"No connection information available for server '{self.name}'")

        # Sort connections: local first, then https, then http
        sorted_connections = sorted(
            self._connections,
            key=lambda c: (not c['local'], c['protocol'] != 'https', c['protocol'] != 'http')
        )

        # Calculate timeout per connection (minimum 3 seconds, maximum 8 seconds)
        timeout_per_connection = max(3, min(8, timeout // len(sorted_connections)))

        last_error = None
        for conn in sorted_connections:
            try:
                base_url = conn['uri'] if conn['uri'] else f"{conn['protocol']}://{conn['address']}:{conn['port']}"

                # Test connection with identity endpoint
                headers = {
                    'X-Plex-Token': self.accessToken,
                    'Accept': 'application/json'
                }

                response = CurlHttpClient.get(
                    f"{base_url}/identity",
                    headers=headers,
                    timeout=timeout_per_connection
                )

                if response.status_code == 200:
                    # Successful connection
                    return PlexServerConnection(base_url, self.accessToken)
                else:
                    last_error = f"HTTP {response.status_code}"

            except Timeout as e:
                last_error = e
                continue
            except (RequestException, NetConnectionError) as e:
                last_error = e
                continue

        # All connections failed
        raise PlexAuthError(f"Failed to connect to server '{self.name}': {last_error}")


class PlexServerConnection:
    """Represents an active connection to a Plex server."""

    def __init__(self, base_url: str, token: str):
        """
        Initialize server connection.

        Args:
            base_url: Base URL of the Plex server (e.g., http://192.168.1.100:32400)
            token: Authentication token
        """
        self._baseurl = base_url.rstrip('/')
        self._token = token

    @property
    def baseurl(self) -> str:
        """Get the base URL of the server."""
        return self._baseurl


class PlexAuthClient:
    """
    Handles Plex OAuth authentication using PIN-based flow.

    Replaces the plexauth library with a simpler implementation.
    """

    PLEX_API_BASE = "https://plex.tv/api/v2"

    def __init__(self, headers: Dict[str, str], poll_interval: int = 3, poll_timeout: int = 300):
        """
        Initialize Plex authentication client.

        Args:
            headers: Client identification headers (X-Plex-Product, X-Plex-Version, etc.)
            poll_interval: Seconds between token polling attempts (default: 3)
            poll_timeout: Maximum seconds to wait for user authentication (default: 300)
        """
        self.headers = headers.copy()

        # Ensure X-Plex-Client-Identifier exists (required by Plex API)
        if 'X-Plex-Client-Identifier' not in self.headers:
            self.headers['X-Plex-Client-Identifier'] = str(uuid.uuid4())

        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

        self._pin_id = None
        self._pin_code = None
        self._auth_token = None

    def initiate_auth(self) -> Dict[str, str]:
        """
        Initiate authentication by requesting a PIN from Plex.

        Returns:
            Dict containing 'id' and 'code' for the authentication PIN

        Raises:
            PlexAuthError: If PIN request fails
        """
        try:
            # Prepare headers with Accept header for JSON response
            request_headers = self.headers.copy()
            request_headers['Accept'] = 'application/json'

            # Request a PIN (params must be in URL for POST, empty body needed)
            response = CurlHttpClient.post(
                f"{self.PLEX_API_BASE}/pins.json?strong=true",
                json_data={},
                headers=request_headers,
                timeout=30
            )

            if response.status_code != 201:
                raise PlexAuthError(f"Failed to request PIN: HTTP {response.status_code}")

            data = response.json()
            self._pin_id = data.get('id')
            self._pin_code = data.get('code')

            if not self._pin_id or not self._pin_code:
                raise PlexAuthError("Invalid PIN response from Plex")

            return {
                'id': str(self._pin_id),
                'code': self._pin_code
            }

        except (RequestException, NetConnectionError, Timeout) as e:
            raise PlexAuthError(f"Network error during PIN request: {e}")
        except (ValueError, KeyError) as e:
            raise PlexAuthError(f"Failed to parse PIN response: {e}")

    def auth_url(self) -> str:
        """
        Get the authentication URL for the user to visit.

        Returns:
            URL string for user authentication

        Raises:
            PlexAuthError: If initiate_auth() hasn't been called
        """
        if not self._pin_id or not self._pin_code:
            raise PlexAuthError("Must call initiate_auth() before getting auth URL")

        client_id = self.headers.get('X-Plex-Client-Identifier', '')
        params = {
            'clientID': client_id,
            'code': self._pin_code,
            'context[device][product]': self.headers.get('X-Plex-Product', ''),
        }

        query_string = urlencode(params)
        return f"https://app.plex.tv/auth#!?{query_string}"

    def get_token(self) -> str:
        """
        Poll for authentication token until user authorizes or timeout.

        Returns:
            Authentication token string

        Raises:
            PlexAuthError: If polling fails or times out
        """
        if not self._pin_id:
            raise PlexAuthError("Must call initiate_auth() before polling for token")

        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.poll_timeout:
                raise PlexAuthError(f"Authentication timed out after {self.poll_timeout} seconds")

            try:
                # Prepare headers with Accept header for JSON response
                request_headers = self.headers.copy()
                request_headers['Accept'] = 'application/json'

                # Poll the PIN status
                response = CurlHttpClient.get(
                    f"{self.PLEX_API_BASE}/pins/{self._pin_id}",
                    headers=request_headers,
                    timeout=30
                )

                if response.status_code != 200:
                    raise PlexAuthError(f"Failed to check PIN status: HTTP {response.status_code}")

                data = response.json()
                auth_token = data.get('authToken')

                if auth_token:
                    self._auth_token = auth_token
                    return auth_token

                # Token not yet available, wait and retry
                time.sleep(self.poll_interval)

            except (RequestException, NetConnectionError, Timeout) as e:
                # Network errors during polling - wait and retry
                time.sleep(self.poll_interval)
                continue
            except (ValueError, KeyError) as e:
                raise PlexAuthError(f"Failed to parse PIN status response: {e}")


class PlexAccountClient:
    """
    Handles Plex account operations and server discovery.

    Replaces MyPlexAccount from plexapi.
    """

    PLEX_API_BASE = "https://plex.tv"

    def __init__(self, token: str, client_identifier: Optional[str] = None):
        """
        Initialize Plex account client.

        Args:
            token: Plex authentication token
            client_identifier: Optional client UUID (generated if not provided)
        """
        self.token = token

        # Generate or use provided client identifier
        if client_identifier is None:
            client_identifier = str(uuid.uuid4())

        # Build headers with client identification (required by Plex API)
        self._headers = {
            'X-Plex-Token': token,
            'X-Plex-Client-Identifier': client_identifier,
            'X-Plex-Product': 'Commercial Breaker',
            'X-Plex-Version': '0.0.1',
            'Accept': 'application/xml'
        }

    def validate_token(self) -> Dict[str, Any]:
        """
        Validate the authentication token and get account info.

        Returns:
            Dict containing account information

        Raises:
            PlexAuthError: If token is invalid or request fails
        """
        try:
            response = CurlHttpClient.get(
                f"{self.PLEX_API_BASE}/api/v2/user",
                headers={'X-Plex-Token': self.token, 'Accept': 'application/json'},
                timeout=30
            )

            if response.status_code == 401:
                raise PlexAuthError("Invalid or expired Plex token")

            if response.status_code != 200:
                raise PlexAuthError(f"Failed to validate token: HTTP {response.status_code}")

            return response.json()

        except (RequestException, NetConnectionError, Timeout) as e:
            raise PlexAuthError(f"Network error during token validation: {e}")
        except (ValueError, KeyError) as e:
            raise PlexAuthError(f"Failed to parse account response: {e}")

    def resources(self) -> List[PlexResource]:
        """
        Get list of Plex server resources accessible with this account.

        Returns:
            List of PlexResource objects

        Raises:
            PlexAuthError: If resource listing fails
        """
        try:
            # Request server resources
            response = CurlHttpClient.get(
                f"{self.PLEX_API_BASE}/api/v2/resources",
                params={'includeHttps': '1', 'includeRelay': '1'},
                headers=self._headers,
                timeout=30
            )

            if response.status_code == 401:
                raise PlexAuthError("Invalid or expired Plex token")

            if response.status_code != 200:
                raise PlexAuthError(f"Failed to get resources: HTTP {response.status_code}")

            # Parse XML response
            root = ET.fromstring(response.text)

            # Filter for server resources only (not players, etc.)
            # The API v2 uses <resource> tags, not <Device>
            resources = []
            for resource_elem in root.findall('resource'):
                provides = resource_elem.get('provides', '')
                if 'server' in provides:
                    resources.append(PlexResource(resource_elem))

            return resources

        except (RequestException, NetConnectionError, Timeout) as e:
            raise PlexAuthError(f"Network error during resource listing: {e}")
        except ET.ParseError as e:
            raise PlexAuthError(f"Failed to parse resources XML: {e}")


# Convenience functions for backwards compatibility

def authenticate_with_pin(
    client_headers: Dict[str, str],
    poll_interval: int = 3,
    poll_timeout: int = 300
) -> tuple[str, str]:
    """
    Perform complete PIN-based authentication flow.

    Args:
        client_headers: Client identification headers
        poll_interval: Seconds between polling attempts
        poll_timeout: Maximum seconds to wait for authentication

    Returns:
        Tuple of (auth_url, token)

    Raises:
        PlexAuthError: If authentication fails
    """
    client = PlexAuthClient(client_headers, poll_interval, poll_timeout)
    client.initiate_auth()
    auth_url = client.auth_url()
    token = client.get_token()
    return (auth_url, token)


def get_server_list(token: str) -> List[str]:
    """
    Get list of server names for a Plex account.

    Args:
        token: Plex authentication token

    Returns:
        List of server name strings

    Raises:
        PlexAuthError: If request fails
    """
    client = PlexAccountClient(token)
    resources = client.resources()
    return [resource.name for resource in resources]
