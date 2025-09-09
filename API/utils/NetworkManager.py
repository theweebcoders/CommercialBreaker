import re
import os
from typing import Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


WIKIPEDIA_BASE = "https://en.wikipedia.org/wiki/"


def _slugify_for_wiki(network_name: str) -> str:
    """Return a Wikipedia-friendly slug replacing spaces with underscores.

    Does not change the original capitalization to allow normal wiki behavior.
    """
    # Trim and collapse whitespace
    cleaned = re.sub(r"\s+", " ", network_name.strip())
    return cleaned.replace(" ", "_")


def _candidate_pages(network_name: str) -> list[str]:
    """Generate likely Wikipedia page titles for broadcast lists."""
    slug = _slugify_for_wiki(network_name)
    return [
        f"List_of_programs_broadcast_by_{slug}",
        f"List_of_programs_broadcast_on_{slug}",
        # Some networks have region qualifiers (rare); callers can extend if needed
    ]


def _url_exists(url: str, timeout: float = 5.0) -> bool:
    # Try HEAD first (lighter). Some sites reject HEAD; on 405, try GET
    try:
        req = Request(url, method='HEAD', headers={'User-Agent': 'CommercialBreaker/1.0'})
        with urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, 'status', resp.getcode())
            return 200 <= code < 400
    except HTTPError as e:
        if e.code == 405:
            try:
                req = Request(url, method='GET', headers={'User-Agent': 'CommercialBreaker/1.0'})
                with urlopen(req, timeout=timeout) as resp:
                    code = getattr(resp, 'status', resp.getcode())
                    return 200 <= code < 400
            except Exception:
                return False
        # Follow redirects are automatic; treat 200-399 as success
        return 200 <= e.code < 400
    except URLError:
        return False
    except Exception:
        return False


def validate_network_name(network_name: str) -> Tuple[bool, str]:
    """Validate the network by checking for an existing Wikipedia list page.

    Returns (is_valid, message).
    """
    if not network_name or not network_name.strip():
        return False, "Network name cannot be empty"

    # Basic sanity check to avoid obviously invalid values
    if len(network_name.strip()) > 80:
        return False, "Network name is too long"

    candidates = _candidate_pages(network_name)
    for page in candidates:
        url = WIKIPEDIA_BASE + page
        if _url_exists(url):
            return True, f"Validated via Wikipedia: {page}"

    return False, (
        "Could not find a Wikipedia page like 'List of programs broadcast by/on <Network>'. "
        "Please check the exact network name (e.g., 'Cartoon Network', 'Disney Channel')."
    )


def update_config_network(config_path: str, new_network: str) -> None:
    """Rewrite the `network = "..."` line in config.py to persist the change."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("network = "):
            # Preserve quoting style
            quote = '"' if '"' in line else "'"
            lines[i] = f"network = {quote}{new_network}{quote}\n"
            updated = True
            break

    if not updated:
        # Insert near top if not present
        insert_line = f"network = \"{new_network}\"\n"
        lines.insert(0, insert_line)

    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
