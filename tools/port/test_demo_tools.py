"""Protocol/runner regression checks, with no game launch."""
import io
from pathlib import Path
import tempfile
import socket
import threading
import unittest

import demo_tour
import test_demo_mods
from tools.test_support import require_game


class TourTests(unittest.TestCase):
    def test_direct_calls_and_pcall_references_are_checked(self):
        source="gd.player(1); gd.kit.text(1,2,'x'); pcall(gd.not_registered,1) -- gd.fake()\nlocal text='gd.fake()'"
        self.assertEqual(test_demo_mods.lua_calls(source),{'player','kit.text','not_registered'})
        names=test_demo_mods.registered_api()
        self.assertIn('gd.wait',names)  # Embedded Lua helper, not a luaL_Reg row.
        self.assertNotIn('gd.not_registered',names)

    def test_visible_second_monitor(self):
        env = demo_tour.tour_environment(Path('out'), Path('mods'), 51707)
        self.assertEqual(env['MELEE_WINDOW_X'], '-1080')
        self.assertEqual(env['MELEE_WINDOW_Y'], '-360')
        self.assertEqual(env['MELEE_WINDOW_HIDE'], '0')
        self.assertLessEqual(int(env['MELEE_WINDOW_W']), 1080)
        self.assertEqual(env['MELEE_TURBO'], '0')
        self.assertEqual(env['MELEE_SCRIPTS'], '0')

    def test_script_hook_errors_fail(self):
        self.assertTrue(demo_tour.script_errors('gw: script [demo_input] on_tick: bad argument'))
        self.assertTrue(demo_tour.script_errors('gw: script [x] load: unexpected symbol'))
        self.assertFalse(demo_tour.script_errors('gw: script: loaded demo_input from main.lua (gameplay)'))
        self.assertFalse(demo_tour.script_errors('gd: [demo_input] optional export not installed'))

    def test_catalogue_filter(self):
        rows=[{'id':'a','reference_only':True},{'id':'b','tour':False},{'id':'c'}]
        self.assertEqual([r['id'] for r in demo_tour.admitted(rows)], ['c'])

    def test_queued_capture_requires_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'missing.png'
            with self.assertRaises(TimeoutError):
                demo_tour.wait_file(path, timeout=0.01)

    def test_protocol_drains_response_and_raises_on_error(self):
        require_game('pc/scripts/examples/demos/console-socket/client.py')
        Console=demo_tour.load_console_class()
        with socket.socket() as server:
            server.bind(('127.0.0.1',0)); server.listen(1)
            def replies():
                conn,_=server.accept()
                with conn,conn.makefile('rb') as incoming:
                    conn.sendall(b'banner\n')
                    self.assertEqual(incoming.readline(),b'state\n')
                    conn.sendall(b'value\n>>> '); conn.sendall(b'ok\n')
                    self.assertEqual(incoming.readline(),b'bad\n')
                    conn.sendall(b'bad argument\n>>> error\n')
            thread=threading.Thread(target=replies); thread.start()
            with Console(server.getsockname()[1]) as client:
                self.assertEqual(client.command('state'),['value'])
                with self.assertRaisesRegex(RuntimeError,'bad argument'):
                    client.command('bad')
                with self.assertRaises(ValueError):
                    client.command('state\nquit')
            thread.join(timeout=2); self.assertFalse(thread.is_alive())


if __name__ == '__main__':
    unittest.main()
