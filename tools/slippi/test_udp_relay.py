"""Local UDP impairment relay tests using synthetic packets only."""

import random
import socket
import time
import unittest

from udp_relay import UdpRelay


class UdpRelayTest(unittest.TestCase):
    def setUp(self):
        self.clients = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(2)]
        for client in self.clients:
            client.bind(('127.0.0.1', 0))
            client.settimeout(0.6)
        self.ports = tuple(client.getsockname()[1] for client in self.clients)
        self.relay = None

    def tearDown(self):
        if self.relay is not None:
            self.relay.close()
        for client in self.clients:
            client.close()

    def start_relay(self, **kwargs):
        self.relay = UdpRelay(self.ports, **kwargs)
        self.relay.start()

    def test_bidirectional_non_neutral_payload_and_proxy_source(self):
        self.start_relay(latency_ms=0, loss_percent=0, seed=4)
        a_proxy, b_proxy = self.relay.ports
        self.clients[0].sendto(b'\x80\x01\x03A', ('127.0.0.1', a_proxy))
        data, source = self.clients[1].recvfrom(128)
        self.assertEqual(data, b'\x80\x01\x03A')
        self.assertEqual(source, ('127.0.0.1', b_proxy))
        self.clients[1].sendto(b'\x80\x02\x07B', ('127.0.0.1', b_proxy))
        data, source = self.clients[0].recvfrom(128)
        self.assertEqual(data, b'\x80\x02\x07B')
        self.assertEqual(source, ('127.0.0.1', a_proxy))
        self.assertEqual(self.relay.stats['forwarded'], (1, 1))

    def test_latency_and_complete_loss(self):
        self.start_relay(latency_ms=80, loss_percent=0, seed=4)
        start = time.monotonic()
        self.clients[0].sendto(b'change', ('127.0.0.1', self.relay.ports[0]))
        self.clients[1].settimeout(0.025)
        with self.assertRaises(socket.timeout):
            self.clients[1].recvfrom(128)
        self.clients[1].settimeout(0.6)
        data, _ = self.clients[1].recvfrom(128)
        self.assertEqual(data, b'change')
        self.assertGreaterEqual(time.monotonic() - start, 0.075)
        self.relay.close()
        self.relay = None
        self.start_relay(latency_ms=0, loss_percent=100, seed=4)
        self.clients[0].sendto(b'never', ('127.0.0.1', self.relay.ports[0]))
        self.clients[1].settimeout(0.12)
        with self.assertRaises(socket.timeout):
            self.clients[1].recvfrom(128)
        self.assertEqual(self.relay.stats['dropped'], (1, 0))

    def test_seeded_loss_sequence(self):
        seed = 17
        self.start_relay(latency_ms=0, loss_percent=50, seed=seed)
        for i in range(12):
            self.clients[0].sendto(bytes((i + 1,)), ('127.0.0.1', self.relay.ports[0]))
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            stats = self.relay.stats
            if stats['received'][0] == 12 and (stats['forwarded'][0] + stats['dropped'][0] == 12):
                break
            time.sleep(0.005)
        rng = random.Random(seed)
        expected = sum(rng.random() < 0.5 for _ in range(12))
        self.assertEqual(self.relay.stats['received'], (12, 0))
        self.assertEqual(self.relay.stats['dropped'], (expected, 0))
        self.assertEqual(self.relay.stats['forwarded'], (12 - expected, 0))


if __name__ == '__main__':
    unittest.main()
