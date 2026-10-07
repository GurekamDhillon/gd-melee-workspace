# GD's Melee matchmaking server

A small UDP server for your VPS. It gives each host a 4-letter **room code** (like `KQ7X`), tells
the guest who types it where the host is, and **relays** the match when the two can't reach each
other directly. One Python file, standard library only.

## Run it

```sh
python3 gdmelee_server.py              # UDP 51600 on all interfaces
python3 gdmelee_server.py --port 51600 --bind 0.0.0.0
```

Open the port in the VPS firewall (and any cloud security group):

```sh
sudo ufw allow 51600/udp               # Ubuntu/Debian with ufw
```

### As a service (systemd)

```sh
sudo mkdir -p /opt/gdmelee && sudo cp gdmelee_server.py /opt/gdmelee/
sudo cp gdmelee.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now gdmelee
journalctl -u gdmelee -f               # watch rooms open, join and relay
```

## Point the game at it

The online package carries the server address in `netplay_server.txt` next to `melee-pc.exe`:

```
your.vps.address:51600
```

Build the package with it filled in: `powershell -File tools\netplay\make_package.ps1 -Server your.vps.address:51600` (a wrapper over `tools\release\build_release.ps1`; players can change the server in the game's SETTINGS > ONLINE > Server).

Random matchmaking retains a completed assignment so a repeated RAND resends the same MATCH
after packet loss. Pending entries are capped at 5000; matching an existing waiter is still allowed
at capacity, while a new unmatched waiter receives `ERR server queue full`. REG/JOIN switches clear
the previous queue/guest membership without leaving a relay route into an unrelated room.
(`MELEE_NETPLAY_SERVER` overrides the file.) Without a server, the game falls back to swapping
addresses by hand.

## What it costs

A room is two addresses and a timestamp. While two players connect directly the server only sees
keepalives every few seconds. Relaying a match is ~60 packets/s each way of under 200 bytes -
about 25 KB/s per match. A $5 VPS handles hundreds of relayed matches.

## Security notes

- The server only forwards between the two addresses of a room; it never forwards to an address a
  client names, so it can't be used to send traffic at third parties.
- Codes are 4 characters from a 32-letter alphabet (about a million rooms) and expire after two
  minutes without the host. A room accepts one guest.
- Nothing is stored on disk.

## Protocol 3 compatibility (2026-09-27)

The game uses protocol 3 (40 MiB MEM1 and the expanded fighter heap). GDMR
REG/JOIN/RAND still carry no version, including in the v3 game. Do not require a
version argument there. The server checks the little-endian version in relayed
GN HELLO/ACCEPT packets, sends both peers `ERR protocol version mismatch ...;
update GD's Melee on both PCs`, and closes an incompatible room. Bounded rejection records repeat that error for
60 seconds on retries, including when the first UDP reply was lost; after updating,
wait for expiry or use a new socket address. Other relay
payloads stay opaque. Direct connections use the game's peer version check.
The server cannot reject old clients at registration or split the random queue
by version until the game advertises its version there; two old direct peers
are not blocked by this server.

Production's configured address is netplay.gsd.sh:51600: matchmaking uses UDP;
opt-in HTTP crash uploads use TCP in the separate tools/release/crash_upload_server.py
process. Crash uploads remain compatible with old launchers. No deployment is
part of this change.

The crash-upload service's optional `--jev` setting adds advisory TypeSafe crash
triage to metadata, off by default. Deploy `tools/jev/` alongside the service and
set only `TYPESAFE_API_KEY` in its environment. See [Jev tools](../../jev/README.md)
for privacy limits, offline verification, and manual classification of stored reports.

Local verification from the workspace root (Python 3.8+):

```powershell
python -m unittest discover -s tools/netplay/server -v
python tools/netplay/server/gdmelee_server.py --bind 127.0.0.1 --port 51600
# Second terminal; synthetic reports only, never production reports:
python tools/release/crash_upload_server.py --bind 127.0.0.1 --port 51600 --dir _build/p3-test-crashes
```

The unittest socket test uses an ephemeral loopback port for both UDP and TCP
and a temporary directory for synthetic crash reports. No public host is contacted.
