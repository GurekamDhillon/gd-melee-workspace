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
    any   -> RAND <mods-hash> <lan-addr> random opponent: queue, repeated every ~2 s while waiting
                                        server -> QUEUED <players-waiting-with-this-hash>
                                        server -> MATCH HOST|GUEST <code> <other-public> <other-lan>
    any   -> RANDCANCEL                 leave the queue      server -> CANCELED
    either -> RELAY                     "no direct path": the server relays for this pair
    either -> BYE                       leave
  relay, binary:  b"GDMD" + payload     forwarded verbatim to the partner, as b"GDMD" + payload

RANDOM MATCHMAKING pairs two queued players whose <mods-hash> (the hash of the global game data -
codes, physics, global sim tables; fighters and stages are intersected per match) is identical. The
one who waited longer becomes HOST. The pair gets an ordinary persistent room with a code, so
everything after MATCH is the REG/JOIN flow: the host re-registers from the same address and keeps
the code, the guest rejoins with JOIN <code>. A queue entry is dropped after QUEUE_IDLE seconds
without a RAND and after QUEUE_MAX seconds in all (the client is told TIMEOUT).

A room lives while its host keeps it alive (keepalives every few seconds) and ends after
ROOM_IDLE seconds of silence. Rooms are PERSISTENT: the same code survives match after match -
the host re-registers from the same address and keeps its code, and a returning guest (new port)
takes the seat again. Relaying is per pair and costs about 60 small packets a second
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
PAIR_IDLE = 900.0      # seconds without traffic before a PAIRED room is dropped: long enough for a
                       # results screen, where the game closes its match socket (persistent rooms)
QUEUE_IDLE = 10.0      # random queue: seconds without a RAND before an entry is dropped
QUEUE_MAX = 300.0      # random queue: longest wait before the client is told TIMEOUT
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


class Waiter:
    def __init__(self, addr, mods, lan):
        self.addr = addr
        self.mods = mods
        self.lan = lan
        self.since = time.monotonic()
        self.seen = self.since


class Server(asyncio.DatagramProtocol):
    def __init__(self):
        self.rooms = {}      # code -> Room
        self.by_addr = {}    # addr -> Room (host or guest)
        self.queue = {}      # addr -> Waiter (random matchmaking)
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
                # the host again - a repeat, or a rematch: same code, the room waits for its guest
                room.host_lan = lan or room.host_lan
                if room.guest is not None and self.by_addr.get(room.guest) is room:
                    del self.by_addr[room.guest]
                room.guest = None
                room.relay = False
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
                # PERSISTENT ROOMS: a guest coming back for a rematch arrives from a new port;
                # the newest guest takes the seat (the game's own handshake admits one peer)
                if self.by_addr.get(target.guest) is target:
                    del self.by_addr[target.guest]
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
        elif cmd == "RAND":
            mods = words[1] if len(words) > 1 else "-"
            lan = words[2] if len(words) > 2 else ""
            me = self.queue.get(addr)
            if me is None:
                if room is not None:
                    self.drop(room, "%s went to random matchmaking" % fmt(addr))
                me = Waiter(addr, mods, lan)
                self.queue[addr] = me
                log.info("random: %s queued (mods %s, %d waiting)", fmt(addr), mods, len(self.queue))
            else:
                me.seen = time.monotonic()
                me.mods, me.lan = mods, lan or me.lan
            other = None
            for w in self.queue.values():
                if w is not me and w.mods == me.mods and (other is None or w.since < other.since):
                    other = w
            if other is None:
                waiting = sum(1 for w in self.queue.values() if w.mods == me.mods)
                self.send(addr, "QUEUED %d" % waiting)
                return
            host, guest = (other, me) if other.since <= me.since else (me, other)
            del self.queue[host.addr]
            del self.queue[guest.addr]
            if len(self.rooms) >= MAX_ROOMS:
                self.send(host.addr, "ERR server full")
                self.send(guest.addr, "ERR server full")
                return
            pair = Room(self.new_code(), host.addr, host.lan)
            pair.guest = guest.addr
            pair.guest_lan = guest.lan
            self.rooms[pair.code] = pair
            self.by_addr[host.addr] = pair
            self.by_addr[guest.addr] = pair
            self.send(host.addr, "MATCH HOST %s %s %s" % (pair.code, fmt(guest.addr), guest.lan or "-"))
            self.send(guest.addr, "MATCH GUEST %s %s %s" % (pair.code, fmt(host.addr), host.lan or "-"))
            log.info("random: room %s - host %s, guest %s (mods %s)", pair.code, fmt(host.addr),
                     fmt(guest.addr), host.mods)
        elif cmd == "RANDCANCEL":
            if self.queue.pop(addr, None) is not None:
                log.info("random: %s left the queue", fmt(addr))
            self.send(addr, "CANCELED")
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
            for w in list(self.queue.values()):
                if now - w.since > QUEUE_MAX:
                    self.send(w.addr, "TIMEOUT")
                    del self.queue[w.addr]
                    log.info("random: %s timed out after %d s", fmt(w.addr), QUEUE_MAX)
                elif now - w.seen > QUEUE_IDLE:
                    del self.queue[w.addr]
                    log.info("random: %s dropped (silent)", fmt(w.addr))
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
