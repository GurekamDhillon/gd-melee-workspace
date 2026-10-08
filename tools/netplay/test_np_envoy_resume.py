"""Offline regressions for the stage-5 proof's live-state and reconnect checks."""
import importlib.util
import os
from pathlib import Path
import subprocess
import unittest

os.environ.setdefault("GW_MELEE", "unused-game")
os.environ.setdefault("GW_BUILD_ROOT", "unused-build")
spec = importlib.util.spec_from_file_location("proof", Path(__file__).with_name("np_envoy_resume.py"))
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class ProofTests(unittest.TestCase):
    def test_abandon_checks_live_lobby_not_archived_game_two(self):
        # The real Lua probe must read the new lobby while the abandoned record
        # deliberately still holds the old game, score and picks.
        lua = '''gd={netplay=function() return {phase="lobby",game=1,score={0,0},
          envoy={mode="versus",seed=1488769113,round=0,open=false,word="c0d58f6b",picks={-1,-1},history={},
            run={status="abandoned",pending=false,live=false,resumed=1,abandoned=1,interrupted=0,note="abandoned",
              record={digest="97164c34fc8f1184",state="abandoned",game=2,round=2,seed=1996363217,
                score={1,0},picks={[2]={1,2}}}}}} end}
        print(%s)
        print(%s)
        ''' % (proof.LOBBY, proof.RUN)
        result = subprocess.run(["lua", "-"], input=lua, text=True, capture_output=True, check=True)
        lines = result.stdout.splitlines()
        live = proof.parse(lines[0], proof.LOBBY_KEYS)
        archived = proof.parse(lines[1], proof.RUN_KEYS)
        self.assertEqual((archived["game"], archived["score"], archived["pick2"]), ("2", "1-0", "12"))
        self.assertTrue(proof.fresh_lobby(live, live))
        for key, bad in (("game", "2"), ("score", "1-0"), ("picks", "1,-1"),
                         ("history", "false"), ("live", "true"), ("env_open", "true"),
                         ("env_round", "2"), ("phase", "connecting")):
            with self.subTest(key=key):
                self.assertFalse(proof.fresh_lobby(live, dict(live, **{key: bad})))
        self.assertFalse(proof.fresh_lobby(live, dict(live, env_seed="999")))

    def test_rejoin_waits_for_host_to_leave_old_lobby_without_live_record(self):
        events = []

        class Host:
            def __init__(self):
                self.phases = iter(("lobby", "working"))

            def state(self):
                phase = next(self.phases)
                events.append(phase)
                return {"phase": phase}

        class Guest:
            def kill(self):
                events.append("kill")

            def launch(self, code):
                events.append("launch " + code)

        driver = object.__new__(proof.Driver)
        driver.host, driver.guest = Host(), Guest()
        # Advance deterministic observations instead of wall time or sockets.
        def wait(what, predicate, *args):
            self.assertFalse(predicate())
            return predicate()
        driver.wait = wait
        self.assertTrue(driver.rejoin_after_loss("ABCD"))
        self.assertEqual(events, ["kill", "lobby", "working", "launch ABCD"])

    def test_rejoin_timeout_does_not_launch_into_old_session(self):
        driver = object.__new__(proof.Driver)
        events = []
        class Guest:
            def kill(self): events.append("kill")
            def launch(self, code): events.append("launch")
        driver.guest = Guest()
        driver.wait = lambda *args: None
        self.assertFalse(driver.rejoin_after_loss("ABCD"))
        self.assertEqual(events, ["kill"])


if __name__ == "__main__":
    unittest.main()
