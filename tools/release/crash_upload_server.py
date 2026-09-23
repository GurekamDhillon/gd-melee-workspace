"""crash_upload_server.py - receives opt-in crash reports from GD's Melee launchers.

NOT DEPLOYED. A player who said "Yes" to "Send crash reports?" in the launcher gets the COMPACT
crash report (crashlogs/crash-<time>.log, at most 64 KB, user paths already replaced by
%USERPROFILE%, no player name) uploaded by the launcher on its next start. This is the other end.

It is plain HTTP on TCP, on the same host:port as the UDP matchmaking server (netplay_server.txt,
e.g. netplay.gsd.sh:51600) - TCP and UDP port numbers are separate, so nothing collides. It runs
as its own process (it does not touch gdmelee_server.py), or gdmelee_server.py can start it
inside its own event loop:

    from crash_upload_server import start_crash_upload
    await start_crash_upload("0.0.0.0", 51600, "/var/lib/gdmelee/crashes")

Standalone:

    python3 crash_upload_server.py [--bind 0.0.0.0] [--port 51600] [--dir ./crashes]

Protocol: POST /crash, Content-Type text/plain, Content-Length <= 65536, the body a report that
starts with "==== GD's Melee crash report ====". Answers:
    200 "OK <id>"          stored
    400 "bad request"      not a report, not text, malformed HTTP
    404                    any other path/method
    413 "too large"        over 64 KB
    429 "slow down"        per-address or global limit hit
    507 "full"             the storage cap is reached

Limits (all in memory, reset on restart): per source address 3 reports an hour and 10 a day; all
sources together 300 a day; the directory at most 200 MB. Addresses are never written to disk:
the rate limiter keys on a salted hash that lives only in memory.
Stored as <dir>/<YYYY-MM-DD>/<HHMMSS>-<sha256 prefix>.log, with a small .json beside it
(received time, size, version and build id copied from the report header).
"""
import argparse
import asyncio
import datetime
import hashlib
import json
import logging
import os
import secrets
import time

MAX_BODY = 64 * 1024
MAX_HEADER = 8 * 1024
READ_TIMEOUT = 15.0
PER_ADDR_HOUR = 3
PER_ADDR_DAY = 10
GLOBAL_DAY = 300
DIR_CAP = 200 * 1024 * 1024
MAGIC = b"==== GD's Melee crash report ===="

log = logging.getLogger("crash")


class Limits:
    def __init__(self):
        self.salt = secrets.token_bytes(16)
        self.by_addr = {}  # hashed address -> [timestamps]
        self.day = []

    def key(self, addr):
        return hashlib.sha256(self.salt + addr.encode()).hexdigest()[:16]

    def allow(self, addr, now=None):
        now = time.time() if now is None else now
        k = self.key(addr)
        hits = [t for t in self.by_addr.get(k, []) if now - t < 86400]
        self.day = [t for t in self.day if now - t < 86400]
        if len(self.day) >= GLOBAL_DAY:
            return False
        if len(hits) >= PER_ADDR_DAY or len([t for t in hits if now - t < 3600]) >= PER_ADDR_HOUR:
            self.by_addr[k] = hits
            return False
        hits.append(now)
        self.by_addr[k] = hits
        self.day.append(now)
        return True


def dir_size(root):
    total = 0
    for base, _dirs, files in os.walk(root):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(base, f))
            except OSError:
                pass
    return total


def header_field(body, name):
    """'version:         0.1.1 (melee ...)' -> '0.1.1 (melee ...)' (first 40 lines only)."""
    for line in body.splitlines()[:40]:
        if line.startswith(name + ":"):
            return line.split(":", 1)[1].strip()[:200]
    return ""


def store(root, body):
    now = datetime.datetime.now(datetime.timezone.utc)
    digest = hashlib.sha256(body).hexdigest()
    day = os.path.join(root, now.strftime("%Y-%m-%d"))
    os.makedirs(day, exist_ok=True)
    stem = os.path.join(day, now.strftime("%H%M%S") + "-" + digest[:12])
    with open(stem + ".log", "wb") as f:
        f.write(body)
    text = body.decode("utf-8", "replace")
    meta = {
        "received": now.isoformat(timespec="seconds"),
        "bytes": len(body),
        "sha256": digest,
        "version": header_field(text, "version"),
        "build_id": header_field(text, "build id"),
        "exit_path": header_field(text, "exit path"),
        "reason": header_field(text, "reason"),
    }
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    return digest[:12]


async def reply(writer, code, text):
    reason = {200: "OK", 400: "Bad Request", 404: "Not Found", 413: "Payload Too Large",
              429: "Too Many Requests", 507: "Insufficient Storage"}.get(code, "Error")
    body = (text + "\n").encode()
    writer.write(("HTTP/1.1 %d %s\r\nContent-Type: text/plain\r\nContent-Length: %d\r\n"
                  "Connection: close\r\n\r\n" % (code, reason, len(body))).encode() + body)
    try:
        await writer.drain()
    except ConnectionError:
        pass


async def handle(reader, writer, root, limits):
    peer = writer.get_extra_info("peername")
    addr = peer[0] if peer else "?"
    try:
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), READ_TIMEOUT)
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, asyncio.TimeoutError, ConnectionError):
        writer.close()
        return
    try:
        if len(head) > MAX_HEADER:
            return await reply(writer, 400, "bad request")
        lines = head.decode("latin-1").split("\r\n")
        parts = lines[0].split(" ")
        if len(parts) != 3 or parts[0] != "POST" or parts[1] != "/crash":
            return await reply(writer, 404, "not found")
        length = -1
        for line in lines[1:]:
            if line.lower().startswith("content-length:"):
                try:
                    length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    length = -1
        if length < 0:
            return await reply(writer, 400, "bad request")
        if length > MAX_BODY:
            return await reply(writer, 413, "too large")
        try:
            body = await asyncio.wait_for(reader.readexactly(length), READ_TIMEOUT)
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionError):
            return
        if not body.startswith(MAGIC):
            return await reply(writer, 400, "bad request")
        try:
            body.decode("utf-8")
        except UnicodeDecodeError:
            return await reply(writer, 400, "bad request")
        if not limits.allow(addr):
            return await reply(writer, 429, "slow down")
        if dir_size(root) + len(body) > DIR_CAP:
            return await reply(writer, 507, "full")
        rid = store(root, body)
        log.info("crash report %s (%d bytes)", rid, len(body))
        return await reply(writer, 200, "OK " + rid)
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def start_crash_upload(bind, port, root):
    os.makedirs(root, exist_ok=True)
    limits = Limits()
    server = await asyncio.start_server(lambda r, w: handle(r, w, root, limits), bind, port,
                                        limit=MAX_HEADER + 1024)
    log.info("crash reports on tcp %s:%d -> %s", bind, port, root)
    return server


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=51600)
    ap.add_argument("--dir", default="crashes")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    server = await start_crash_upload(args.bind, args.port, args.dir)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
