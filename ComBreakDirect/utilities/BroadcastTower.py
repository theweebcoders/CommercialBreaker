"""
BroadcastTower - Beams live stream to multiple clients simultaneously.

Like a TV broadcast tower - receives signal from studio and broadcasts it.
No recording, no buffering, no history. Just live transmission.

Architecture:
- Studio (Builder thread): Has the "tape" with full content, encodes chunks
- BroadcastTower: Receives chunks and immediately beams to all antennas
- Antenna (Subscriber): Each client's receiver, minimal buffer for signal stability
"""

import threading
import time
from collections import deque
from typing import Iterator, Optional


class BroadcastTower:
    """
    Broadcasts live MPEG-TS stream to multiple clients simultaneously.

    NO BUFFERING - receives chunk from studio, broadcasts to all antennas, moves on.
    Antennas join at live position (whatever is being broadcast NOW).
    """

    def __init__(self):
        """
        Initialize broadcast tower.

        NO BUFFERING - just beams current chunk to all antennas.
        Only transmits what's being sent RIGHT NOW.
        """
        # Lock for thread-safe access
        self.lock = threading.Lock()

        # Condition variable for signaling new chunks
        self.condition = threading.Condition(self.lock)

        # Active antennas (subscribers receiving broadcast)
        self.antennas = []  # List of Antenna (Subscriber) objects

        # Stats
        self.total_chunks_broadcast = 0
        self.total_mb_broadcast = 0

        print(f"[BROADCAST_TOWER] Tower online (live broadcast only, no buffering)")

    def broadcast(self, chunk: bytes):
        """
        Broadcast chunk to all active antennas.

        No buffering - chunk is immediately beamed to all antennas and discarded.

        Args:
            chunk: MPEG-TS chunk bytes from studio
        """
        with self.condition:
            # Immediately beam to all antennas (no buffering)
            for antenna in self.antennas:
                antenna.receive(chunk)

            # Update stats
            self.total_chunks_broadcast += 1
            self.total_mb_broadcast += len(chunk) / 1024 / 1024

            # Wake up any waiting antennas
            self.condition.notify_all()

    def connect_antenna(self, client_id: str) -> 'Antenna':
        """
        Connect new antenna to receive broadcast.

        Antenna joins at LIVE position - no historical signal sent.

        Args:
            client_id: Identifier for this client (for logging)

        Returns:
            Antenna object for receiving broadcast
        """
        with self.lock:
            antenna = Antenna(client_id, self)
            self.antennas.append(antenna)
            print(f"[BROADCAST_TOWER] Antenna {client_id} connected at LIVE position ({len(self.antennas)} active)")
            return antenna

    def disconnect_antenna(self, antenna: 'Antenna'):
        """
        Disconnect antenna from broadcast.

        Args:
            antenna: Antenna to disconnect
        """
        with self.lock:
            if antenna in self.antennas:
                self.antennas.remove(antenna)
                print(f"[BROADCAST_TOWER] Antenna {antenna.client_id} disconnected ({len(self.antennas)} active)")

    def has_antennas(self) -> bool:
        """Check if any antennas are connected."""
        with self.lock:
            return len(self.antennas) > 0

    def get_stats(self) -> dict:
        """Get broadcast tower statistics."""
        with self.lock:
            return {
                'active_antennas': len(self.antennas),
                'total_chunks_broadcast': self.total_chunks_broadcast,
                'total_mb_broadcast': self.total_mb_broadcast
            }


class Antenna:
    """
    Individual antenna receiving broadcast from tower.

    Minimal signal buffer for network stability.
    If signal gets too weak (can't keep up), drops old signal to stay live.
    """

    def __init__(self, client_id: str, broadcast_tower: BroadcastTower):
        """
        Initialize antenna.

        Args:
            client_id: Identifier for logging
            broadcast_tower: Parent broadcast tower
        """
        self.client_id = client_id
        self.broadcast_tower = broadcast_tower

        # Signal buffer - enough for network stability without allowing read-ahead
        # ~132 chunks = ~2 seconds buffer (smooth playback, prevents signal loss)
        # Still can't buffer way ahead like old 60-second queue
        max_signal_buffer = 132  # 2 seconds at ~66 chunks/sec
        self.signal_buffer = deque(maxlen=max_signal_buffer)

        # Lock for antenna buffer
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

        # Track if antenna is active
        self.active = True

        # Stats
        self.chunks_received = 0
        self.signal_lost = 0  # Chunks dropped due to weak signal (can't keep up)

    def receive(self, chunk: bytes):
        """
        Receive chunk from broadcast tower (called by BroadcastTower).

        Args:
            chunk: MPEG-TS chunk bytes
        """
        with self.condition:
            if not self.active:
                return

            # Check if buffer full (signal too weak - can't keep up with broadcast)
            if len(self.signal_buffer) == self.signal_buffer.maxlen:
                self.signal_lost += 1

            self.signal_buffer.append(chunk)
            self.condition.notify()

    def read_signal(self, timeout: float = 30.0) -> Optional[bytes]:
        """
        Read next chunk from antenna's signal buffer.

        Args:
            timeout: How long to wait for next signal

        Returns:
            Chunk bytes, or None if timeout/disconnected
        """
        with self.condition:
            # Wait for signal or timeout
            deadline = time.time() + timeout
            while self.active and not self.signal_buffer:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                self.condition.wait(timeout=remaining)

            if not self.active:
                return None

            if self.signal_buffer:
                chunk = self.signal_buffer.popleft()
                self.chunks_received += 1
                return chunk

            return None

    def __iter__(self) -> Iterator[bytes]:
        """
        Iterate over signal as it arrives.

        Yields chunks at real-time rate to prevent greedy clients from
        draining buffer faster than tower broadcasts.
        """
        import time

        chunk_interval = 0.013  # 13ms per chunk (matches studio broadcast rate)
        last_yield_time = time.time()

        while self.active:
            chunk = self.read_signal(timeout=30.0)
            if chunk is None:
                if not self.active:
                    break
                # Timeout - check if still active
                continue

            # Rate limit yielding to prevent greedy clients from draining buffer
            now = time.time()
            time_since_last = now - last_yield_time
            if time_since_last < chunk_interval:
                time.sleep(chunk_interval - time_since_last)

            last_yield_time = time.time()
            yield chunk

    def disconnect(self):
        """
        Disconnect antenna and clean up.

        Should be called when client disconnects.
        """
        with self.condition:
            self.active = False
            self.condition.notify()

        # Disconnect from broadcast tower
        self.broadcast_tower.disconnect_antenna(self)

        if self.signal_lost > 0:
            print(f"[ANTENNA] {self.client_id}: Received {self.chunks_received} chunks, lost signal {self.signal_lost} times")
        else:
            print(f"[ANTENNA] {self.client_id}: Received {self.chunks_received} chunks")
