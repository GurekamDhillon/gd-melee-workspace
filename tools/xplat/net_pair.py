#!/usr/bin/env python3
"""A real netplay session between the Windows build and the Linux build (WSL), on this machine.

    net_pair.py NAME [--host win|linux] [--mode direct|random] [--seconds 150]
                [--stocks 4] [--minutes 8] [--delay 2] [--turbo on|off|HEX] [--envoy on|off]
                [--char-host 2] [--char-guest 9] [--stage 31] [--seed 100]
                [--disc vanilla|ace|akaneia] [--net-sim PRESET] [--linux-dir outD]

Both clients run in real time (windows open; the Linux one through WSLg/X11), each driven by
MELEE_PAD_BOT (a reactive pad program, native, deterministic given the game state), and write the
game's own confirmed-frame checksum log (MELEE_RB_HASHLOG). `direct` connects host -> guest by IP;
`random` goes through a LOCAL matchmaking server (tools/netplay/server/gdmelee_server.py on this
machine, never the production one) the way Random Opponent does. When --seconds are up both games are
stopped by numeric PID and the two hash logs are compared frame by frame.

WSL2 reaches Windows at the vEthernet gateway and Windows reaches WSL at its eth0 address; both are
looked up here. Environment for the Windows side as pair.py (source env_win.sh first).
"""
import argparse, json, os, re, shutil, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('GW_ROOT_ENV', 'E:/Projects/Melee Workspace')
GIT_BASH = os.environ.get('GIT_BASH', 'C:/Program Files/Git/bin/bash.exe')
DISCS = {'vanilla': '/mnt/c/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso',
         'ace': '/mnt/c/iso/SSBM ACE Build v2.0.0.iso', 'akaneia': '/mnt/c/iso/Akaneia.iso'}


def q(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def wsl(cmd, **kw):
    env = dict(os.environ)
    env['MSYS_NO_PATHCONV'] = '1'
    return subprocess.run(['wsl', '-d', 'Debian', '--', 'bash', '-lc', cmd], env=env, capture_output=True, text=True, **kw)


def ps(cmd):
    r = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True)
    return r.stdout.strip()


def win_pids(fragment):
    out = ps("Get-CimInstance Win32_Process -Filter \"Name='melee-pc.exe'\" | Where-Object { $_.ExecutablePath -like '*%s*' } "
             "| ForEach-Object { $_.ProcessId }" % fragment)
    return [int(x) for x in out.split() if x.isdigit()]


def lin_pids(fragment):
    r = wsl("for p in $(pgrep -x melee); do c=$(readlink /proc/$p/cwd 2>/dev/null); case \"$c\" in *%s*) echo $p;; esac; done" % fragment)
    return [int(x) for x in r.stdout.split() if x.isdigit()]


def hashes(path):
    out = {}
    try:
        for line in open(path):
            p = line.strip().split(',')
            if len(p) == 2 and p[0].lstrip('-').isdigit():
                out[int(p[0])] = p[1]
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--host', default='win', choices=('win', 'linux'))
    ap.add_argument('--mode', default='direct', choices=('direct', 'random'))
    ap.add_argument('--seconds', type=int, default=150)
    ap.add_argument('--stocks', default='4'); ap.add_argument('--minutes', default='8'); ap.add_argument('--delay', default='2')
    ap.add_argument('--turbo', default=''); ap.add_argument('--envoy', default='')
    ap.add_argument('--char-host', default='2'); ap.add_argument('--char-guest', default='9')
    ap.add_argument('--stage', default='31'); ap.add_argument('--seed', type=int, default=100)
    ap.add_argument('--disc', default='vanilla'); ap.add_argument('--net-sim', default='')
    ap.add_argument('--linux-dir', default='outD')
    ap.add_argument('--port', type=int, default=0)
    ap.add_argument('--no-bot', action='store_true')
    ap.add_argument('--scene', default='', help='MELEE_SCENE for the DIRECT mode (the room code path ignores it)')
    a = ap.parse_args()

    out = os.path.join(ROOT, '_build', 'xplat', 'net_' + a.name)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    gw = ps("(Get-NetIPAddress -InterfaceAlias 'vEthernet (WSL*' -AddressFamily IPv4 | Select-Object -First 1).IPAddress")
    wsl_ip = wsl("ip -4 addr show eth0 | awk '/inet /{print $2}' | cut -d/ -f1").stdout.strip()
    print('windows gateway seen from WSL:', gw, ' WSL address:', wsl_ip)
    port = a.port or (51600 + 50 + (os.getpid() % 40))
    server = None
    if a.mode == 'random':
        server = subprocess.Popen([sys.executable, os.path.join(ROOT, 'tools/netplay/server/gdmelee_server.py'),
                                   '--port', str(port), '--bind', '0.0.0.0'],
                                  stdout=open(os.path.join(out, 'server.log'), 'w'), stderr=subprocess.STDOUT)
        time.sleep(1.5)
        print('local matchmaking server pid', server.pid, 'on udp', port)

    common = {'MELEE_NETPLAY_STOCKS': a.stocks, 'MELEE_NETPLAY_MINUTES': a.minutes, 'MELEE_NETPLAY_DELAY': a.delay,
              'MELEE_NETPLAY_STAGE': a.stage, 'MELEE_VOLUME': '0'}
    if a.turbo:
        common['MELEE_NETPLAY_TURBO'] = a.turbo
    if a.envoy:
        common['MELEE_NETPLAY_ENVOY'] = a.envoy
    if a.net_sim:
        common['MELEE_NET_SIM'] = a.net_sim
    if a.scene:
        common['MELEE_SCENE'] = a.scene
    if a.mode == 'random':
        side = {'win': dict(MELEE_NETPLAY='random', MELEE_NETPLAY_SERVER='%s:%d' % (gw, port)),
                'linux': dict(MELEE_NETPLAY='random', MELEE_NETPLAY_SERVER='%s:%d' % (gw, port))}
    else:
        hostwin = a.host == 'win'
        side = {'win': dict(MELEE_NETPLAY=('host:%d' % port) if hostwin else ('join:%s:%d' % (wsl_ip, port))),
                'linux': dict(MELEE_NETPLAY=('join:%s:%d' % (gw, port)) if hostwin else ('host:%d' % port))}
    chars = {'win': a.char_host if a.host == 'win' else a.char_guest, 'linux': a.char_host if a.host == 'linux' else a.char_guest}
    slots = {'win': 0 if a.host == 'win' else 1, 'linux': 0 if a.host == 'linux' else 1}
    for k in ('win', 'linux'):
        side[k]['MELEE_NETPLAY_CHAR'] = chars[k]
        if not a.no_bot:
            side[k]['MELEE_PAD_BOT'] = '%d,0,%d' % (slots[k], a.seed + slots[k])
    wname, lname = 'n_' + a.name, 'n_' + a.name

    def start_win():
        env = dict(os.environ)
        env.update(common)
        env.update(side['win'])
        env.update(MELEE_PAD_IGNORE_ADAPTER='1', MELEE_SKIP_INTRO='1', MELEE_PAD_BOT_EDGE='62', MELEE_WINDOW_W='960', MELEE_WINDOW_H='540', MELEE_WINDOW_X='20', MELEE_WINDOW_Y='20',
                   MELEE_MODS_DIR=os.path.join(ROOT, '_build', 'nomods'))
        iso = {'vanilla': 'GW_ISO_VANILLA', 'ace': 'GW_ISO_ACE', 'akaneia': 'GW_ISO_AKANEIA'}[a.disc]
        sandbox = os.path.join(os.environ['GW_BUILD_ROOT'], 'runs', wname)
        os.makedirs(sandbox, exist_ok=True)
        env['MELEE_RB_HASHLOG'] = os.path.join(sandbox, 'hashes.csv').replace('\\', '/')
        env['MELEE_RB_LOG'] = '0'
        script = ('set -a; . "%s/.env"; set +a; exec bash "%s/tools/port/run.sh" --realtime %s --iso "${%s}"'
                  % (ROOT, ROOT, wname, iso))
        with open(os.path.join(out, 'win.out'), 'w') as fo:
            return subprocess.Popen([GIT_BASH, '-c', script], env=env, stdout=fo, stderr=subprocess.STDOUT, cwd=os.environ['GW_MELEE'])

    def start_lin():
        env_pairs = dict(common)
        env_pairs.update(side['linux'])
        env_pairs.update(MELEE_PAD_BOT_EDGE='62', XP_DISC=a.disc)
        extra = ' '.join(q('%s=%s' % kv) for kv in env_pairs.items())
        inner = ('cd ~/lb2; export MELEE_VANILLA_ISO=%s MELEE_ACE_ISO=%s MELEE_AKANEIA_ISO=%s; '
                 './enterD.sh env bash /mnt/h/wsD/tools/xplat/run_linux_net.sh /mnt/h/%s/linux %s %d %s'
                 % (q(DISCS['vanilla']), q(DISCS['ace']), q(DISCS['akaneia']), a.linux_dir, lname, a.seconds + 60, extra))
        env = dict(os.environ)
        env['MSYS_NO_PATHCONV'] = '1'
        with open(os.path.join(out, 'linux.out'), 'w') as fo:
            return subprocess.Popen(['wsl', '-d', 'Debian', '--', 'bash', '-lc', inner], env=env, stdout=fo, stderr=subprocess.STDOUT)

    started = []
    order = ['win', 'linux'] if a.host == 'win' else ['linux', 'win']
    if a.mode == 'random':
        order = ['win', 'linux']
    t0 = time.time()
    procs = {}
    for k in order:
        procs[k] = (start_win if k == 'win' else start_lin)()
        print('started', k)
        time.sleep(4 if a.mode == 'direct' else 2)
    # wait for both games to exist and run for the requested time
    time.sleep(a.seconds)
    wp = win_pids('runs\\' + wname) or win_pids('runs/' + wname)
    lp = lin_pids('xpn-' + lname)
    print('game pids at the end: windows', wp, 'linux', lp)
    for pid in wp:
        ps('Stop-Process -Id %d -Force' % pid)
    for pid in lp:
        wsl('kill %d' % pid)
    time.sleep(3)
    for k, p in procs.items():
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            print('stray', k, 'launcher process', p.pid)
            p.kill()
    if server is not None:
        server.terminate()
        server.wait(timeout=10)
    # collect
    wsrc = os.path.join(os.environ['GW_BUILD_ROOT'], 'runs', wname)
    lsrc = '//wsl.localhost/Debian/home/gd/lb2/%s/xpn-%s' % (a.linux_dir, lname)
    for side_name, src in (('win', wsrc), ('linux', lsrc)):
        d = os.path.join(out, side_name)
        os.makedirs(d, exist_ok=True)
        for fn in ('melee-pc.log', 'hashes.csv'):
            try:
                shutil.copy2(os.path.join(src, fn), d)
            except OSError as e:
                print('missing', side_name, fn, e)
    hw, hl = hashes(os.path.join(out, 'win', 'hashes.csv')), hashes(os.path.join(out, 'linux', 'hashes.csv'))
    shared = sorted(hw.keys() & hl.keys())
    bad = [f for f in shared if hw[f] != hl[f]]
    print('confirmed frames: windows %d, linux %d, shared %d, mismatching %d%s' % (
        len(hw), len(hl), len(shared), len(bad), (' first %d' % bad[0]) if bad else ''))
    for side_name in ('win', 'linux'):
        log = open(os.path.join(out, side_name, 'melee-pc.log'), errors='replace').read() if os.path.exists(os.path.join(out, side_name, 'melee-pc.log')) else ''
        for pat in (r'netplay: build id[^\n]*', r'netplay: DESYNC[^\n]*', r'netplay:[^\n]*[Rr]efus[^\n]*', r'Refused[^\n]*',
                    r'rb: [^\n]*(summary|rollbacks|session)[^\n]*', r'netplay: match[^\n]*', r'netplay: connected[^\n]*',
                    r'netplay: relay[^\n]*', r'netplay: direct[^\n]*', r'PANIC[^\n]*', r'FATAL[^\n]*'):
            for m in list(re.finditer(pat, log))[:3]:
                print('  [%s] %s' % (side_name, m.group(0)[:230]))
    res = dict(shared=len(shared), mismatching=len(bad), win_frames=len(hw), linux_frames=len(hl))
    json.dump(res, open(os.path.join(out, 'result.json'), 'w'))
    return 0 if len(shared) >= 600 and not bad else 1


if __name__ == '__main__':
    sys.exit(main())
