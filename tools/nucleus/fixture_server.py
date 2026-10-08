#!/usr/bin/env python3
"""A local stand-in for the SSBM Nucleus public API (v1), for testing the in-game Nucleus browser without touching the real site.

    python tools/nucleus/fixture_server.py --port 8765 [--count 120] [--dat costume.dat] [--page-delay 0]
    set MELEE_NUCLEUS_API=http://127.0.0.1:8765/api/public/v1      (the game accepts a loopback API base and nothing else)

Everything it serves is SYNTHETIC: invented titles and authors, a generated portrait (136x188) and stock icon (24x24) per costume, and for a
costume download either a tiny hand-built HSD archive that only carries the costume symbol (enough to exercise the installer; it will not
render) or the file named by --dat (use a costume you own, kept out of git). It speaks the parts of the API the browser uses:

    GET /api/public/v1/mods?limit=&cursor=&updated_since=      keyset pages {data, next_cursor, total}; unknown or repeated params -> 400
    GET /api/public/v1/mods/removed?since=&cursor=&limit=      {data:[{id, removed_at}], next_cursor}
    GET /api/public/v1/mods/{id}/download[?file=]              302 to /media/files/..., counted in /stats
    GET /media/...                                             the generated images and DATs
    GET /stats                                                 {requests, downloads, by_path, api} as JSON (what a test asserts on)

--fail-first N answers the first N API requests with 503; --retry-after S answers the 2nd API request with 429 and Retry-After: S.
"""
import argparse
import base64
import json
import struct
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FIGHTERS = [("Mario", "Mr", "Mario", ["Nr", "Ye", "Bk", "Bu", "Gr"]), ("Fox", "Fx", "Fox", ["Nr", "Or", "La", "Gr"]),
            ("Captain Falcon", "Ca", "Captain", ["Nr", "Gy", "Re", "Wh", "Gr", "Bu"]), ("Zelda", "Zd", "Zelda", ["Nr", "Re", "Bu", "Gr", "Wh"]),
            ("Marth", "Ms", "Mars", ["Nr", "Re", "Gr", "Bk", "Wh"]), ("Falco", "Fc", "Falco", ["Nr", "Re", "Bu", "Gr"]),
            ("Sheik", "Sk", "Seak", ["Nr", "Re", "Bu", "Gr", "Wh"])]
COLOUR = {"Nr": "Default", "Re": "Red", "Bu": "Blue", "Gr": "Green", "Ye": "Yellow", "Wh": "White", "Bk": "Black", "Or": "Orange", "La": "Lavender", "Gy": "Gray"}
ADJ = ["Neon", "Ember", "Frost", "Noir", "Sunset", "Jade", "Crimson", "Ivory", "Cobalt", "Amber", "Violet", "Onyx"]
KINDS = ["costume"] * 9 + ["stage_skin", "effects", "other"]
ALLOWED = {"limit", "cursor", "updated_since", "type", "character", "q", "sort", "order", "author", "tags", "exclude_tags", "stage"}

STATE = {"requests": 0, "downloads": 0, "by_path": {}, "api": 0}
OPTS = None
MODS = []


def png(w, h, rgba_rows):
    raw = b"".join(b"\x00" + bytes(row) for row in rgba_rows)

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def art(seed, w, h):
    hue = (seed * 47) % 256
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            edge = x < 2 or y < 2 or x >= w - 2 or y >= h - 2
            r = (hue + y * 255 // h) & 255
            g = (255 - hue + x * 255 // w) & 255
            b = (hue * 3 + (x + y) * 2) & 255
            row += [255, 255, 255, 255] if edge else [r, g, b, 255]
        rows.append(row)
    return png(w, h, rows)


def hsd_costume(token, colour):
    """A header, an empty data section and two public symbols: all the installer reads."""
    syms = [f"Ply{token}5K{colour}_Share_joint", f"Ply{token}5K{colour}_Share_matanim_joint"]
    data = 0x40
    strings = b""
    pubs = b""
    for s in syms:
        pubs += struct.pack(">II", 0, len(strings))
        strings += s.encode() + b"\0"
    body = bytearray(0x20 + data) + pubs + strings
    struct.pack_into(">IIIII", body, 0, len(body), data, 0, len(syms), 0)
    return bytes(body)


def make_mods(count):
    mods = []
    for i in range(count):
        kind = KINDS[i % len(KINDS)]
        mid = 2000 + i
        name, pl, token, codes = FIGHTERS[i % len(FIGHTERS)]
        title = f"{ADJ[i % len(ADJ)]} {name}" if kind == "costume" else f"{ADJ[i % len(ADJ)]} {kind.replace('_', ' ').title()}"
        files = []
        if kind == "costume":
            for k in range(1 + (i % 3 == 0)):
                code = codes[(i + k) % len(codes)]
                fid = mid * 10 + k
                base = f"http://127.0.0.1:{OPTS.port}/media/posts/{mid}"
                files.append({"id": fid, "filename": f"{title} - Pl{pl}{code}.dat" if k == 0 else f"Pl{pl}{code}.dat", "file_type": "character_dat",
                              "character": name, "color": COLOUR[code], "slippi_safe": None,
                              "csp_url": f"{base}/{fid}_csp.png", "stock_url": f"{base}/{fid}_stock.png", "preview_url": None,
                              "download_url": f"http://127.0.0.1:{OPTS.port}/api/public/v1/mods/{mid}/download?file={fid}",
                              "file_url": f"{base}/{fid}.dat"})
        month = 1 + i % 9
        mods.append({"id": mid, "title": title, "description": f"Synthetic {kind} number {i} for testing the browser. Not a real post.",
                     "author": f"Tester {i % 5}", "type": kind, "stage": None, "tags": ["Character Costume" if kind == "costume" else kind, name],
                     "created_at": f"2026-{month:02d}-{1 + i % 27:02d}T10:00:00.000000Z", "updated_at": f"2026-{month:02d}-{1 + i % 27:02d}T12:{i % 60:02d}:00.000000Z",
                     "download_count": (i * 37) % 500, "like_count": (i * 11) % 90, "page_url": f"https://ssbmnucleus.net/post/{mid}/synthetic-{i}",
                     "thumbnail_url": None, "screenshots": [], "download_url": f"http://127.0.0.1:{OPTS.port}/api/public/v1/mods/{mid}/download",
                     "zip_url": None, "files": files})
    mods.sort(key=lambda m: (m["updated_at"], m["id"]), reverse=True)
    return mods


class H(BaseHTTPRequestHandler):
    server_version = "nucleus-fixture"

    def log_message(self, fmt, *a):
        pass

    def send(self, code, body, ctype="application/json", extra=()):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def err(self, code, msg):
        self.send(code, {"error": {"code": "error", "message": msg}})

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query, keep_blank_values=True)
        STATE["requests"] += 1
        STATE["by_path"][u.path] = STATE["by_path"].get(u.path, 0) + 1
        if u.path == "/stats":
            return self.send(200, STATE)
        if u.path.startswith("/media/"):
            return self.media(u.path)
        if not u.path.startswith("/api/public/v1/"):
            return self.err(404, "not found")
        STATE["api"] += 1
        if OPTS.page_delay:
            time.sleep(OPTS.page_delay)
        if STATE["api"] <= OPTS.fail_first:
            return self.err(503, "try again")
        if OPTS.retry_after and STATE["api"] == 2:
            return self.send(429, {"error": {"code": "rate_limited", "message": "slow down"}}, extra=[("Retry-After", str(OPTS.retry_after))])
        path = u.path[len("/api/public/v1"):]
        for k, v in q.items():
            if len(v) != 1:
                return self.err(400, f"repeated parameter {k}")
        if path == "/mods":
            for k in q:
                if k not in ALLOWED:
                    return self.err(400, f"unknown parameter {k}")
            return self.list_mods(q)
        if path == "/mods/removed":
            return self.send(200, {"data": [{"id": r, "removed_at": "2026-09-01T00:00:00Z"} for r in OPTS.removed], "next_cursor": None})
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "mods" and parts[2] == "download":
            STATE["downloads"] += 1
            fid = q.get("file", [""])[0]
            return self.send(302, b"", extra=[("Location", f"http://127.0.0.1:{OPTS.port}/media/files/{parts[1]}/{fid or 'all'}.dat")])
        return self.err(404, "not found")

    def list_mods(self, q):
        mods = [m for m in MODS if m["type"] == q["type"][0]] if "type" in q else MODS
        if "updated_since" in q:
            since = q["updated_since"][0].rstrip("Z")
            mods = [m for m in mods if m["updated_at"][:19] >= since[:19]]
        limit = int(q.get("limit", ["50"])[0])
        if not 1 <= limit <= 100:
            return self.err(400, "limit")
        start = 0
        if "cursor" in q:
            try:
                start = int(base64.urlsafe_b64decode(q["cursor"][0] + "==").decode())
            except Exception:
                return self.err(400, "cursor")
        page = mods[start:start + limit]
        nxt = base64.urlsafe_b64encode(str(start + limit).encode()).decode().rstrip("=") if start + limit < len(mods) else None
        self.send(200, {"data": page, "next_cursor": nxt, "total": len(mods)})

    def media(self, path):
        name = path.rsplit("/", 1)[-1]
        if name.endswith("_csp.png"):
            return self.send(200, art(int(name.split("_")[0]), 136, 188), "image/png")
        if name.endswith("_stock.png"):
            return self.send(200, art(int(name.split("_")[0]), 24, 24), "image/png")
        if path.startswith("/media/files/"):
            parts = path.split("/")
            mid, fid = int(parts[3]), parts[4][:-4]
            for m in MODS:
                for f in m["files"]:
                    if m["id"] == mid and str(f["id"]) == fid:
                        if OPTS.dat:
                            with open(OPTS.dat, "rb") as fp:
                                return self.send(200, fp.read(), "application/octet-stream")
                        fi = next(x for x in FIGHTERS if x[0] == f["character"])
                        code = next(c for c, n in COLOUR.items() if n == f["color"])
                        return self.send(200, hsd_costume(fi[2], code), "application/octet-stream")
        self.err(404, "not found")


def main():
    global OPTS, MODS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--count", type=int, default=120)
    ap.add_argument("--dat", default="", help="serve this file for every costume download (a real costume of yours; never commit it)")
    ap.add_argument("--page-delay", type=float, default=0.0)
    ap.add_argument("--fail-first", type=int, default=0)
    ap.add_argument("--retry-after", type=int, default=0)
    ap.add_argument("--removed", type=int, nargs="*", default=[])
    OPTS = ap.parse_args()
    MODS = make_mods(OPTS.count)
    srv = ThreadingHTTPServer(("127.0.0.1", OPTS.port), H)
    print(f"nucleus fixture server on http://127.0.0.1:{OPTS.port}/api/public/v1  ({len(MODS)} synthetic mods)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
