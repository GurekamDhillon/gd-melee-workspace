"""Smoke-test the deployed Windows launcher without SDK/toolset DLL lookup paths."""
import os
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--tls-probe', required=True, type=Path,
                        help='build-only update_tls_probe executable (not shipped)')
    args = parser.parse_args()
    root = args.root.resolve()
    env = {key.upper(): value for key, value in os.environ.items()}
    for key in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH',
                'QT_QPA_PLATFORMTHEME', 'QT_STYLE_OVERRIDE'):
        env.pop(key, None)
    # Without an attached console Qt answers --version with a modal message box, which
    # would block this check until the timeout; ask for plain output instead.
    env['QT_COMMAND_LINE_PARSER_NO_GUI_MESSAGE_BOXES'] = '1'
    system = env['SYSTEMROOT']
    env['PATH'] = system+'\\System32;'+system
    for executable in (root/'launcher/bin/gd-melee-launcher.exe', root/'GD Melee.exe'):
        try:
            result = subprocess.run([str(executable), '-platform', 'offscreen', '--version'],
                                    env=env, capture_output=True, text=True, timeout=20,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f'deployed launcher smoke failed: {error}', file=sys.stderr)
            return 1
        print(result.stdout, end='')
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            print(f'deployed launcher smoke failed: {result.returncode}', file=sys.stderr)
            return 1
    cert_dir = Path(__file__).resolve().parent/'launcher/qt/testdata'
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/update.json':
                self.send_error(404)
                return
            body = b'GDMELEE-TLS-RUNTIME-OK'
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *unused):
            pass

    # The probe uses only this deployed plugin directory. It adds the fixture CA
    # to this request, never the Windows certificate store, and ignores no errors.
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(str(cert_dir/'tls-localhost.pem'), str(cert_dir/'tls-localhost-key.pem'))
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
    probe = root/f'launcher/bin/.tls-probe-{os.getpid()}.exe'
    thread.start()
    try:
        # Same bin/qt.conf/DLL directory as the launcher, under an SDK-free PATH.
        # Temporary test helper is removed before this package can be guarded.
        shutil.copy2(args.tls_probe, probe)
        result = subprocess.run([str(probe), f'https://127.0.0.1:{server.server_port}/update.json',
                                 str(cert_dir/'tls-localhost.pem')], env=env, capture_output=True,
                                text=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        print(result.stdout, end='')
        if result.returncode or 'HTTPS OK (backend=schannel)' not in result.stdout:
            print(result.stderr, file=sys.stderr)
            print(f'deployed HTTPS smoke failed: {result.returncode}', file=sys.stderr)
            return 1
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f'deployed HTTPS smoke failed: {error}', file=sys.stderr)
        return 1
    finally:
        probe.unlink(missing_ok=True)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    print('deployed launcher runtime and HTTPS OK (SDK-free PATH)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
