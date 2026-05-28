"""Generate one extension chunk of channel lineup for the infinite-channel feature.

Each invocation:
  1. Reads the per-version configuration from ``config.TOONAMI_CONFIG_CONT``.
  2. Runs ``ShowScheduler`` with ``continue_from_last_used_episode_block=True``
     so the per-show cursor in ``last_used_episode_block`` advances.
  3. Writes to a chunk-specific table named
     ``{merger_out}_inf_ch{channel}_ext{seq}`` so each extension stays
     debuggable in isolation and never collides with the manual Page-7
     ``_cont`` flow.
  4. Runs ``CutlessFinalizer.run_for_table`` when cutless mode is enabled
     (ComBreakDirect always uses cutless).
  5. Loads the freshly-written rows via ``load_lineup_rows`` and returns them.

The caller (typically ``LineupExtender``) formats the rows into program
dicts via ``LoadingDock.format_extension`` and hands them off to
``FactoryFloor.extend_channel``.
"""

from __future__ import annotations

import config

from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager

from .ComBreakToComBreakDirect import load_lineup_rows
from .CutlessFinalization import CutlessFinalizer
from .Merger import ShowScheduler


class InfiniteChannelExtender:
    """Build one extension chunk of lineup rows for an existing channel."""

    def __init__(self):
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()

    def generate_chunk(self, channel_number, infinite_meta):
        """Run ShowScheduler (+ CutlessFinalizer) and return the new lineup rows.

        Args:
            channel_number: The channel being extended; used in the chunk's
                table name so multiple channels can extend concurrently
                without table-name collisions.
            infinite_meta: The channel's ``_infinite_meta`` dict. Must
                contain ``toonami_version``. ``cutless_enabled`` defaults
                to ``True`` (ComBreakDirect's only supported mode).
                ``extension_seq`` is the *current* sequence number; this
                method increments it for the new chunk.

        Returns:
            A tuple ``(rows, output_table)`` where ``rows`` is a list of
            normalized lineup dicts (same shape as
            ``ComBreakToComBreakDirect.load_lineup_rows``) and
            ``output_table`` is the name of the SQLite table the rows live
            in (useful for diagnostics). Returns ``([], None)`` if
            ShowScheduler produced an empty chunk.

        Raises:
            RuntimeError on configuration errors or hard finalizer failure.
            The caller is responsible for translating these into
            ``_infinite_meta.consecutive_failures`` bumps and
            ``_infinite_meta.enabled`` toggles.
        """
        toonami_version = infinite_meta.get('toonami_version')
        if not toonami_version:
            raise RuntimeError(
                "infinite_meta is missing 'toonami_version' — cannot generate chunk"
            )

        cont_config = getattr(config, 'TOONAMI_CONFIG_CONT', {}).get(toonami_version)
        if not cont_config:
            raise RuntimeError(
                f"No TOONAMI_CONFIG_CONT entry for version '{toonami_version}'"
            )

        cutless_enabled = bool(infinite_meta.get('cutless_enabled', True))
        # extension_seq in meta is the *count* of completed extensions; the
        # new chunk takes the next number.
        seq = int(infinite_meta.get('extension_seq') or 0) + 1
        output_table = (
            f"{cont_config['merger_out']}_inf_ch{channel_number}_ext{seq}"
        )

        # Tracks the per-show cursor across invocations via the
        # ``last_used_episode_block`` table. ``reuse_episode_blocks=True``
        # makes the scheduler cycle back to a show's first block when it
        # exhausts the cursor, keeping generation truly unbounded.
        merger = ShowScheduler(
            reuse_episode_blocks=True,
            continue_from_last_used_episode_block=True,
            uncut=bool(cont_config.get('uncut', False)),
        )
        merger.run(
            cont_config['merger_bump_list'],
            cont_config['encoder_in'],
            output_table,
        )

        if not self.db_manager.table_exists(output_table):
            raise RuntimeError(
                f"ShowScheduler did not produce output table '{output_table}'"
            )

        consumable_table = output_table
        if cutless_enabled:
            cutless_table = f"{output_table}_cutless"
            finalizer = CutlessFinalizer()
            success = finalizer.run_for_table(output_table, cutless_table)
            if not success:
                raise RuntimeError(
                    f"CutlessFinalizer.run_for_table failed for '{output_table}'"
                )
            consumable_table = cutless_table

        rows = load_lineup_rows(consumable_table, self.db_manager)
        if not rows:
            # The scheduler can produce an empty chunk if the bump pool is
            # entirely exhausted. Caller treats this as a soft failure.
            return [], consumable_table

        return rows, consumable_table
