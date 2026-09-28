"""No game or public server needed: python -m unittest discover -s tools/netplay/server."""
import struct
import unittest

from gdmelee_server import Server


class Transport:
    def __init__(self):
        self.sent = []

    def sendto(self, data, addr):
        self.sent.append((data, addr))


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.transport = Transport()
        self.server.connection_made(self.transport)
        self.host = ('127.0.0.1', 51001)
        self.guest = ('127.0.0.1', 51002)

    def ctl(self, text, addr):
        self.server.datagram_received(b'GDMR' + text.encode(), addr)

    def pair(self):
        self.ctl('REG 127.0.0.1:51001', self.host)
        code = next(iter(self.server.rooms))
        self.ctl('JOIN ' + code + ' 127.0.0.1:51002', self.guest)
        self.transport.sent.clear()
        return code

    @staticmethod
    def handshake(version, kind=1):
        # gw_net.c: 18-byte LE header; HELLO/ACCEPT begin with u16 version.
        return b'GDMD' + struct.pack('<HBBIIIH', 0x4e47, kind, 0, 0, 0, 0, 0) + struct.pack('<H', version) + bytes(30)

    def test_v3_handshakes_forward_unchanged(self):
        self.pair()
        for kind, source, target in [(1, self.guest, self.host), (2, self.host, self.guest)]:
            packet = self.handshake(3, kind)
            self.server.datagram_received(packet, source)
            self.assertEqual(self.transport.sent.pop(), (packet, target))

    def test_incompatible_handshake_reports_version_to_both_peers(self):
        for version in [1, 2, 4, 256]:
            for kind in [1, 2]:
                with self.subTest(version=version, kind=kind):
                    self.setUp()
                    self.pair()
                    self.server.datagram_received(self.handshake(version, kind), self.guest)
                    self.assertEqual({addr for _, addr in self.transport.sent}, {self.host, self.guest})
                    for data, _ in self.transport.sent:
                        self.assertTrue(data.startswith(b'GDMRERR protocol version mismatch'), data)
                        self.assertIn(b'update', data)
                    self.assertFalse(self.server.rooms)
                    self.assertFalse(self.server.by_addr)

    def test_unknown_sender_cannot_inject_version_error(self):
        self.pair()
        self.server.datagram_received(self.handshake(2), ('127.0.0.1', 59999))
        self.assertEqual(self.transport.sent, [])
        self.assertEqual(len(self.server.rooms), 1)

    def test_retries_repeat_lost_version_error_after_room_is_removed(self):
        code = self.pair()
        self.server.datagram_received(self.handshake(2), self.guest)
        self.transport.sent.clear()  # simulate loss of the first error datagrams
        self.server.datagram_received(self.handshake(2), self.guest)
        self.ctl('JOIN ' + code + ' 127.0.0.1:51002', self.guest)
        self.assertEqual(len(self.transport.sent), 2)
        for data, addr in self.transport.sent:
            self.assertEqual(addr, self.guest)
            self.assertTrue(data.startswith(b'GDMRERR protocol version mismatch'), data)

    def test_random_and_persistent_room_keep_existing_wire_format(self):
        self.ctl('RAND 0123456789abcdef 127.0.0.1:51001', self.host)
        self.assertTrue(self.transport.sent[-1][0].startswith(b'GDMRQUEUED'))
        self.ctl('RAND 0123456789abcdef 127.0.0.1:51002', self.guest)
        self.assertTrue(self.transport.sent[-1][0].startswith(b'GDMRMATCH GUEST'))
        code = next(iter(self.server.rooms))
        self.ctl('REG 127.0.0.1:51001', self.host)
        self.assertEqual(next(iter(self.server.rooms)), code)


if __name__ == '__main__':
    unittest.main()
