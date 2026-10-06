"""No game or public server needed: python -m unittest discover -s tools/netplay/server."""
import struct
import unittest
from unittest.mock import patch

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

    def test_v5_handshakes_forward_unchanged(self):
        self.pair()
        for kind, source, target in [(1, self.guest, self.host), (2, self.host, self.guest)]:
            packet = self.handshake(5, kind)
            self.server.datagram_received(packet, source)
            self.assertEqual(self.transport.sent.pop(), (packet, target))

    def test_incompatible_handshake_reports_version_to_both_peers(self):
        for version in [1, 2, 3, 4, 6, 256]:
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

    def test_random_retry_resends_same_match_without_dropping_partner(self):
        self.ctl('RAND 0123456789abcdef -', self.host)
        self.ctl('RAND 0123456789abcdef -', self.guest)
        room = self.server.by_addr[self.host]
        for address, role in [(self.host, b'HOST'), (self.guest, b'GUEST')]:
            self.transport.sent.clear()  # the first MATCH reply was lost
            self.ctl('RAND 0123456789abcdef -', address)
            self.assertIs(self.server.by_addr.get(address), room)
            self.assertIs(self.server.by_addr.get(self.guest), room)
            self.assertFalse(self.server.queue)
            self.assertEqual(self.transport.sent[-1][1], address)
            self.assertTrue(self.transport.sent[-1][0].startswith(b'GDMRMATCH ' + role))
            self.assertIn(room.code.encode(), self.transport.sent[-1][0])

    def test_waiting_queue_has_a_bound_but_existing_waiters_can_retry(self):
        with patch('gdmelee_server.MAX_QUEUE', 3, create=True):
            for index in range(5):
                self.ctl('RAND %016x -' % index, ('127.0.0.1', 52000 + index))
            self.assertEqual(len(self.server.queue), 3)
            self.assertEqual(self.transport.sent[-1][0], b'GDMRERR server queue full')
            first = ('127.0.0.1', 52000)
            waiter = self.server.queue[first]
            self.ctl('RAND 0000000000000000 -', first)
            self.assertIs(self.server.queue[first], waiter)
            self.assertTrue(self.transport.sent[-1][0].startswith(b'GDMRQUEUED'))

    def test_guest_switching_rooms_detaches_old_relay_membership(self):
        old_code = self.pair()
        second_host = ('127.0.0.1', 51003)
        self.ctl('REG -', second_host)
        second = self.server.by_addr[second_host]
        self.ctl('JOIN ' + second.code + ' -', self.guest)
        self.assertIsNone(self.server.rooms[old_code].guest)
        self.assertIs(self.server.by_addr[self.host], self.server.rooms[old_code])
        self.transport.sent.clear()
        self.server.datagram_received(b'GDMDold-match', self.host)
        self.assertEqual(self.transport.sent, [])
        self.server.datagram_received(b'GDMDnew-match', self.guest)
        self.assertEqual(self.transport.sent, [(b'GDMDnew-match', second_host)])

    def test_self_join_does_not_evict_existing_guest(self):
        code = self.pair()
        room = self.server.rooms[code]
        self.ctl('JOIN ' + code + ' -', self.host)
        self.assertIs(self.server.by_addr.get(self.guest), room)
        self.assertEqual(room.guest, self.guest)
        self.assertEqual(self.transport.sent[-1][0], b'GDMRERR that is your own room')

    def test_random_cancel_after_matching_releases_only_guest_seat(self):
        self.ctl('RAND 0123456789abcdef -', self.host)
        self.ctl('RAND 0123456789abcdef -', self.guest)
        room = self.server.by_addr[self.host]
        self.ctl('RANDCANCEL', self.guest)
        self.assertNotIn(self.guest, self.server.by_addr)
        self.assertIsNone(room.guest)
        self.assertIs(self.server.by_addr[self.host], room)

    def test_host_registration_removes_pending_random_membership(self):
        self.ctl('RAND 0123456789abcdef -', self.host)
        self.ctl('REG -', self.host)
        room = self.server.by_addr[self.host]
        self.assertNotIn(self.host, self.server.queue)
        self.ctl('RAND 0123456789abcdef -', self.guest)
        self.assertIs(self.server.by_addr[self.host], room)
        self.assertIn(self.guest, self.server.queue)

    def test_full_queue_still_admits_an_immediately_matchable_player(self):
        with patch('gdmelee_server.MAX_QUEUE', 1):
            self.ctl('RAND 0123456789abcdef -', self.host)
            self.ctl('RAND 0123456789abcdef -', self.guest)
            self.assertFalse(self.server.queue)
            self.assertIs(self.server.by_addr.get(self.host), self.server.by_addr.get(self.guest))
            self.assertEqual(len(self.server.rooms), 1)

    def test_failed_host_registration_keeps_the_existing_guest_seat(self):
        code = self.pair()
        room = self.server.rooms[code]
        with patch('gdmelee_server.MAX_ROOMS', 1):
            self.ctl('REG -', self.guest)
        self.assertIs(self.server.by_addr.get(self.guest), room)
        self.assertEqual(room.guest, self.guest)
        self.assertEqual(self.transport.sent[-1][0], b'GDMRERR server full')


if __name__ == '__main__':
    unittest.main()
