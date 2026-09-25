"""Run two visible native clients through Slippi and verify finalized artifacts.

Windows only. Builds must already exist; all launches go through run.sh. Optional
account providers return profile dictionaries in memory, sent to each game's
stdin. Neither profiles nor command lines containing play keys are written.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

import psutil

from alter_fixture import FixtureMutationError, make_altered_p1_fixture
from compare_finalized import _complete_replay, verify_pair
from udp_relay import UdpRelay

ROOT = Path(__file__).resolve().parents[2]
MIN_FREE_RAM = 8 * 1024 ** 3


class RunError(RuntimeError):
    """An error with a fixed, credential-free message safe for the report."""


def account_tag(profile: dict, salt: str) -> str:
    fingerprint = 14695981039346656037
    for byte in profile['uid'].encode('utf-8'):
        fingerprint = ((fingerprint ^ byte) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return hashlib.sha256(b'GD Slippi account v1\0' + bytes.fromhex(salt) +
                          fingerprint.to_bytes(8, 'big')).hexdigest()


def profiles_from_args(args) -> list[dict]:
    if args.mode != 'direct':
        return []
    if args.accounts_helper:
        spec = importlib.util.spec_from_file_location('private_slippi_accounts', args.accounts_helper)
        if spec is None or spec.loader is None:
            raise ValueError('cannot load private account provider')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        profiles = module.profiles()
    else:
        if not args.user_a or not args.user_b:
            raise ValueError('Direct requires two profiles or an in-memory account provider')
        profiles = [json.loads(path.read_text(encoding='utf-8')) for path in (args.user_a, args.user_b)]
    required = ('uid', 'playKey', 'connectCode', 'displayName', 'latestVersion')
    if not isinstance(profiles, list) or len(profiles) != 2 or any(
        not isinstance(profile, dict) or any(not isinstance(profile.get(key), str) or
        not profile[key] for key in required) for profile in profiles
    ):
        raise ValueError('account provider must return two complete Launcher profiles')
    if profiles[0]['uid'] == profiles[1]['uid']:
        raise ValueError('Direct requires two distinct accounts')
    # Send the exact supported schema; never forward Firebase refresh/access tokens.
    return [{key: profile[key] for key in required} for profile in profiles]


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(os.path.realpath(left)) == os.path.normcase(os.path.realpath(right))


class OwnedRun:
    """Track only this launcher's descendants and verify path/creation time to stop."""
    def __init__(self, process: subprocess.Popen, exe: Path, directory: Path, log,
                 launched_after: float = 0):
        self.process = process
        self.exe = exe
        self.directory = directory
        self.log = log
        self.launched_after = launched_after
        launcher = psutil.Process(process.pid)
        self.launcher = (launcher.pid, launcher.create_time(), launcher.exe())
        self.games: dict[int, tuple[float, str]] = {}

    def discover(self):
        try:
            parent = psutil.Process(self.launcher[0])
            if parent.create_time() != self.launcher[1]:
                return
            for child in parent.children(recursive=True):
                try:
                    path = child.exe()
                    if _same_path(path, self.exe):
                        self.games[child.pid] = (child.create_time(), path)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    @staticmethod
    def stop_identity(pid, created, expected_path):
        try:
            process = psutil.Process(pid)
            if process.create_time() != created or not _same_path(process.exe(), expected_path):
                return
            process.terminate()
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                # Recheck identity before a forced stop; a recycled PID is never killed.
                if process.create_time() == created and _same_path(process.exe(), expected_path):
                    process.kill()
                    process.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def close(self):
        try:
            self.discover()
            for pid, (created, path) in self.games.items():
                self.stop_identity(pid, created, path)
            self.stop_identity(*self.launcher)
            # run.sh can exit before discovery, orphaning its copied game executable.
            stop_copied_games(self.exe, self.launched_after)
        finally:
            if self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()
            self.log.close()


def stop_copied_games(exe: Path, launched_after: float) -> None:
    """Stop only game processes using this run's unique copied executable."""
    for process in psutil.process_iter(['pid', 'create_time', 'exe']):
        try:
            info = process.info
            path, created = info.get('exe'), info.get('create_time')
            if path and type(created) in (int, float) and created >= launched_after and _same_path(path, exe):
                OwnedRun.stop_identity(info['pid'], created, path)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def cleanup_failed_launch(process: subprocess.Popen, exe: Path, launched_after: float) -> None:
    """Reap a process even if launcher identity capture failed after Popen."""
    try:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    except (OSError, psutil.NoSuchProcess):
        pass
    finally:
        stop_copied_games(exe, launched_after)


def verify_owned_game(evidence: dict, owned: OwnedRun) -> int:
    """Bind one evidence file to the game observed beneath its own launcher."""
    pid = evidence.get('process_id') if isinstance(evidence, dict) else None
    if type(pid) is not int or pid not in owned.games:
        raise RunError('evidence process is not this launcher game')
    return pid


def free_ports() -> tuple[int, int]:
    sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(2)]
    try:
        for item in sockets:
            item.bind(('127.0.0.1', 0))
        return tuple(item.getsockname()[1] for item in sockets)
    finally:
        for item in sockets:
            item.close()


def launch(args, role, ports, run_id, salt, profiles, proxy_ports=None,
           fixture_override: Path | None = None) -> OwnedRun:
    free = psutil.virtual_memory().available
    if free < MIN_FREE_RAM:
        raise RunError('fewer than 8 GiB of free physical memory before launch')
    name = f'slippi-{run_id}-{role}'
    directory = args.build_root / 'runs' / name
    directory.mkdir(parents=True, exist_ok=False)
    log = (directory / 'launch.log').open('wb')
    # Experimental runs cannot inherit another input source, resync, Lua script,
    # fake network or scene from the shell that launched the diagnostic.
    env = {key: value for key, value in os.environ.items() if not key.startswith('MELEE_')}
    env.update(GW_ROOT=ROOT.as_posix(), GW_MELEE=args.game_root.as_posix(),
               GW_BUILD_ROOT=args.build_root.as_posix(), GW_RUNS_KEEP='1000000',
               MELEE_SLIPPI_RUN_NAME=name, MELEE_ISO=args.iso.as_posix(),
               MELEE_SLIPPI_MODE=args.mode, MELEE_SLIPPI_REPLAY_ROLE=str(role),
               MELEE_SLIPPI_LOCAL_PORT=str(ports[role-1]),
               MELEE_SLIPPI_REMOTE_PORT=str(proxy_ports[role-1] if proxy_ports else ports[2-role]),
               MELEE_SLIPPI_MATCH_ID=run_id,
               MELEE_SLIPPI_DELAY=str(args.delay), MELEE_SLIPPI_RUN_SALT=salt,
               MELEE_SLP=(fixture_override or args.fixture).as_posix(),
               MELEE_INPUT='none', MELEE_VOLUME='3',
               MELEE_MODS_DIR=args.empty_mods.as_posix(),
               MELEE_STATE_TRACE=(directory/'state.csv').as_posix(),
               MELEE_RB_HASHLOG=(directory/'hashes.csv').as_posix(),
               MELEE_SLP_RECORD=(directory/'match.slp').as_posix(),
               MELEE_SLIPPI_EVIDENCE=(directory/'evidence.json').as_posix(),
               MELEE_RUN_LABEL=f'Slippi {args.mode} / client {role}')
    if profiles:
        env['MELEE_SLIPPI_USER_JSON'] = '-'
        env['MELEE_SLIPPI_CODE'] = profiles[2-role]['connectCode']
    command = ['C:/Program Files/Git/bin/bash.exe', '-c',
               'export PATH=/usr/bin:/bin:$PATH; exec bash "$GW_ROOT/tools/port/run.sh" '
               '"$MELEE_SLIPPI_RUN_NAME" --iso "$MELEE_ISO"']
    process = None
    owned = None
    launched_after = time.time() - 1  # tolerate OS process timestamp granularity
    try:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        owned = OwnedRun(process, directory/'melee-pc.exe', directory, log, launched_after)
        if profiles:
            payload = json.dumps(profiles[role-1], ensure_ascii=False).encode('utf-8')
            process.stdin.write(payload)
            process.stdin.flush()
        process.stdin.close()
        return owned
    except Exception:
        if process is not None and process.stdin and not process.stdin.closed:
            process.stdin.close()
        if owned is not None:
            owned.close()
        elif process is not None:
            cleanup_failed_launch(process, directory/'melee-pc.exe', launched_after)
        log.close()
        raise


def evaluate_negative_control(mutation: dict, normal: dict, consensus: dict) -> dict:
    """Require a changed result versus source and exact agreement between clients."""
    errors = []
    divergence = normal.get('first_divergence')
    frame = divergence.get('frame') if isinstance(divergence, dict) else None
    if normal.get('ok') is not False:
        errors.append('original fixture unexpectedly matched the altered run')
    if type(frame) is not int or frame < mutation['frame']:
        errors.append('no first gameplay divergence at or after the altered input')
    if normal.get('checksums_equal') is not True:
        errors.append('client checksums disagree in negative control')
    if consensus.get('ok') is not True:
        errors.append('clients disagree on the altered match result')
    return dict(ok=not errors, kind='negative_control', mode='loopback',
                errors=errors, mutation=mutation,
                normal_verification=normal, consensus_verification=consensus)


def run(args) -> dict:
    if os.name != 'nt':
        raise RunError('this runner requires Windows and visible native game windows')
    for name in ('fixture', 'iso', 'game_root', 'build_root'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    if not (args.build_root/'melee-pc.exe').is_file():
        raise RunError('build the selected lane first')
    if not 0 <= args.latency_ms <= 2000 or not 0 <= args.loss_percent <= 100:
        raise RunError('invalid UDP impairment setting')
    if args.mode != 'loopback' and (args.latency_ms or args.loss_percent):
        raise RunError('UDP impairment is only available in loopback mode')
    if args.negative_control and args.mode != 'loopback':
        raise RunError('input negative control is only available in loopback mode')
    replay = _complete_replay(args.fixture)
    profiles = profiles_from_args(args)
    ports = free_ports()
    run_id = time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3)
    salt = secrets.token_hex(16)
    report_dir = args.build_root/'runs'/f'slippi-{run_id}-result'
    report_dir.mkdir(parents=True, exist_ok=False)
    args.empty_mods = report_dir/'empty-mods'
    args.empty_mods.mkdir()
    runs = []
    relay = None
    mutation = None
    altered_fixture = None
    result = dict(ok=False, mode=args.mode, errors=[])
    try:
        if args.negative_control:
            altered_fixture = report_dir/'negative-control-input.slp'
            try:
                mutation = make_altered_p1_fixture(args.fixture, altered_fixture)
            except FixtureMutationError as exc:
                raise RunError(str(exc)) from None
        if args.latency_ms or args.loss_percent:
            relay = UdpRelay(ports, latency_ms=args.latency_ms,
                             loss_percent=args.loss_percent, seed=args.network_seed)
            relay.start()
        for role in (1, 2):
            runs.append(launch(args, role, ports, run_id, salt, profiles,
                               relay.ports if relay else None,
                               altered_fixture if role == 1 else None))
        deadline = time.monotonic() + (args.timeout or max(180, (replay.last_frame+124)/60*3+120))
        next_update = time.monotonic()
        while any(item.process.poll() is None for item in runs):
            for item in runs:
                item.discover()
            if time.monotonic() >= deadline:
                raise RunError('paired match exceeded its deadline')
            if any(item.process.poll() not in (None, 0) for item in runs):
                raise RunError('a native client exited with failure; inspect its private run log')
            if time.monotonic() >= next_update:
                print(json.dumps(dict(status='running', mode=args.mode,
                                      observed_game_processes=sum(len(item.games) for item in runs))), flush=True)
                next_update = time.monotonic()+10
            time.sleep(0.2)
        if any(item.process.returncode != 0 for item in runs):
            raise RunError('native client failed')
        clients = []
        expected_tags = {account_tag(profile, salt) for profile in profiles}
        game_pids = []
        for item in runs:
            item.discover()
            evidence = json.loads((item.directory/'evidence.json').read_text())
            game_pids.append(verify_owned_game(evidence, item))
            if profiles and (evidence.get('run_salt') != salt or
                             evidence.get('account_tag') not in expected_tags):
                raise RunError('matchmaking identity does not match the requested account pair')
            clients.append(dict(evidence=evidence, trace=item.directory/'state.csv',
                                recording=item.directory/'match.slp', hashes=item.directory/'hashes.csv'))
        clients.sort(key=lambda client: client['evidence'].get('role', 0))
        if len(set(game_pids)) != 2:
            raise RunError('both evidence files name the same game process')
        if args.negative_control:
            normal = verify_pair(args.fixture, *clients, require_mode='loopback',
                                 require_rollback=args.require_rollback)
            consensus = verify_pair(clients[0]['recording'], *clients,
                                    require_mode='loopback',
                                    require_rollback=args.require_rollback)
            result = evaluate_negative_control(mutation, normal, consensus)
        else:
            result = verify_pair(args.fixture, *clients, require_mode=args.mode,
                                 require_rollback=args.require_rollback)
        result['run_directories'] = [str(item.directory) for item in runs]
        result['game_process_ids'] = [sorted(item.games) for item in runs]
        if not all(item.games for item in runs):
            result['ok'] = False
            result['errors'].append('could not identify both launched game processes')
    except RunError as exc:
        result = dict(ok=False, mode=args.mode, errors=[str(exc)],
                      run_directories=[str(item.directory) for item in runs])
    except Exception as exc:
        # Do not print exception bodies from credential providers or network code.
        result = dict(ok=False, mode=args.mode, errors=[type(exc).__name__],
                      run_directories=[str(item.directory) for item in runs])
    finally:
        for item in runs:
            item.close()
        if relay:
            relay.close()
            result['relay'] = relay.stats
    if args.negative_control:
        result.setdefault('kind', 'negative_control')
        if mutation is not None:
            result.setdefault('mutation', mutation)
    (report_dir/'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--game-root', type=Path, default=ROOT/'worktrees/delta_slippi')
    parser.add_argument('--build-root', type=Path, default=ROOT/'_build/agents/delta_slippi')
    parser.add_argument('--mode', choices=('loopback','direct'), default='loopback')
    parser.add_argument('--user-a', type=Path)
    parser.add_argument('--user-b', type=Path)
    parser.add_argument('--accounts-helper', type=Path, help='private local Python provider exposing profiles()')
    parser.add_argument('--delay', type=int, choices=range(1,8), default=2)
    parser.add_argument('--timeout', type=float)
    parser.add_argument('--require-rollback', action='store_true')
    parser.add_argument('--negative-control', action='store_true',
                        help='alter one P1 A input in client 1 only; require divergence and client consensus')
    parser.add_argument('--latency-ms', type=int, default=0, help='one-way loopback UDP delay')
    parser.add_argument('--loss-percent', type=float, default=0, help='seeded loopback UDP loss')
    parser.add_argument('--network-seed', type=int, default=12345)
    args = parser.parse_args()
    try:
        result = run(args)
    except RunError as exc:
        result = dict(ok=False, errors=[str(exc)])
    except Exception as exc:
        result = dict(ok=False, errors=[type(exc).__name__])
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
