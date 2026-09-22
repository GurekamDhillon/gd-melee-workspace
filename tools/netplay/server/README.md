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

Build the package with it filled in: `powershell -File tools\netplay\make_package.ps1 -Server your.vps.address:51600` (a wrapper over `tools\release\build_release.ps1`; players can also change the server in the launcher's Online tab).
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
