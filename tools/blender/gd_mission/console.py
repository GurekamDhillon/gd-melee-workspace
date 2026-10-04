"""Bounded console reload request; no game process is started."""
import os
import socket


def reload_mission(port=None):
    try:
        port = int(port if port is not None else os.environ.get('MELEE_CONSOLE_PORT', '0'))
        if not 1 <= port <= 65535: return False, 'MELEE_CONSOLE_PORT is not set to a valid port'
        with socket.create_connection(('127.0.0.1', port), timeout=2) as sock:
            with sock.makefile('r', encoding='utf-8', errors='replace') as stream:
                stream.readline()  # protocol banner
                sock.sendall(b'mission reload\n')
                lines = []
                for _ in range(1024):
                    line = stream.readline()
                    if not line: return False, 'Game console disconnected'
                    line = line.rstrip('\r\n')
                    if line in ('>>> ok', '>>> error'):
                        # Some script commands report failure as text with >>> ok.
                        ok = line == '>>> ok' and not any('error' in s.lower() or 'failed' in s.lower() or 'refused' in s.lower() for s in lines)
                        return ok, '\n'.join(lines) or ('Mission reloaded' if ok else 'Mission reload refused')
                    lines.append(line)
                return False, 'Game console response exceeded limit'
    except (OSError, ValueError) as exc:
        return False, 'No game console available: ' + str(exc)
