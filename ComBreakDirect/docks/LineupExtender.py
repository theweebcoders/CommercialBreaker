"""Per-channel scheduler that keeps a ComBreakDirect channel's lineup infinite.

One ``LineupExtender`` per infinite channel arms a single ``threading.Timer``
to fire ``INFINITE_EXTEND_LEAD_MS`` before the channel's last program ends.
The channel is clock-anchored at creation, so we know the exact wall-clock
moment the last program stops — no polling needed.

When the timer fires it runs ``InfiniteChannelExtender.generate_chunk``,
formats the new rows via ``LoadingDock.format_extension``, hands them to
``FactoryFloor.extend_channel`` (which appends under the factory lock and
persists), then computes the new end time and arms a fresh timer. The
channel never runs out as long as the server is running, regardless of
whether anyone is currently streaming.

Safety: if the current end is already within the lead window (or in the
past), the timer fires immediately. This covers brand-new tiny test
channels, restarts that picked up a channel whose end has elapsed, and
recovery from previous extension failures.

Failures retry on a short backoff (``RETRY_AFTER_FAILURE_MS``). After
``MAX_CONSECUTIVE_FAILURES`` consecutive failures the extender disables
infinite mode for the channel and stops scheduling — the channel keeps
playing existing programs via Studio's modulo loop without further noise.
"""

from __future__ import annotations

import shutil
import threading
import traceback
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

import config

from API.utils.ErrorManager import get_error_manager

if TYPE_CHECKING:  # pragma: no cover
    from .FactoryFloor import FactoryFloor


class LineupExtender:
    """Schedules one ``threading.Timer`` per channel to keep it infinite."""

    # How long before the channel's end to fire the extension.
    DEFAULT_EXTEND_LEAD_MS = 3 * 60 * 60 * 1000  # 3 hours
    DEFAULT_MIN_FREE_DISK_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
    # When an extension fails recoverably, retry sooner than the next normal
    # extension would have fired.
    RETRY_AFTER_FAILURE_MS = 5 * 60 * 1000  # 5 minutes
    MAX_CONSECUTIVE_FAILURES = 3

    def __init__(self, factory_floor: "FactoryFloor", channel_number):
        self.factory_floor = factory_floor
        self.channel_number = channel_number
        self.channel_key = str(channel_number)
        self.error_manager = get_error_manager()

        self.lead_ms = int(
            getattr(config, 'INFINITE_EXTEND_LEAD_MS', self.DEFAULT_EXTEND_LEAD_MS)
        )
        self.min_free_disk_bytes = int(
            getattr(
                config, 'INFINITE_MIN_FREE_DISK_BYTES',
                self.DEFAULT_MIN_FREE_DISK_BYTES,
            )
        )

        self._timer: Optional[threading.Timer] = None
        self._cancelled = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lazy LoadingDock access — see Step-6 ordering note in the plan.
    # ------------------------------------------------------------------
    @property
    def loading_dock(self):
        return self.factory_floor.loading_dock

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self):
        """Compute the next extension time and arm the timer.

        Named ``start`` for symmetry with the prior Thread-subclass design —
        FactoryFloor calls ``extender.start()`` exactly the same way.
        """
        self._schedule_next()

    def cancel(self):
        """Cancel any pending timer. Idempotent. Call when the channel is removed."""
        with self._lock:
            self._cancelled = True
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def is_active(self) -> bool:
        """Whether a future extension is still scheduled or running."""
        with self._lock:
            return not self._cancelled

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    def _schedule_next(self, delay_override_ms: Optional[int] = None):
        with self._lock:
            if self._cancelled:
                return
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

            channel_data = self.factory_floor.get_channel(self.channel_number)
            if channel_data is None:
                self._cancelled = True
                return

            meta = channel_data.get('_infinite_meta') or {}
            if not meta.get('enabled'):
                # Don't reschedule. If something re-enables, the caller can
                # call start() again.
                return

            if delay_override_ms is not None:
                delay_ms = max(0, int(delay_override_ms))
            else:
                delay_ms = self._compute_delay_ms(channel_data)

            delay_s = delay_ms / 1000.0
            timer = threading.Timer(delay_s, self._on_timer_fire)
            timer.daemon = True
            timer.name = f"LineupExtenderTimer-Ch{self.channel_number}"
            self._timer = timer
            timer.start()

        fire_at = datetime.now(timezone.utc) + timedelta(seconds=delay_s)
        print(
            f"[LINEUP_EXTENDER] Channel {self.channel_number}: next extension "
            f"in {delay_s/60:.1f} min (fires {fire_at.isoformat()})"
        )

    def _compute_delay_ms(self, channel_data) -> int:
        """Milliseconds from now until ``lead_ms`` before the channel ends.

        Returns 0 (fire immediately) for channels shorter than the lead time
        and for channels whose end has already passed.
        """
        programs = channel_data.get('programs') or []
        if not programs:
            return 0

        last_stop_iso = programs[-1].get('stop')
        if not last_stop_iso:
            return 0

        try:
            last_stop = datetime.fromisoformat(
                last_stop_iso.replace('Z', '+00:00')
            )
        except ValueError:
            return 0

        ms_until_end = (
            (last_stop - datetime.now(timezone.utc)).total_seconds() * 1000
        )
        # Fire ``lead_ms`` before the end. If the end is closer than the
        # lead window (or already past), fire immediately.
        return max(0, int(ms_until_end - self.lead_ms))

    # ------------------------------------------------------------------
    # Extension execution (timer callback)
    # ------------------------------------------------------------------
    def _on_timer_fire(self):
        try:
            self._do_extension()
        except Exception as exc:  # defensive — never let the timer die silently
            self._record_unexpected_failure(exc)
            self._schedule_next(delay_override_ms=self.RETRY_AFTER_FAILURE_MS)

    def _do_extension(self):
        channel_data = self.factory_floor.get_channel(self.channel_number)
        if channel_data is None:
            print(
                f"[LINEUP_EXTENDER] Channel {self.channel_number} no longer "
                f"in FactoryFloor — cancelling extender"
            )
            self.cancel()
            return

        meta = channel_data.get('_infinite_meta') or {}
        if not meta.get('enabled'):
            return  # disabled externally; do not reschedule

        if int(meta.get('consecutive_failures') or 0) >= self.MAX_CONSECUTIVE_FAILURES:
            self._disable(
                channel_data,
                f"Max consecutive failures ({self.MAX_CONSECUTIVE_FAILURES}) reached",
            )
            return

        if not self._has_disk_space():
            self._bump_failures(channel_data, "Insufficient free disk space")
            self._schedule_next(delay_override_ms=self.RETRY_AFTER_FAILURE_MS)
            return

        try:
            new_programs = self._build_extension(channel_data, meta)
        except Exception as exc:
            self._bump_failures(
                channel_data,
                f"InfiniteChannelExtender / format_extension failed: {exc}",
            )
            self._schedule_next(delay_override_ms=self.RETRY_AFTER_FAILURE_MS)
            return

        if not new_programs:
            self._disable(
                channel_data,
                "ShowScheduler produced no new programs to extend with",
            )
            return

        # Race check: channel may have been deleted during the build.
        if self.factory_floor.get_channel(self.channel_number) is None:
            print(
                f"[LINEUP_EXTENDER] Channel {self.channel_number} deleted during "
                f"build — discarding {len(new_programs)} programs"
            )
            self.cancel()
            return

        new_length = self.factory_floor.extend_channel(
            self.channel_number, new_programs
        )
        if new_length is None:
            self._bump_failures(channel_data, "extend_channel returned None")
            self._schedule_next(delay_override_ms=self.RETRY_AFTER_FAILURE_MS)
            return

        print(
            f"[LINEUP_EXTENDER] Channel {self.channel_number}: appended "
            f"{len(new_programs)} programs (now {new_length} total)"
        )
        # Schedule the next extension based on the new (extended) end.
        self._schedule_next()

    # ------------------------------------------------------------------
    # Disk-space gate
    # ------------------------------------------------------------------
    def _has_disk_space(self) -> bool:
        try:
            target = self.factory_floor.storage_path.parent
            stats = shutil.disk_usage(str(target))
            return stats.free >= self.min_free_disk_bytes
        except Exception:
            return True  # best-effort — don't block extension on a stat failure

    # ------------------------------------------------------------------
    # The actual build
    # ------------------------------------------------------------------
    def _build_extension(self, channel_data, meta):
        # Local import to avoid a ToonamiTools <-> ComBreakDirect import
        # cycle at module-load time.
        from ToonamiTools.InfiniteChannelExtender import InfiniteChannelExtender

        extender = InfiniteChannelExtender()
        rows, _table = extender.generate_chunk(self.channel_number, meta)
        if not rows:
            return []

        return self.loading_dock.format_extension(rows, channel_data)

    # ------------------------------------------------------------------
    # Failure bookkeeping
    # ------------------------------------------------------------------
    def _bump_failures(self, channel_data, message) -> None:
        meta = channel_data.setdefault('_infinite_meta', {})
        meta['consecutive_failures'] = int(meta.get('consecutive_failures') or 0) + 1
        attempt = meta['consecutive_failures']
        self.error_manager.send_warning(
            source="LineupExtender",
            operation="extension",
            message=f"Channel {self.channel_number} extension failed (recoverable)",
            details=message,
            suggestion=(
                f"Retrying in {self.RETRY_AFTER_FAILURE_MS/1000/60:.0f} min. "
                f"Attempt {attempt} of {self.MAX_CONSECUTIVE_FAILURES} before "
                f"the channel's infinite mode is disabled."
            ),
        )

    def _record_unexpected_failure(self, exc) -> None:
        self.error_manager.send_error_level(
            source="LineupExtender",
            operation="extension",
            message=f"Channel {self.channel_number} extender hit unexpected error",
            details=f"{exc}\n{traceback.format_exc()}",
            suggestion="A retry is scheduled. Investigate logs if this recurs.",
        )

    def _disable(self, channel_data, reason) -> None:
        meta = channel_data.setdefault('_infinite_meta', {})
        meta['enabled'] = False
        # Best-effort persist so the disabled state survives a restart.
        try:
            self.factory_floor._save_channels()
        except Exception:
            pass
        self.error_manager.send_error_level(
            source="LineupExtender",
            operation="disable",
            message=f"Channel {self.channel_number} infinite extension disabled",
            details=reason,
            suggestion=(
                "The channel will keep playing existing programs via the "
                "Studio's modulo loop. To restore infinite mode, fix the "
                "underlying issue and recreate the channel."
            ),
        )
        self.cancel()
