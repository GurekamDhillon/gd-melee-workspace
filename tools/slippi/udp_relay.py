"""Deterministic local UDP relay for Slippi loopback impairment tests.

Each client sends to its own proxy port. Packets from client A are sent through
the B-side proxy socket to client B, so B sees its configured proxy as source.
The reverse path uses the A-side proxy socket. No public endpoint is accepted.
"""

from __future__ import annotations

import heapq
import random
import select
import socket
import threading
import time


class UdpRelay:
    """Two-socket localhost relay with latency, seeded loss and bounded queue."""

    def __init__(self, client_ports: tuple[int, int], latency_ms: int = 0,
                 loss_percent: float = 0, seed: int = 0, max_queue: int = 2048):
        if (len(client_ports) != 2 or any(not isinstance(p, int) or not 1 <= p <= 65535
                                          for p in client_ports) or client_ports[0] == client_ports[1]):
            raise ValueError('client_ports must be two distinct UDP ports')
        if latency_ms < 0 or not 0 <= loss_percent <= 100 or max_queue < 1:
            raise ValueError('invalid relay impairment setting')
        self.client_ports = tuple(client_ports)
        self.latency_ms = latency_ms
        self.loss_percent = loss_percent
        self.max_queue = max_queue
        self._rng = random.Random(seed)
        self._sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(2)]
        try:
            for sock in self._sockets:
                sock.bind(('127.0.0.1', 0))
                sock.setblocking(False)
        except Exception:
            for sock in self._sockets:
                sock.close()
            raise
        self.ports = tuple(sock.getsockname()[1] for sock in self._sockets)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._counts = {'received': [0, 0], 'forwarded': [0, 0],
                        'dropped': [0, 0], 'queue_dropped': [0, 0],
                        'foreign': [0, 0]}
        self._pending: list[tuple[float, int, int, bytes]] = []
        self._serial = 0
        self._closed = False

    @property
    def stats(self) -> dict:
        with self._lock:
            return {key: tuple(value) for key, value in self._counts.items()} | {
                'queued': len(self._pending)}

    def start(self) -> None:
        if self._closed:
            raise RuntimeError('relay already closed')
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name='slippi-udp-relay', daemon=True)
            self._thread.start()

    def _run(self) -> None:
        delay = self.latency_ms / 1000.0
        while not self._stop.is_set():
            with self._lock:
                next_due = self._pending[0][0] if self._pending else None
            wait = min(0.05, max(0.0, next_due - time.monotonic())) if next_due is not None else 0.05
            try:
                readable, _, _ = select.select(self._sockets, [], [], wait)
            except (OSError, ValueError):
                break
            for side, sock in enumerate(self._sockets):
                if sock not in readable:
                    continue
                try:
                    payload, address = sock.recvfrom(65535)
                except (BlockingIOError, OSError):
                    continue
                with self._lock:
                    if address != ('127.0.0.1', self.client_ports[side]):
                        self._counts['foreign'][side] += 1
                        continue
                    self._counts['received'][side] += 1
                    if self._rng.random() * 100 < self.loss_percent:
                        self._counts['dropped'][side] += 1
                        continue
                    if len(self._pending) >= self.max_queue:
                        self._counts['queue_dropped'][side] += 1
                        continue
                    self._serial += 1
                    heapq.heappush(self._pending,
                                   (time.monotonic() + delay, self._serial, side, payload))
            now = time.monotonic()
            while True:
                with self._lock:
                    if not self._pending or self._pending[0][0] > now:
                        break
                    _, _, side, payload = heapq.heappop(self._pending)
                try:
                    # The destination-side socket is the source port the receiving
                    # ENet peer expects for its configured remote endpoint.
                    self._sockets[1 - side].sendto(
                        payload, ('127.0.0.1', self.client_ports[1 - side]))
                except OSError:
                    with self._lock:
                        self._counts['queue_dropped'][side] += 1
                else:
                    with self._lock:
                        self._counts['forwarded'][side] += 1

    def close(self) -> None:
        if self._closed:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                raise RuntimeError('relay thread did not stop')
        for sock in self._sockets:
            sock.close()
        with self._lock:
            self._pending.clear()
        self._closed = True
