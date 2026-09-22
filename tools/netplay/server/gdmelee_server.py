#!/usr/bin/env python3
"""gdmelee_server.py - the matchmaking server for GD's Melee online play.

One UDP port. It gives a host a short ROOM CODE, introduces a guest who types that code to the
host (each learns the other's public and local address, so they can connect directly), and RELAYS
the match's packets between them when no direct path opens - symmetric NATs, carrier-grade NAT,
routers that do not loop connections back. Python 3.8+, standard library only.

    python3 gdmelee_server.py [--port 51600] [--bind 0.0.0.0]

Protocol (all packets start with a 4-byte magic):
  control, text:  b"GDMR" + utf-8 words
    host  -> REG <lan-addr>             server -> CODE <code> <your-public-addr>
    guest -> JOIN <code> <lan-addr>     server -> PEER <other-public> <other-lan>   (to BOTH)
                                        server -> ERR <reason>
    either -> KA                        keepalive (holds the router mapping and the room)
    either -> RELAY                     "no direct path": the server relays for this pair
    either -> BYE                       leave
  relay, binary:  b"GDMD" + payload     forwarded verbatim to the partner, as b"GDMD" + payload

A room lives while its host keeps it alive (keepalives every few seconds) and ends after
ROOM_IDLE seconds of silence. Relaying is per pair and costs about 60 small packets a second
each way during a match.
"""
import argparse
import asyncio
import logging
import secrets
import time

MAGIC_CTL = b"GDMR"
MAGIC_DATA = b"GDMD"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0, 1: easy to read out loud
CODE_LEN = 4
ROOM_IDLE = 120.0      # seconds without a packet from the host before a room is dropped
PAIR_IDLE = 60.0       # seconds without traffic before a relay pair is dropped
MAX_ROOMS = 5000

log = logging.getLogger("gdmelee")


def fmt(addr):
    return "%s:%d" % addr


class Room:
    def __init__(self, code, host, host_lan):
        self.code = code
        self.host = host
        self.host_lan = host_lan
        self.guest = None
        self.guest_lan = ""
        self.relay = False
        self.seen = time.monotonic()


class Server(asyncio.DatagramProtocol):
    def __init__(self):
        self.rooms = {}      # code -> Room
        self.by_addr = {}    # addr -> Room (host or guest)
        self.transport = None
        self.relayed = 0

    def connection_made(self, transport):
        self.transport = transport

    def send(self, addr, text):
        self.transport.sendto(MAGIC_CTL + text.encode(), addr)

    def new_code(self):
        for _ in range(100):
            code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
            if code not in self.rooms:
                return code
        raise RuntimeError("no free room code")

    def drop(self, room, why):
        log.info("room %s closed (%s)", room.code, why)
        self.rooms.pop(room.code, None)
        for a in (room.host, room.guest):
            if a is not None and self.by_addr.get(a) is room:
                del self.by_addr[a]

    def datagram_received(self, data, addr):
        if data[:4] == MAGIC_DATA:
            room = self.by_addr.get(addr)
            if room is None or room.guest is None:
                return
            room.seen = time.monotonic()
            room.relay = True
            other = room.guest if addr == room.host else room.host
            self.transport.sendto(data, other)
            self.relayed += 1
            return
        if data[:4] != MAGIC_CTL:
            return
        words = data[4:].decode("utf-8", "replace").split()
        if not words:
            return
        cmd = words[0].upper()
        room = self.by_addr.get(addr)
        if room is not None:
            room.seen = time.monotonic()

        if cmd == "REG":
            lan = words[1] if len(words) > 1 else ""
            if room is not None and room.host == addr:
                room.host_lan = lan or room.host_lan  # a repeat: same code
            else:
                if room is not None:
                    self.drop(room, "host re-registered")
                if len(self.rooms) >= MAX_ROOMS:
                    self.send(addr, "ERR server full")
                    return
                room = Room(self.new_code(), addr, lan)
                self.rooms[room.code] = room
                self.by_addr[addr] = room
                log.info("room %s opened by %s (lan %s)", room.code, fmt(addr), lan)
            self.send(addr, "CODE %s %s" % (room.code, fmt(addr)))
        elif cmd == "JOIN":
            if len(words) < 2:
                self.send(addr, "ERR no code")
                return
            code = words[1].upper().replace("-", "")
            lan = words[2] if len(words) > 2 else ""
            target = self.rooms.get(code)
            if target is None:
                self.send(addr, "ERR no room with that code")
                return
            if target.guest is not None and target.guest != addr:
                self.send(addr, "ERR that room is already playing")
                return
            if target.host == addr:
                self.send(addr, "ERR that is your own room")
                return
            target.guest = addr
            target.guest_lan = lan
            target.seen = time.monotonic()
            self.by_addr[addr] = target
            self.send(addr, "PEER %s %s" % (fmt(target.host), target.host_lan or "-"))
            self.send(target.host, "PEER %s %s" % (fmt(addr), lan or "-"))
            log.info("room %s: %s joined %s", code, fmt(addr), fmt(target.host))
        elif cmd == "KA":
            if room is not None:
                self.send(addr, "KA")
        elif cmd == "RELAY":
            if room is not None and room.guest is not None:
                room.relay = True
                other = room.guest if addr == room.host else room.host
                self.send(other, "RELAY")
                log.info("room %s: relaying", room.code)
        elif cmd == "BYE":
            if room is not None:
                other = room.guest if addr == room.host else room.host
                if other is not None:
                    self.send(other, "BYE")
                self.drop(room, "bye from %s" % fmt(addr))

    async def reaper(self):
        while True:
            await asyncio.sleep(10)
            now = time.monotonic()
            for room in list(self.rooms.values()):
                idle = now - room.seen
                if idle > (PAIR_IDLE if room.guest else ROOM_IDLE):
                    self.drop(room, "idle")
            if self.relayed:
                log.info("%d rooms, %d packets relayed in the last 10 s", len(self.rooms), self.relayed)
                self.relayed = 0


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=51600)
    ap.add_argument("--bind", default="0.0.0.0")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    loop = asyncio.get_running_loop()
    server = Server()
    await loop.create_datagram_endpoint(lambda: server, local_addr=(args.bind, args.port))
    log.info("GD's Melee server on udp %s:%d", args.bind, args.port)
    await server.reaper()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
