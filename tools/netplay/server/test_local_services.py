"""Real loopback UDP and TCP on one ephemeral port; synthetic reports only."""
import asyncio
from pathlib import Path
import sys
import tempfile
import unittest

from gdmelee_server import Server

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'release'))
from crash_upload_server import start_crash_upload


class LocalServices(unittest.IsolatedAsyncioTestCase):
    async def test_matchmaking_and_old_crash_report_share_port(self):
        with tempfile.TemporaryDirectory() as root:
            tcp = await start_crash_upload('127.0.0.1', 0, root)
            port = tcp.sockets[0].getsockname()[1]
            udp = client = None
            try:
                loop = asyncio.get_running_loop()
                udp, _ = await loop.create_datagram_endpoint(Server, local_addr=('127.0.0.1', port))
                answer = loop.create_future()

                class Receiver(asyncio.DatagramProtocol):
                    def datagram_received(self, data, addr):
                        if not answer.done():
                            answer.set_result(data)

                client, _ = await loop.create_datagram_endpoint(Receiver, remote_addr=('127.0.0.1', port))
                client.sendto(b'GDMRREG 127.0.0.1:51001')
                self.assertTrue((await asyncio.wait_for(answer, 3)).startswith(b'GDMRCODE '))
                reader, writer = await asyncio.open_connection('127.0.0.1', port)
                body = b"==== GD's Melee crash report ====\nversion:         0.1.1\nreason:          synthetic local test\n"
                writer.write(b'POST /crash HTTP/1.1\r\nHost: localhost\r\nContent-Type: text/plain\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
                await writer.drain()
                response = await asyncio.wait_for(reader.read(), 3)
                writer.close()
                await writer.wait_closed()
                self.assertTrue(response.startswith(b'HTTP/1.1 200 OK'), response)
                self.assertEqual(len(list(Path(root).rglob('*.log'))), 1)
            finally:
                if client:
                    client.close()
                if udp:
                    udp.close()
                tcp.close()
                await tcp.wait_closed()
