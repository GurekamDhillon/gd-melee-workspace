#!/usr/bin/env python3
"""Interactive prompt -> in-game comm callouts, over the console socket.

Start the game with the socket open (any windowed run; keep the window visible):

    export MELEE_CONSOLE_PORT=51700          # in the same shell that launches the game
    bash tools/port/run.sh play --iso "$GW_ISO_ACE"

Then run this (Git Bash or cmd, on Windows - the socket is 127.0.0.1 only):

    python tools/port/gd_prompt.py                 # interactive prompt
    python tools/port/gd_prompt.py --who falco
    python tools/port/gd_prompt.py --send "gg"     # one message, then exit

A plain line becomes a comm callout by the current speaker. Lines starting with ":"

    :who fox|falco|peppy|slippy|custom   change the speaker
    :sound <id>                          attach a sound id to messages (0 clears)
    :clear                               clear the callout window and queue
    :raw <console line>                  send any console command, e.g. :raw state
    :help / :quit

The console runs one command per client per rendered frame, so a hidden or minimised
window answers slowly or not at all.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys

SPEAKERS = ("fox", "falco", "peppy", "slippy", "custom")

HELP = """\
plain text        show it in game as a comm callout from the current speaker
:who <name>       fox | falco | peppy | slippy | custom
:sound <id>       play a game sound id with each message (0 turns it off)
:clear            clear the callout window and queue in game
:raw <line>       send any console command: :raw state, :raw step 30, :raw = gd.player(1).x
:help             this list
:quit             leave this prompt (the game keeps running)"""


class Console:
    """One console-socket client (docs/scripting.md, 'The console')."""

    def __init__(self, host: str, port: int, timeout: float = 6.0):
        self.timeout = timeout
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buf = b""
        self.banner = self._banner()

    def _banner(self) -> str:
        try:
            while b"\n" not in self.buf:
                self.sock.settimeout(2.0)
                self.buf += self.sock.recv(4096)
            line, self.buf = self.buf.split(b"\n", 1)
            return line.decode("utf-8", "replace").rstrip("\r")
        except OSError:
            return ""

    def run(self, line: str):
        self.sock.sendall((line + "\n").encode("utf-8"))
        out = []
        while True:
            while b"\n" in self.buf:
                raw, self.buf = self.buf.split(b"\n", 1)
                text = raw.decode("utf-8", "replace").rstrip("\r")
                if text == ">>> ok":
                    return out, True
                if text == ">>> error":
                    return out, False
                out.append(text)
            self.sock.settimeout(self.timeout)
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                raise TimeoutError("no reply - is the game window visible and rendering?") from None
            if not chunk:
                raise ConnectionError("the game closed the console socket")
            self.buf += chunk


def command(console: Console, text: str, state: dict) -> None:
    """Handle one typed line (`:` commands or a plain message)."""
    text = text.strip()
    if not text:
        return
    if text.startswith(":"):
        name, _, rest = text[1:].partition(" ")
        name, rest = name.lower(), rest.strip()
        if name in ("quit", "q", "exit"):
            state["quit"] = True
            return
        if name == "help":
            print(HELP)
            return
        if name == "who":
            if rest in SPEAKERS:
                state["who"] = rest
                print("speaker:", rest)
            else:
                print("who is one of:", ", ".join(SPEAKERS))
            return
        if name == "sound":
            try:
                state["sound"] = int(rest or "0")
            except ValueError:
                print("sound takes an integer id (0 clears)")
                return
            print("sound:", state["sound"] if state["sound"] else "off")
            return
        if name == "clear":
            line = "= gd.comm_clear()"
        elif name == "raw" and rest:
            line = rest
        else:
            print("unknown:", text, "- try :help")
            return
    else:
        body = text.replace('"', "'")
        line = 'comm %s "%s"' % (state["who"], body)
        if state["sound"]:
            line += " %d" % state["sound"]

    if line != text:
        print("  >", line)
    out, ok = console.run(line)
    for o in out:
        print("  " + o)
    print("  ok" if ok else "  error")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=int(os.environ.get("MELEE_CONSOLE_PORT", "51700")))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--who", default="fox", choices=SPEAKERS)
    ap.add_argument("--sound", type=int, default=0)
    ap.add_argument("--send", metavar="TEXT", help="send one line and exit (:commands allowed)")
    args = ap.parse_args()

    try:
        console = Console(args.host, args.port)
    except OSError as e:
        print(f"could not connect to {args.host}:{args.port} ({e})")
        print(f"start the game with MELEE_CONSOLE_PORT={args.port} set, and keep its window visible")
        return 2

    state = {"who": args.who, "sound": args.sound, "quit": False}

    if args.send is not None:
        command(console, args.send, state)
        return 0 if not state["quit"] else 0

    print(f"connected to the GD Melee console at {args.host}:{args.port}"
          + (f" - {console.banner}" if console.banner else ""))
    print(f"speaker: {state['who']}   (plain text shows in game; :help for commands)")
    try:
        while not state["quit"]:
            try:
                line = input(f"{state['who']}> ")
            except EOFError:
                print()
                break
            try:
                command(console, line, state)
            except (TimeoutError, ConnectionError) as e:
                print("  !", e)
                break
    except KeyboardInterrupt:
        print()
    print("bye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
