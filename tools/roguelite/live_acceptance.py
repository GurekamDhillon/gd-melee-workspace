#!/usr/bin/env python3
"""Drive an already running 60 Hz native game; log fixtures separately from combat.

--route --branch a|b traverses either actual route. --custom-enemy adds a ReDead
check using charge earned with real fighter hits and retained through rest.
Built-in actions never inject charge/damage/Core state, remove enemies or dispatch
fake defeats. Positions, stand CPU and fighter ringouts are labelled fixtures.
Default is read-only. This program never starts or accelerates a game.
"""
import argparse
from collections import deque
import json
import math
from pathlib import Path
import re
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(game_source.SCRIPTS))
from console import run
import game_source


def rows(output, prefix):
    output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    result = []
    for match in re.finditer(r'\b' + re.escape(prefix) + r'\s+([^\n]+)', output):
        row = {}
        for key, raw in re.findall(r'(\w+)=([^\s]+)', match[1]):
            if raw in ('true', 'false', 'nil'):
                value = {'true': True, 'false': False, 'nil': None}[raw]
            else:
                try:
                    value = float(raw)
                    if not math.isfinite(value):
                        value = raw
                except ValueError:
                    value = raw
            row[key] = value
        if row:
            result.append(row)
    return result


def scalar(output):
    for line in reversed(output.splitlines()):
        value = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
        if value in ('true', 'false', 'nil'):
            return {'true': True, 'false': False, 'nil': None}[value]
        if re.fullmatch(r'-?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?', value, re.I):
            n = float(value)
            if math.isfinite(n):
                return n
    raise AssertionError('Missing scalar console result: ' + output)


def menu_path(output, target):
    headers, controls = rows(output, 'rogue_menu'), rows(output, 'rogue_control')
    assert headers and controls, 'Expected an open native menu'
    header = headers[-1]
    ids = [c['id'] for c in controls]
    assert target in ids, 'Missing menu control: ' + target
    assert controls[ids.index(target)]['enabled'], 'Disabled menu control: ' + target
    assert header['focus'] in ids, 'Unknown native focus'
    queue, seen = deque([(ids.index(header['focus']), [])]), set()
    while queue:
        at, path = queue.popleft()
        if at in seen:
            continue
        seen.add(at)
        if ids[at] == target:
            return path
        c = controls[at]
        x, y = c['x']+c['w']/2, c['y']+c['h']/2
        for direction, dx, dy in [('LEFT',-1,0), ('RIGHT',1,0), ('UP',0,-1), ('DOWN',0,1)]:
            candidates = []
            for i, other in enumerate(controls):
                rx, ry = other['x']+other['w']/2-x, other['y']+other['h']/2-y
                along, cross = (rx*dx,abs(ry)) if dx else (ry*dy,abs(rx))
                if i != at and along > 5:
                    candidates.append((along+cross*3,i))
            nxt = min(candidates)[1] if candidates else (
                len(controls)-1 if dy < 0 and header.get('wrap', True)
                else 0 if dy > 0 and header.get('wrap', True) else at)
            queue.append((nxt,path+[direction]))
    raise AssertionError('Unreachable native menu control: ' + target)


class Driver:
    """Injectable console/clock boundary: tests need no sockets/native process."""
    def __init__(self, command, *, sleep=time.sleep, clock=time.monotonic, note=None):
        self.cmd, self.sleep, self.clock = command, sleep, clock
        self.note = note or (lambda event, detail: print(event, detail, flush=True))
        self.pad_owned = self.cpu_fixture = self.earned_charge = False

    def state(self):
        data = rows(self.cmd('rogue_state'), 'rogue_state')
        assert data, 'Missing rogue_state diagnostics'
        assert data[-1].get('menu') != 'error', 'Native transition entered error UI'
        return data[-1]

    def value(self, expression):
        return scalar(self.cmd('= ' + expression))

    def press(self, button, seconds=.1):
        self.pad_owned = True
        self.cmd('input 1 none 1', 'test_controller');self.sleep(.08)
        self.cmd(f'input 1 {button} {max(2,math.ceil(seconds*60)+2)}', 'test_controller')
        self.sleep(seconds)
        self.cmd('input 1 none 1', 'test_controller');self.sleep(.08)

    def face(self, direction):
        self.pad_owned = True
        self.cmd(f'input 1 none 6 {80 if direction > 0 else -80} 0', 'test_controller')
        self.sleep(.12)
        self.cmd('input 1 none 1', 'test_controller');self.sleep(.20)

    def smash(self, direction):
        self.pad_owned = True
        self.cmd(f'= gd.input(1,{{buttons=0,cx={127 if direction > 0 else -127}}},3)', 'test_controller')
        self.sleep(.05)
        self.cmd('input 1 none 1', 'test_controller');self.sleep(.65)

    def place(self, port, x, y, deadline=None):
        for attempt in range(6):
            if deadline is not None and self.clock() >= deadline:
                raise AssertionError('Position fixture timed out')
            try:
                self.cmd(f'tp {port} {x:.4g} {y:.4g}', 'explicit_fixture')
                return
            except RuntimeError:
                if attempt == 5:
                    raise
                self.sleep(.5)

    def await_state(self, timeout=18, **expected):
        deadline = self.clock()+timeout
        while self.clock() < deadline:
            state = self.state()
            if all(state.get(k) == v for k,v in expected.items()):
                return state
            self.sleep(.25)
        raise AssertionError('Native state timeout: ' + repr(expected))

    def root_commands(self):
        for _ in range(4):
            if self.state().get('command') == 'root':
                return
            self.press('UP')
        raise AssertionError('Could not return command menu to root')

    def menu_select(self, target):
        for direction in menu_path(self.cmd('rogue_menu'), target):
            self.press(direction)
        assert rows(self.cmd('rogue_menu'), 'rogue_menu')[-1]['focus'] == target, 'Native focus diverged'
        self.press('A')

    def menu_gene(self, gene):
        target = 'gene:' + gene
        for _ in range(32):
            previous = next((c for c in rows(self.cmd('rogue_menu'),'rogue_control') if c['id'] == 'previous'),None)
            if not previous or not previous['enabled']:
                break
            self.menu_select('previous')
        for _ in range(32):
            controls = rows(self.cmd('rogue_menu'),'rogue_control')
            if any(c['id'] == target for c in controls):
                self.menu_select(target)
                return
            nxt = next((c for c in controls if c['id'] == 'next'),None)
            if not nxt or not nxt['enabled']:
                break
            self.menu_select('next')
        raise AssertionError('Gene absent from native menu: ' + gene)

    def build(self):
        return rows(self.cmd('rogue_build'), 'rogue_gene')

    def assault(self):
        placed = [g for g in self.build() if g.get('host') == 'player' and g.get('slot') == 'assault']
        assert len(placed) == 1, 'Actual player assault placement required'
        return placed[0]

    def ability_state(self):
        state = self.state()
        for field in ('charge','cost','remaining','reach'):
            assert isinstance(state.get(field),(int,float)) and not isinstance(state[field],bool), (
                'rogue_state needs read-only assault ' + field)
        assert state.get('diag_version') == 1, 'rogue_state must expose versioned diagnostics'
        assert isinstance(state.get('runtime_ready'),bool) and isinstance(state.get('ability_ready'),bool), (
            'rogue_state needs runtime_ready and ability_ready')
        assert state['cost'] > 0 and state['ability_ready'] == state.get('ready'), 'Inconsistent ability readiness'
        return state

    def normal_speed(self, sample=False):
        assert self.value('gd.perf().target') == 60, 'Acceptance requires a 60 Hz paced process'
        for port in (1, 2):
            assert not self.value(f'gd.fly({port})'), 'Disable debug flight before ordinary combat acceptance'
        if sample:
            assert not self.value('gd.paused()'), 'Combat requires running simulation'
            frame, start = self.value('gd.match().frame'), self.clock()
            self.sleep(.5)
            end_frame = self.value('gd.match().frame')
            rate = (end_frame-frame)/(self.clock()-start)
            assert 0 < rate <= 75, 'Accelerated/turbo or stalled simulation: ' + str(rate)
            self.note('timing_observation',{'target':60,'logic_frames_per_second':rate})

    def stand_cpu(self):
        self.cpu_fixture = True
        self.cmd("= gd.cpu_mode(2,'stand')", 'explicit_fixture')

    def actors(self):
        return rows(self.cmd('rogue_enemies'), 'rogue_enemy')

    def enemy_value(self, handle, field):
        # The console cannot call gameplay-only gd.enemy_state. The owning mod
        # supplies immutable diagnostic rows through its read-only command.
        actor = next((e for e in self.actors() if e.get('handle') == handle), None)
        return actor.get(field) if actor else None

    def kill_custom(self, room, timeout=45):
        """Real ordinary pad attacks; only player positioning is a fixture."""
        deadline, attacks = self.clock()+timeout, 0
        while self.clock() < deadline:
            state = self.state()
            assert state.get('room') == room and state.get('menu') is None, 'Unexpected combat transition'
            assert state.get('stocks',0) > 0, 'Run ended during custom enemy combat'
            if state.get('cleared'):
                self.note('custom_room_clear',{'room':room,'controller_attacks':attacks,
                    'evidence':'Native cleared flag; disappearance alone is not proof of melee KO'})
                return
            actors = self.actors()
            if not actors:
                self.sleep(.2)
                continue
            actor = actors[0]
            x = max(-58,min(58,actor['x']-4))
            direction = 1 if actor['x'] >= x else -1
            self.face(direction)
            actor = next((e for e in self.actors() if e.get('handle') == actor['handle']),None)
            if actor is None:
                continue
            x = max(-58,min(58,actor['x']-direction*4))
            self.place(1,x,max(0,actor['y']),deadline)
            before = self.enemy_value(actor['handle'],'received')
            self.smash(direction);attacks += 1
            after = self.enemy_value(actor['handle'],'received')
            self.note('native_melee_observation',{'handle':actor['handle'],'received_before':before,
                'received_after':after,'attack':'ordinary C-stick smash'})
        raise AssertionError('Controller melee did not clear '+room+' within timeout')

    def door(self, side, destination):
        self.root_commands();self.place(1,-55 if side == 'left' else 55,0);self.press('DOWN')
        # Exit commits finish and returns to collection with active=false.
        return self.await_state(room=destination,**({} if destination == 'exit' else {'active':True}))

    def to_arena(self, branch):
        state = self.state()
        if state.get('menu') == 'collection':
            controls = rows(self.cmd('rogue_menu'),'rogue_control')
            resume = any(c['id'] == 'resume' and c['enabled'] for c in controls)
            self.menu_select('resume' if resume else 'start')
            state = self.await_state(active=True,menu=None)
        if state.get('room') == 'entry':
            self.cmd('resume','test_capture_control')
            state = self.door('right','trail')
        if state.get('room') == 'trail':
            self.cmd('resume','test_capture_control')
            self.normal_speed(sample=True);self.kill_custom('trail')
            state = self.door('left' if branch == 'a' else 'right','arena_'+branch)
        assert state.get('room') == 'arena_'+branch, 'Selected branch was not reached'

    def cast_assault(self, capture=False):
        before = self.ability_state()
        assert before['ready'], 'Assault must be naturally ready'
        self.root_commands()
        family = self.assault()['family']
        assert family in ('cinder','rime'), 'Unsupported assault family'
        self.press('LEFT');self.press('LEFT' if family == 'cinder' else 'RIGHT');self.press('LEFT',.04)
        after = self.ability_state()
        assert after['charge'] < before['charge'], 'Actual command refused; charge retained'
        if capture:
            self.cmd('shot /tmp/roguelite-release-early.png');self.cmd('fx')
            self.cmd('pause','test_capture_control');self.cmd('shot /tmp/roguelite-release-late.png')
        return before,after

    def earn_charge(self):
        state = self.ability_state()
        assert state.get('room') in ('arena_a','arena_b') and state.get('menu') is None and not state.get('cleared')
        self.stand_cpu();self.cmd('resume','test_capture_control');self.normal_speed(sample=True)
        self.face(1);self.place(1,0,0);self.place(2,5,0)
        drain_partial = state['charge'] > 0 and not state['ready']
        if state['charge'] > 0 and state['ready']:
            self.cast_assault()  # Consume prior charge through actual gameplay, never deletion.
        baseline, deadline, confirmed_hits = self.ability_state()['charge'], self.clock()+40, 0
        while self.clock() < deadline:
            state = self.ability_state()
            if state['ready']:
                if drain_partial:
                    self.cast_assault()
                    baseline = self.ability_state()['charge']
                    confirmed_hits = 0
                    drain_partial = False
                    self.note('prior_charge_consumed',{'method':'Actual fighter-target gene release'})
                    continue
                assert confirmed_hits > 0 and state['charge'] > baseline, 'No observed arena-earned charge'
                self.earned_charge = True
                self.note('arena_charge_earned',{'charge_before':baseline,'charge_after':state['charge'],
                    'cost':state['cost'],'confirmed_fighter_collisions':confirmed_hits})
                return state
            assert not state.get('cleared') and state.get('menu') is None, 'Arena ended before charge test'
            if state['remaining'] > 0:
                self.sleep(.25)
                continue
            self.face(1);self.place(1,0,0,deadline);self.place(2,5,0,deadline)
            percent = self.value('gd.player(2).percent')
            self.press('A',.04);self.sleep(.7)
            after = self.value('gd.player(2).percent')
            if after > percent:
                confirmed_hits += 1
            self.note('native_fighter_hit_observation',{'percent_before':percent,'percent_after':after})
        raise AssertionError('Actual fighter collisions failed to earn ready charge')

    def to_rest(self):
        state = self.state()
        assert state.get('room') in ('arena_a','arena_b')
        if state.get('menu') != 'reward' and not state.get('cleared'):
            self.stand_cpu();self.cmd('resume','test_capture_control');self.place(2,0,-150)
            state = self.await_state(menu='reward')
        if state.get('menu') == 'reward':
            self.cmd('shot /tmp/roguelite-reward-live.png');self.menu_select('reward1')
        self.door('right','rest');self.await_state(room='rest',menu='rest')
        self.cmd('shot /tmp/roguelite-rest-live.png')

    def workbench(self):
        assault = self.assault()
        self.menu_gene(assault['id'])
        if any(c['id'] == 'place:traversal' and c['enabled'] for c in rows(self.cmd('rogue_menu'),'rogue_control')):
            self.menu_select('place:traversal');self.cmd('shot /tmp/roguelite-placement-live.png')
            self.menu_select('place:assault')
        partners = [g for g in self.build() if g['id'] != assault['id'] and g['family'] == assault['family']
                    and g['host'] in ('player','unplaced')]
        for partner in partners:
            self.menu_gene(assault['id']);self.menu_select('parents');self.menu_gene(partner['id'])
            if any(c['id'] == 'confirm' and c['enabled'] for c in rows(self.cmd('rogue_menu'),'rogue_control')):
                self.menu_select('confirm');self.cmd('shot /tmp/roguelite-fusion-live.png')
                return
            self.menu_select('back')
        self.note('fusion_unavailable',{'selected_gene':assault['id'],'candidate_parents':len(partners)})

    def custom_gene_check(self):
        assert self.earned_charge, 'Custom check requires arena hits recorded in this invocation'
        state = self.ability_state()
        assert state.get('room') == 'approach' and state['ready'], 'Arena charge not retained into approach'
        actors = self.actors()
        assert len(actors) == 1 and actors[0]['kind'] == 'redead', 'Expected actual ReDead encounter'
        handle, deadline, telegraph = actors[0]['handle'], self.clock()+25, False
        percent_before = self.value('gd.player(1).percent')
        while self.clock() < deadline:
            actor = next((e for e in self.actors() if e['handle'] == handle),None)
            assert actor is not None, 'Actor vanished before gene release evidence'
            facing = actor.get('facing', -1) or -1
            self.place(1,max(-58,min(58,actor['x']+facing*4)),max(0,actor['y']),deadline)
            self.cmd('input 1 none 1','test_controller');self.pad_owned=True
            telegraph = telegraph or actor['phase'] == 'telegraph'
            if telegraph and actor['phase'] == 'recovery':
                percent_after = self.value('gd.player(1).percent')
                assert percent_after > percent_before, 'Recovery had no observed native player damage'
                self.note('custom_enemy_gene_release',{'handle':handle,'telegraph_observed':True,
                    'recovery_observed':True,'percent_before':percent_before,'percent_after':percent_after})
                break
            self.sleep(.10)
        else:
            raise AssertionError('Custom enemy did not earn/release its gene within timeout')
        deadline = self.clock()+12
        while self.clock() < deadline:
            actor = next((e for e in self.actors() if e['handle'] == handle),None)
            assert actor is not None, 'Actor vanished before player gene check'
            self.face(1)
            actor = next((e for e in self.actors() if e['handle'] == handle),None)
            assert actor is not None, 'Actor vanished while facing the custom target'
            self.place(1,max(-58,min(58,actor['x']-4)),max(0,actor['y']),deadline)
            action, hitlag = self.value('gd.player(1).action'), self.value('gd.player(1).hitlag')
            if 14 <= action <= 34 and action != 24 and hitlag == 0:
                break
            self.sleep(.15)
        else:
            raise AssertionError('Player did not reach a free casting action')
        damage_before, received_before = self.enemy_value(handle,'damage'), self.enemy_value(handle,'received')
        before, after = self.cast_assault()
        damage_after, received_after = self.enemy_value(handle,'damage'), self.enemy_value(handle,'received')
        cleared = self.state().get('cleared')
        assert ((received_after is not None and received_after > received_before)
                or (damage_after is not None and damage_after > damage_before) or cleared), 'No custom actor impact'
        self.note('player_gene_custom_target',{'handle':handle,'charge_before':before['charge'],
            'charge_after':after['charge'],'damage_before':damage_before,'damage_after':damage_after,
            'received_before':received_before,'received_after':received_after,'room_cleared':cleared})
        self.cmd('shot /tmp/roguelite-custom-gene-live.png')

    def finish_route(self, custom=False):
        assert self.state().get('menu') == 'rest', 'Finish route begins at rest'
        if not custom:
            self.workbench()
        self.menu_select('continue');self.door('right','approach')
        if custom:
            self.custom_gene_check()
        self.normal_speed(sample=True);self.kill_custom('approach');self.door('right','boss')
        self.stand_cpu();self.place(1,-55,0)
        for ringout in range(2):
            self.place(2,0,-150);self.sleep(2)
            state = self.state()
            if ringout == 0:
                assert state.get('menu') is None and not state.get('cleared'), 'Champion needs two native KOs'
            else:
                self.await_state(menu='reward')
        self.menu_select('reward1');self.door('right','exit')
        self.await_state(room='exit',menu='collection',saveerror=False,outcome='success')
        self.cmd('shot /tmp/roguelite-win-live.png')

    def cleanup(self):
        errors = []
        def attempt(action):
            try:
                action()
            except Exception as error:
                errors.append(str(error))
        if self.pad_owned:
            attempt(lambda: self.cmd('input 1 none 1','test_controller_cleanup'))
            attempt(self.root_commands)
        if self.cpu_fixture:
            def restore_cpu():
                diagnostic = rows(self.cmd('rogue_state'),'rogue_state')
                assert diagnostic, 'Missing CPU cleanup context'
                state = diagnostic[-1]
                mode = 'fight' if state.get('room') in ('arena_a','arena_b','boss') and not state.get('cleared') else 'stand'
                self.cmd(f"= gd.cpu_mode(2,'{mode}')",'explicit_fixture_cleanup')
            attempt(restore_cpu)
        if self.pad_owned:
            attempt(lambda: self.cmd('gd.release_pad(1)','test_controller_cleanup'))
        return errors


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=51700)
    p.add_argument('--log',type=Path,default=Path('/tmp/roguelite-acceptance.jsonl'))
    p.add_argument('--branch',choices=('a','b'),default='a')
    p.add_argument('--route',action='store_true',help='Selected branch, arena-earned charge and full route')
    p.add_argument('--custom-enemy',action='store_true',help='With --route: native ReDead/player gene evidence')
    for option in ('pad-tree','to-arena','charge-release','platform','to-rest','finish-route','failure-run'):
        p.add_argument('--'+option,action='store_true')
    for option in ('command','press','menu'):
        p.add_argument('--'+option,action='append',default=[])
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.custom_enemy and not args.route:
        raise SystemExit('--custom-enemy requires --route to record arena-earned charge')
    actions = any((args.route,args.pad_tree,args.to_arena,args.charge_release,args.platform,
                   args.to_rest,args.finish_route,args.failure_run,args.press,args.menu))
    with args.log.open('a') as evidence, socket.create_connection(('127.0.0.1',args.port),timeout=10) as sock:
        reader = sock.makefile('r');reader.readline()
        def record(category, **data):
            evidence.write(json.dumps(dict(time=time.time(),category=category,**data))+'\n');evidence.flush()
        def cmd(command, category='observation'):
            output, ok = run(reader,sock,command)
            record(category,command=command,ok=ok,output=output)
            text = '\n'.join(output);print(command,'=>',text,flush=True)
            if not ok:
                raise RuntimeError({'command':command,'output':output})
            return text
        d = Driver(cmd,note=lambda event,detail: record('acceptance_observation',event=event,detail=detail))
        failed = False
        try:
            d.state()
            if actions:
                d.normal_speed()
            for command in args.command:
                cmd(command,'explicit_fixture')
            for control in args.menu:
                d.menu_select(control)
            if args.route and d.state().get('menu') == 'collection':
                d.menu_select('start');d.await_state(active=True,menu=None)
            if args.route or args.to_arena:
                d.to_arena(args.branch)
            if args.platform:
                assert d.state().get('room') in ('trail','approach','arena_a','arena_b','boss'), 'Current room has no added platform'
                d.stand_cpu();d.place(1,-22,0);cmd('resume','test_capture_control');d.press('X',.03);d.sleep(1.3)
                assert abs(d.value('gd.player(1).y')-12) < .1 and not d.value('gd.player(1).airborne'), 'No native y12 platform landing'
                cmd('state');cmd('shot /tmp/roguelite-platform-live.png')
            if args.route or args.charge_release:
                d.earn_charge()
            if args.charge_release and not args.route:
                d.face(1);d.place(1,0,0);d.place(2,5,0)
                before = d.value('gd.player(2).percent');d.cast_assault(capture=True)
                assert d.value('gd.player(2).percent') > before, 'No native fighter gene damage'
            if args.route or args.to_rest:
                d.to_rest()
            if args.route or args.finish_route:
                d.finish_route(custom=args.custom_enemy)
            if args.failure_run:
                assert d.state().get('menu') == 'collection'
                d.menu_select('start');d.await_state(room='entry',active=True,stocks=3)
                for lives in (2,1,0):
                    d.place(1,0,-150);state = d.await_state(stocks=lives)
                    if lives:
                        assert state.get('menu') is None;d.sleep(1)
                    else:
                        assert state.get('menu') == 'collection' and not state.get('saveerror') and state.get('outcome') == 'failure'
                cmd('shot /tmp/roguelite-failure-live.png')
            if args.pad_tree:
                if d.state().get('menu') == 'collection':
                    d.menu_select('start');d.await_state(room='entry',active=True,menu=None)
                assert d.state().get('room') == 'entry'
                cmd('resume','test_capture_control');d.root_commands()
                d.press('LEFT',.6);assert d.state()['command'] == 'magic'
                d.press('LEFT');assert d.state()['command'] == 'fire'
                d.press('UP');assert d.state()['command'] == 'magic'
                d.press('UP',.5);assert d.state()['command'] == 'root'
                assert 'Appeal' not in cmd('= gd.motion_name(gd.player(1).action,1)')
                d.press('UP',.12);assert 'Appeal' in cmd('= gd.motion_name(gd.player(1).action,1)')
            for button in args.press:
                d.press(button);d.state()
            d.state()
        except BaseException:
            failed = True
            if actions or args.command:
                try:
                    cmd('pause','test_failure_preservation')
                except Exception as error:
                    print('Could not preserve failed capture:',error,file=sys.stderr)
            raise
        finally:
            errors = d.cleanup()
            if errors:
                record('cleanup_failure',errors=errors)
                if not failed:
                    raise RuntimeError('Acceptance cleanup failed: '+repr(errors))


if __name__ == '__main__':
    main()
