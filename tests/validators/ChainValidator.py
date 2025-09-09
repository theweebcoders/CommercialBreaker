import re
import pandas as pd
from API.utils.DatabaseManager import get_db_manager
from ToonamiTools.utils import show_name_mapper


class ChainValidator:
    """
    Validates lineup chain continuity using the Code column (bump-to-bump)
    and episodes (BLOCK_ID) to ensure the channel flow is dictated by bumps.

    Bump-to-bump:
    - NS3 (Now S1, Next S2, Later S3) -> next Code must anchor on S3
      (either Now S3 for NS3 or From S3 for NS2).
    - NS2 (S1 Next From S2) -> next Code must anchor on S1
      (Now S1 for NS3 or From S1 for NS2).

    Episode-aware:
    - After NS3, the next episode must be S1 (Now S1), allowing a triple bump
      to appear before S1’s final part.
    - At show-change boundaries, the new show must match the latest NS3’s Next
      mapping (S1->S2 and S2->S3 sequences).
    - After NS2 (S1 Next From S2), the next episode must be S1, and the
      previous active show should be S2.
    """

    def __init__(self):
        self.db = get_db_manager()
        self.decoder = None  # map abbr -> full name (lower)

    def _load_decoder(self):
        with self.db.transaction() as conn:
            df_codes = pd.read_sql("SELECT * FROM codes", conn)
        # codes table has columns: Name, Code (from BumpEncoder)
        # Build decoder: abbr -> name (lower)
        self.decoder = {row["Code"]: row["Name"].lower() for _, row in df_codes.iterrows()}

    def _decode_shows_from_code(self, code_str: str):
        parts = code_str.split("-")
        show_codes = [part.split(":")[1] for part in parts if part.startswith("S")]
        return [self.decoder.get(sc, sc).lower() for sc in show_codes]

    def _show_from_block_id(self, block_id: str | None):
        if not block_id or not isinstance(block_id, str):
            return None
        base = block_id.rsplit("_S", 1)[0]
        base = base.replace("_", " ").lower()
        mapped = show_name_mapper.map(base, strategy='all')
        return show_name_mapper.clean(mapped, mode='matching')

    def validate_table(self, table_name: str):
        if self.decoder is None:
            self._load_decoder()

        with self.db.transaction() as conn:
            df = pd.read_sql(f"SELECT FULL_FILE_PATH, Code, BLOCK_ID FROM {table_name} ORDER BY ROWID", conn)

        code_rows = df[df["Code"].notna() & (df["Code"].str.strip() != "")]
        violations = []

        # -----------------
        # Bump-to-bump chain
        # -----------------
        expected_next_anchor = None  # lowercased show name expected by the next code row

        for idx, row in code_rows.iterrows():
            code_str = row["Code"]
            shows = self._decode_shows_from_code(code_str)
            is_ns3 = bool(re.search(r"-NS3\b", code_str))
            is_ns2 = bool(re.search(r"-NS2\b", code_str))

            # Validate against expected anchor
            if expected_next_anchor is not None:
                ok = False
                if is_ns3 and len(shows) >= 1:
                    ok = (shows[0] == expected_next_anchor)
                elif is_ns2 and len(shows) >= 2:
                    # NS2 must reference the expected anchor as the 'from' (S2)
                    ok = (shows[1] == expected_next_anchor)
                else:
                    # NS1 or malformed; ignore continuity for this row
                    ok = True

                if not ok:
                    violations.append({
                        "row_index": int(idx),
                        "full_file_path": row["FULL_FILE_PATH"],
                        "code": code_str,
                        "expected_anchor": expected_next_anchor,
                        "decoded_shows": shows,
                    })

            # Update expected anchor for the subsequent code row
            if is_ns3 and len(shows) >= 3:
                expected_next_anchor = shows[2]  # Later -> next Now
            elif is_ns2 and len(shows) >= 1:
                expected_next_anchor = shows[0]  # S1 becomes the next Now anchor
            else:
                # NS1 or malformed; do not alter anchor
                pass

        return violations

    def validate_table_with_episodes(self, table_name: str):
        """
        Extended validation: ensures bump-to-bump anchors AND that episodes
        around bumps match what the bumps announce.
        """
        if self.decoder is None:
            self._load_decoder()

        with self.db.transaction() as conn:
            df = pd.read_sql(f"SELECT FULL_FILE_PATH, Code, BLOCK_ID FROM {table_name} ORDER BY ROWID", conn)

        violations = []

        expected_next_anchor = None  # for next code row (bump-to-bump)
        pending_now_expected = None  # next episode after a bump should be this show
        expected_previous_show_for_ns2 = None  # the show we should be coming from when NS2 appears
        expected_after_current_show = {}  # mapping current_show -> next expected show (from NS3)

        last_episode_show = None

        for idx, row in df.iterrows():
            code_str = (row["Code"] or "").strip()
            block_id = row.get("BLOCK_ID")

            if code_str:
                shows = self._decode_shows_from_code(code_str)
                is_ns3 = bool(re.search(r"-NS3\b", code_str))
                is_ns2 = bool(re.search(r"-NS2\b", code_str))

                # Bump-to-bump continuity
                if expected_next_anchor is not None:
                    ok = True
                    if is_ns3 and len(shows) >= 1:
                        ok = (shows[0] == expected_next_anchor)
                    elif is_ns2 and len(shows) >= 2:
                        ok = (shows[1] == expected_next_anchor)
                    if not ok:
                        violations.append({
                            "type": "bump_chain",
                            "row_index": int(idx),
                            "full_file_path": row["FULL_FILE_PATH"],
                            "code": code_str,
                            "expected_anchor": expected_next_anchor,
                            "decoded_shows": shows,
                        })

                # Episode expectations
                if is_ns3 and len(shows) >= 3:
                    s1, s2, s3 = shows[0], shows[1], shows[2]
                    pending_now_expected = s1
                    expected_after_current_show = {s1: s2, s2: s3}
                    expected_next_anchor = s3
                elif is_ns2 and len(shows) >= 2:
                    s1, s2 = shows[0], shows[1]
                    pending_now_expected = s1
                    expected_previous_show_for_ns2 = s2
                    expected_next_anchor = s1
                continue

            # Episode row
            episode_show = self._show_from_block_id(block_id)
            if not episode_show:
                continue

            # Validate immediate NOW after a bump
            if pending_now_expected is not None:
                if episode_show != pending_now_expected:
                    violations.append({
                        "type": "now_mismatch",
                        "row_index": int(idx),
                        "full_file_path": row["FULL_FILE_PATH"],
                        "expected_now": pending_now_expected,
                        "actual_show": episode_show,
                    })
                pending_now_expected = None

            # Validate NS2 "from" show context
            if expected_previous_show_for_ns2 is not None and last_episode_show is not None:
                if last_episode_show != expected_previous_show_for_ns2:
                    violations.append({
                        "type": "ns2_from_context",
                        "row_index": int(idx),
                        "full_file_path": row["FULL_FILE_PATH"],
                        "expected_previous_show": expected_previous_show_for_ns2,
                        "actual_previous_show": last_episode_show,
                    })
                # Once we see the first S1 episode after NS2, clear the expectation
                expected_previous_show_for_ns2 = None

            # Detect show change and validate against NS3 expectations
            if last_episode_show is not None and episode_show != last_episode_show:
                expected_next = expected_after_current_show.get(last_episode_show)
                if expected_next and episode_show != expected_next:
                    violations.append({
                        "type": "next_mismatch",
                        "row_index": int(idx),
                        "full_file_path": row["FULL_FILE_PATH"],
                        "from_show": last_episode_show,
                        "expected_next": expected_next,
                        "actual_next": episode_show,
                    })

            last_episode_show = episode_show

        return violations

