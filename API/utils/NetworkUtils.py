"""
NetworkUtils - Minimal network operations using only stdlib + subprocess.

Components:
- CurlHttpClient: HTTP operations via subprocess + curl
- WikipediaTableParser: Regex-based HTML table extraction
- Helper utilities for text cleaning and processing
"""

import subprocess
import json
import re
import platform
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode


class CurlResponse:
    """
    Response object mimicking requests.Response interface.
    """

    def __init__(self, stdout: str, stderr: str, returncode: int, http_status: int = None):
        self.text = stdout
        self.stderr = stderr
        self.returncode = returncode
        # Extract HTTP status from curl output or use provided
        self.status_code = http_status or self._extract_status_code(stderr)
        self._json_cache = None

    def _extract_status_code(self, stderr: str) -> int:
        """Extract HTTP status code from curl's stderr output."""
        # This should rarely be called since we use -w flag for status extraction
        # Only fallback to stderr parsing in case the marker approach fails
        # Look for pattern like "< HTTP/1.1 200 OK" in verbose output
        match = re.search(r'HTTP/[\d.]+ (\d{3})', stderr)
        if match:
            return int(match.group(1))

        # Status not found - this indicates a problem with curl execution
        # Map curl error codes to HTTP-like status
        if self.returncode == 0:
            # Success but no status found - this shouldn't happen with -w flag
            # Likely means the request didn't complete properly
            return 500
        # Curl error codes map to 5xx
        return 500

    def json(self) -> Any:
        """Parse response body as JSON."""
        if self._json_cache is None:
            self._json_cache = json.loads(self.text)
        return self._json_cache

    def raise_for_status(self):
        """Raise exception for HTTP error status codes."""
        if self.status_code >= 400:
            raise HTTPError(f"HTTP {self.status_code}: {self.text[:200]}")


class RequestException(Exception):
    """Base exception for network request errors."""
    pass


class HTTPError(RequestException):
    """Exception raised for HTTP error status codes."""
    pass


class Timeout(RequestException):
    """Exception raised when request times out."""
    pass


class ConnectionError(RequestException):
    """Exception raised for connection errors."""
    pass


class CurlHttpClient:
    """
    HTTP client using curl via subprocess.
    Drop-in replacement for requests library with minimal interface.
    """

    @staticmethod
    def get(url: str,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, str]] = None,
            timeout: int = 30) -> CurlResponse:
        """
        Perform HTTP GET request using curl.

        Args:
            url: Target URL
            headers: Optional dict of HTTP headers
            params: Optional dict of query parameters
            timeout: Timeout in seconds (default 30)

        Returns:
            CurlResponse object

        Raises:
            Timeout: If request exceeds timeout
            ConnectionError: If connection fails
            RequestException: For other curl errors
        """
        # Build curl command (no headers in output; status appended via -w)
        cmd = ['curl', '-L', '-X', 'GET', '--max-time', str(timeout), '-s']

        # Windows-specific SSL handling: Disable certificate revocation check
        # This prevents CRYPT_E_NO_REVOCATION_CHECK errors in corporate/restricted environments
        # where CRL/OCSP endpoints may be blocked by firewalls or proxy configurations
        if platform.system() == 'Windows':
            cmd.append('--ssl-no-revoke')

        # Add headers
        if headers:
            for key, val in headers.items():
                cmd.extend(['-H', f'{key}: {val}'])

        # Add query parameters to URL
        if params:
            query_string = urlencode(params, doseq=True)
            separator = '&' if '?' in url else '?'
            url = f'{url}{separator}{query_string}'

        cmd.append(url)

        # Execute curl
        return CurlHttpClient._execute_curl(cmd, timeout)

    @staticmethod
    def post(url: str,
             json_data: Optional[Dict] = None,
             data: Optional[Union[Dict, str]] = None,
             headers: Optional[Dict[str, str]] = None,
             timeout: int = 30) -> CurlResponse:
        """
        Perform HTTP POST request using curl.

        Args:
            url: Target URL
            json_data: Optional dict to send as JSON body
            data: Optional dict or string to send as form data
            headers: Optional dict of HTTP headers
            timeout: Timeout in seconds (default 30)

        Returns:
            CurlResponse object

        Raises:
            Timeout: If request exceeds timeout
            ConnectionError: If connection fails
            RequestException: For other curl errors
        """
        # Build curl command (no headers in output; status appended via -w)
        cmd = ['curl', '-L', '-X', 'POST', '--max-time', str(timeout), '-s']

        # Windows-specific SSL handling: Disable certificate revocation check
        # This prevents CRYPT_E_NO_REVOCATION_CHECK errors in corporate/restricted environments
        # where CRL/OCSP endpoints may be blocked by firewalls or proxy configurations
        if platform.system() == 'Windows':
            cmd.append('--ssl-no-revoke')

        # Add headers (ensure we have a dict)
        headers_dict = headers.copy() if headers else {}

        # Track stdin data for large payloads
        stdin_data = None

        # Handle JSON body
        if json_data is not None:
            headers_dict['Content-Type'] = 'application/json'
            # Serialize JSON to determine size
            json_string = json.dumps(json_data) if isinstance(json_data, dict) else json_data
            json_bytes = json_string.encode('utf-8')

            # For large payloads (>100KB), use stdin to avoid ARG_MAX limit
            # ARG_MAX on most systems is 1MB-2MB, but we use conservative threshold
            if len(json_bytes) > 100000:  # 100KB threshold
                # Use stdin: curl -d @- reads from stdin
                cmd.extend(['-d', '@-'])
                stdin_data = json_bytes
            else:
                # Small payload: use command-line argument (existing behavior)
                cmd.extend(['-d', json_string])

        # Handle form data
        elif data is not None:
            if isinstance(data, dict):
                # Form-encoded data
                headers_dict.setdefault('Content-Type', 'application/x-www-form-urlencoded')
                for key, val in data.items():
                    cmd.extend(['-d', f'{key}={val}'])
            else:
                # Raw data
                cmd.extend(['-d', str(data)])

        # Add all headers
        for key, val in headers_dict.items():
            cmd.extend(['-H', f'{key}: {val}'])

        cmd.append(url)

        # Execute curl (with stdin data if needed)
        return CurlHttpClient._execute_curl(cmd, timeout, input_data=stdin_data)

    @staticmethod
    def _execute_curl(cmd: List[str], timeout: int, input_data: Optional[bytes] = None) -> CurlResponse:
        """
        Execute curl command and return response.

        Args:
            cmd: The curl command to execute
            timeout: Timeout in seconds
            input_data: Optional bytes to send to curl's stdin (for large POST bodies)

        Returns:
            CurlResponse object
        """
        status_marker = '<<<CBD_HTTP_STATUS:'

        try:
            cmd_with_status = cmd + ['-w', f'\n{status_marker}%{{http_code}}\n']
            result = subprocess.run(
                cmd_with_status,
                capture_output=True,
                text=False,
                input=input_data,  # Pass stdin data if provided
                timeout=timeout + 5,  # Subprocess timeout slightly longer than curl timeout
                check=False
            )
        except subprocess.TimeoutExpired:
            raise Timeout(f"Request timed out after {timeout} seconds")
        except FileNotFoundError:
            raise RequestException("curl command not found - ensure curl is installed")
        except Exception as e:
            raise RequestException(f"Failed to execute curl: {e}")

        def _decode_output(data: bytes) -> str:
            if not data:
                return ""
            return data.decode("utf-8", errors="replace")

        stdout = _decode_output(result.stdout)
        stderr = _decode_output(result.stderr)
        returncode = result.returncode

        status_code = None
        body = stdout

        marker_index = stdout.rfind(status_marker)
        if marker_index != -1:
            status_segment = stdout[marker_index + len(status_marker):]
            body = stdout[:marker_index]
            status_line = status_segment.strip()
            if status_line:
                try:
                    status_code = int(status_line.splitlines()[0])
                except ValueError:
                    status_code = None
            # Remove trailing newline introduced before marker
            body = body.rstrip('\n')

        response = CurlResponse(body, stderr, returncode, status_code)

        # Check for curl errors
        if returncode != 0:
            # Curl error codes
            if returncode == 28:
                raise Timeout(f"curl timeout: {stderr}")
            elif returncode in (6, 7):  # Couldn't resolve host / Failed to connect
                raise ConnectionError(f"Connection failed: {stderr}")
            else:
                raise RequestException(f"curl error (code {returncode}): {stderr}")

        return response


class WikipediaTableParser:
    """
    Minimal HTML table parser using regex.
    Designed to extract data from Wikipedia wikitable elements.
    """

    @staticmethod
    def parse_html_tables(html_content: str) -> List[Dict[str, Any]]:
        """
        Parse HTML content and extract wikitable data.

        Args:
            html_content: HTML string containing tables

        Returns:
            List of dicts, each containing:
                - 'headers': List of column headers
                - 'rows': List of lists (each inner list is a row of cell values)
        """
        tables_data = []

        # Find all tables with class 'wikitable'
        # Pattern: <table...class="wikitable"...>...</table>
        table_pattern = r'<table[^>]*class=["\']?[^"\']*wikitable[^"\']*["\']?[^>]*>(.*?)</table>'
        tables = re.findall(table_pattern, html_content, re.DOTALL | re.IGNORECASE)

        for table_html in tables:
            table_dict = WikipediaTableParser._parse_single_table(table_html)
            if table_dict:
                tables_data.append(table_dict)

        return tables_data

    @staticmethod
    def _parse_single_table(table_html: str) -> Optional[Dict[str, Any]]:
        """Parse a single table's HTML into structured data."""
        # Extract all rows
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        rows = re.findall(row_pattern, table_html, re.DOTALL | re.IGNORECASE)

        if not rows:
            return None

        headers = []
        data_rows = []

        for i, row_html in enumerate(rows):
            # Extract cells (th or td)
            cell_pattern = r'<t([hd])[^>]*>(.*?)</t\1>'
            cells = re.findall(cell_pattern, row_html, re.DOTALL | re.IGNORECASE)

            if not cells:
                continue

            # Extract text from cells
            cell_texts = []
            for tag_type, cell_content in cells:
                text = WikipediaTableParser._extract_text(cell_content)
                cell_texts.append(text)

            # First row with th tags is usually headers
            if i == 0 or (not headers and any(tag == 'h' for tag, _ in cells)):
                headers = cell_texts
            else:
                # Data row
                if cell_texts:  # Skip empty rows
                    data_rows.append(cell_texts)

        return {
            'headers': headers,
            'rows': data_rows
        }

    @staticmethod
    def _extract_text(html: str) -> str:
        """Extract plain text from HTML, removing tags and cleaning."""
        # Remove HTML tags
        text = WikipediaTableParser.strip_html_tags(html)

        # Clean up the text
        text = WikipediaTableParser.clean_table_text(text)

        return text

    @staticmethod
    def strip_html_tags(html: str) -> str:
        """Remove all HTML tags from string."""
        # Remove tags
        text = re.sub(r'<[^>]+>', '', html)

        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")

        return text

    @staticmethod
    def clean_table_text(text: str) -> str:
        """Clean extracted table text."""
        # Remove footnote references [1], [a], etc.
        text = re.sub(r'\[.*?\]', '', text)

        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text


# Convenience functions for backward compatibility
def get(url: str, **kwargs) -> CurlResponse:
    """Convenience function for HTTP GET."""
    return CurlHttpClient.get(url, **kwargs)


def post(url: str, **kwargs) -> CurlResponse:
    """Convenience function for HTTP POST."""
    return CurlHttpClient.post(url, **kwargs)
