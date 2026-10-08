"""Exercise the real server socket after a guest disappears during relaying."""
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest


class DisconnectTests(unittest.TestCase):
    def test_midgame_loss_reopens_same_room_and_introduces_new_guest(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        server = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name('gdmelee_server.py')),
             '--bind', '127.0.0.1', '--port', str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        host = guest = replacement = None
        try:
            def client():
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind(('127.0.0.1', 0))
                s.settimeout(0.25)
                return s

            target = ('127.0.0.1', port)
            host, guest = client(), client()

            def exchange(s, packet, prefix):
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    s.sendto(packet, target)
                    try:
                        answer = s.recv(2048)
                    except (socket.timeout, ConnectionResetError):
                        continue
                    if answer.startswith(prefix):
                        return answer
                self.fail('server stopped answering ' + prefix.decode())

            code = exchange(host, b'GDMRREG -', b'GDMRCODE ').split()[1]
            exchange(guest, b'GDMRJOIN ' + code + b' -', b'GDMRPEER ')
            exchange(host, b'GDMRKA', b'GDMRKA')  # drain its introduction
            host.sendto(b'GDMRRELAY', target)
            guest.close()
            guest = None
            # A running host continues sending frames to the closed guest port.
            # Windows returns ICMP port-unreachable to the server's UDP socket.
            for _ in range(30):
                host.sendto(b'GDMDsynthetic-frame', target)
                time.sleep(0.02)
            self.assertIsNone(server.poll(), 'server process exited')
            reopened = exchange(host, b'GDMRREG -', b'GDMRCODE ').split()[1]
            self.assertEqual(reopened, code)
            replacement = client()
            peer = exchange(replacement, b'GDMRJOIN ' + code + b' -', b'GDMRPEER ')
            self.assertEqual(peer.split()[1], ('127.0.0.1:%d' % host.getsockname()[1]).encode())
            exchange(host, b'GDMRKA', b'GDMRPEER ')
            # The resumed pair must carry data too, not only room controls.
            replacement.sendto(b'GDMDreplacement-to-host', target)
            answer = host.recv(2048)
            while answer.startswith(b'GDMR'):
                answer = host.recv(2048)
            self.assertEqual(answer, b'GDMDreplacement-to-host')
            host.sendto(b'GDMDhost-to-replacement', target)
            self.assertEqual(replacement.recv(2048), b'GDMDhost-to-replacement')
        finally:
            for s in (host, guest, replacement):
                if s is not None:
                    s.close()
            server.terminate()
            server.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
