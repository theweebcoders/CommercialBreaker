"""Integration tool for pushing lineups into ComBreakDirect."""

from __future__ import annotations

import time
from urllib.parse import urlparse

import config
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
from API.utils.NetworkUtils import CurlHttpClient, RequestException
from .utils import show_name_mapper


def load_lineup_rows(table: str, db_manager=None) -> list[dict]:
    """Load and normalize lineup rows from a SQLite lineup table.

    Shared by ComBreakToComBreakDirect (initial channel creation) and the
    infinite-channel extender (each extension chunk lives in its own table).
    """
    if not table:
        raise RuntimeError("No table specified for lineup loading")

    if db_manager is None:
        db_manager = get_db_manager()

    if not db_manager.table_exists(table):
        raise RuntimeError(f"Lineup table '{table}' not found")

    query = f"SELECT * FROM {table} ORDER BY rowid"
    rows = db_manager.fetchall(query)

    lineup: list[dict] = []
    for index, row in enumerate(rows):
        if index and index % 500 == 0:
            print(f"[ComBreakDirect] Processed {index}/{len(rows)} lineup items")

        # Provide safe access to potential column name variants
        row_dict = {key.lower(): row[key] for key in row.keys()}

        lineup.append(
            {
                "block_id": row_dict.get("block_id"),
                "file_path": row_dict.get("full_file_path") or row_dict.get("file_path"),
                "code": row_dict.get("code"),
                "start_time": row_dict.get("starttime"),
                "end_time": row_dict.get("endtime"),
                "duration": row_dict.get("duration"),
            }
        )

    print(f"[ComBreakDirect] Loaded {len(lineup)} lineup items from {table}")
    return lineup


class ComBreakToComBreakDirect:
    """Create or update a ComBreakDirect channel using lineup data."""

    def __init__(
        self,
        table: str | None,
        channel_number: int | None,
        flex_duration: str | int | None,
        *,
        network: str | None = None,
        base_url: str | None = None,
        create_channel: bool = True,
        commercial_folder: str | None = None,
        infinite: bool = False,
        infinite_meta: dict | None = None,
    ) -> None:
        self.error_manager = get_error_manager()
        self.db_manager = get_db_manager()
        self.table = table
        self.channel_number = channel_number
        self.flex_duration = flex_duration
        self.network = network or config.network
        self.create_channel = create_channel
        self.commercial_folder = commercial_folder
        self.infinite = infinite
        self.infinite_meta = infinite_meta or {}

        if self.create_channel:
            if not self.table:
                raise ValueError("table is required when create_channel is True")
            if self.channel_number is None:
                raise ValueError("channel_number is required when create_channel is True")
            if self.flex_duration in (None, ""):
                raise ValueError("flex_duration is required when create_channel is True")
            if not self.network:
                raise ValueError("network name is required when create_channel is True")

        default_port = getattr(config, "CBDIRECT_PORT", 8083)

        resolved_base = base_url or getattr(config, "CBDIRECT_BASE_URL", f"http://127.0.0.1:{default_port}")
        parsed = urlparse(resolved_base.strip())
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("base_url must include scheme and host (e.g., http://127.0.0.1:8083)")

        self.base_url = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')

    def run(self) -> bool:
        try:
            if not self._wait_for_server():
                raise RuntimeError("ComBreakDirect server not reachable")

            if self.create_channel:
                lineup = self._load_lineup()
                if not lineup:
                    raise RuntimeError("No lineup data available")

                if self.infinite:
                    self._seed_episode_cursor(lineup)

                self._push_lineup(lineup)
            else:
                print("[ComBreakDirect] create_channel disabled; server is running awaiting manual trigger")

            return True
        except Exception as exc:
            self.error_manager.send_error_level(
                source="ComBreakToComBreakDirect",
                operation="run",
                message=str(exc),
                details=str(exc),
                suggestion="Review ComBreakDirect configuration and ensure lineup data exists",
            )
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait_for_server(self, retries: int = 30, delay: float = 1.0) -> bool:
        status_url = f"{self.base_url}/status"
        for _ in range(retries):
            try:
                response = CurlHttpClient.get(status_url, timeout=2)
                if response.status_code == 200:
                    return True
            except RequestException:
                pass
            time.sleep(delay)
        return False

    def _load_lineup(self) -> list[dict]:
        return load_lineup_rows(self.table, self.db_manager)

    def _seed_episode_cursor(self, lineup: list[dict]) -> None:
        """Pre-populate ``last_used_episode_block`` from the initial channel's
        BLOCK_IDs so the very first infinite extension picks up where the
        channel's existing content left off, instead of starting each show
        from scratch.

        Without this, the first extension's ShowScheduler call sees an empty
        cursor and selects the first available block per show — which can
        replay episodes the user already watched in the original chunk, or
        jump to an arbitrary unrelated episode (whichever happens to be
        index 0 in the show pool).

        Show keys must match ShowScheduler's internal format
        (``show_name_mapper.clean(show_name_mapper.map(name), mode='matching')``)
        or the cursor lookup will silently miss and fall through to the
        "fresh start" path again.
        """
        cursor_from_lineup: dict[str, str] = {}
        for row in lineup:
            block_id = row.get("block_id")
            if not block_id or "_S" not in block_id:
                continue
            # BLOCK_ID format is SHOW_NAME_PARTS_S##E## — strip the trailing
            # _S##E## and turn the underscored show prefix into the spaced
            # form that the show_name_mapper expects.
            prefix = block_id.rsplit("_S", 1)[0]
            raw_name = prefix.replace("_", " ")
            show_key = show_name_mapper.clean(
                show_name_mapper.map(raw_name, strategy="all"),
                mode="matching",
            )
            if not show_key:
                continue
            prior = cursor_from_lineup.get(show_key)
            if prior is None or block_id > prior:
                cursor_from_lineup[show_key] = block_id

        if not cursor_from_lineup:
            print(
                "[ComBreakDirect] No BLOCK_IDs in lineup; episode cursor not seeded"
            )
            return

        # Merge with any pre-existing cursor data, always taking the larger
        # BLOCK_ID per show. The cursor table is shared across every channel
        # the user has ever created — never roll it backwards just because
        # this channel happened to be built from an earlier slice of content.
        merged: dict[str, str] = {}
        if self.db_manager.table_exists("last_used_episode_block"):
            for existing in self.db_manager.fetchall_as_dicts(
                "SELECT * FROM last_used_episode_block"
            ):
                show = existing.get("show")
                block = existing.get("last_used_block")
                if show and block:
                    merged[show] = block

        for show_key, block_id in cursor_from_lineup.items():
            prev = merged.get(show_key)
            if prev is None or block_id > prev:
                merged[show_key] = block_id

        data = [
            {"show": show, "last_used_block": block_id}
            for show, block_id in merged.items()
        ]
        self.db_manager.replace_table_data("last_used_episode_block", data)
        print(
            f"[ComBreakDirect] Seeded last_used_episode_block from initial "
            f"lineup: {len(cursor_from_lineup)} shows derived "
            f"({len(merged)} total now in cursor table)"
        )

    def _push_lineup(self, lineup: list[dict]) -> None:
        payload = {
            "channel_number": self.channel_number,
            "network": self.network,
            "lineup": lineup,
            "flex_duration": self._flex_duration_ms(),
        }

        if self.commercial_folder:
            payload["commercial_folder"] = self.commercial_folder

        if self.infinite:
            payload["infinite"] = True
            payload["infinite_meta"] = self.infinite_meta

        try:
            response = CurlHttpClient.post(
                f"{self.base_url}/channels",
                json_data=payload,
                headers={"Content-Type": "application/json"},
                timeout=300,
            )
        except RequestException as exc:
            raise RuntimeError(f"Failed to reach ComBreakDirect: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(
                f"ComBreakDirect returned {response.status_code}: {response.text}"
            )

        print("[ComBreakDirect] Channel created successfully")
        try:
            data = response.json()
            print(
                f"[ComBreakDirect] Channel {data.get('channel_number')} ready at "
                f"{data.get('playlist_url')}"
            )
        except ValueError:
            pass

    def _flex_duration_ms(self) -> int:
        duration = self.flex_duration
        if duration in (None, ""):
            raise ValueError("flex_duration is required")

        if isinstance(duration, (int, float)):
            return int(duration)

        if isinstance(duration, str):
            duration = duration.strip()
            parts = duration.split(":")
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                minutes, seconds = (int(parts[0]), int(parts[1]))
                return (minutes * 60 + seconds) * 1000
            if duration.isdigit():
                return int(duration)

        return 0
