#!/usr/bin/env python3
"""Ultimate mesh visibility -> ModelVis channels (vis_channels.py), checked against a model of the
engine's ftParts_80074B6C and, where the Ultimate extraction exists, Sora's real clips."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vis_channels as VC  # noqa: E402


def engine_visible(models, current, dobj_count):
    """ftParts_80074B6C: every DObj starts shown; per model, in state order, the current state's
    DObjs are shown and every other state's hidden (later states win). `models` is
    [model][state] -> DObj indexes, `current` the state per model (-1: nothing current)."""
    shown = [True] * dobj_count
    for states, cur in zip(models, current):
        for j, dobjs in enumerate(states):
            for d in dobjs:
                shown[d] = (j == cur)
    return {i for i, s in enumerate(shown) if s}


# Sora-like toy: eyes and lids are exclusive, the mouth is independent, the blush never shows.
CLIPS = {
    "wait": [{"Eye", "Openblink", "MouthN", "Sword"}] * 3 + [{"Halfblink1", "MouthN", "Sword"},
                                                            {"Blink", "MouthN", "Sword"},
                                                            {"Eye", "Openblink", "MouthN", "Sword"}],
    "ouch": [{"Eye_Heavyhit", "Blink_Ouch", "MouthOuch", "Sword"}] * 4,
    "talk": [{"Eye", "Openblink", "MouthTalk", "Sword"}] * 4,
}
GROUPS = ["Eye", "Eye_Heavyhit", "Openblink", "Halfblink1", "Blink", "Blink_Ouch", "MouthN", "MouthOuch",
          "MouthTalk", "Sword", "Hot"]
# DObj order of a costume: body first, then two DObjs for some groups (left/right, skin/alpha)
DOBJS = [None, "Sword", "Eye", "Eye", "Eye_Heavyhit", "Eye_Heavyhit", "Hot", "Blink", "Blink", "Openblink",
         "Openblink", "Halfblink1", "Blink_Ouch", "MouthN", "MouthN", "MouthOuch", "MouthTalk", "MouthTalk"]


def models_for(channels, dobjs=DOBJS):
    return VC.state_lists(channels, dobjs)


class ChannelPlanTest(unittest.TestCase):
    def setUp(self):
        self.frames = [frozenset(s) for seq in CLIPS.values() for s in seq]
        self.channels = VC.plan_channels(self.frames, GROUPS)

    def test_states_of_one_model_never_share_a_dobj(self):
        for states in models_for(self.channels):
            seen = [d for s in states for d in s]
            self.assertEqual(len(seen), len(set(seen)))

    def test_every_group_is_in_exactly_one_channel(self):
        flat = [g for ch in self.channels for g in ch]
        self.assertEqual(sorted(flat), sorted(GROUPS))

    def test_groups_visible_together_are_never_in_one_channel(self):
        for fs in self.frames:
            for ch in self.channels:
                self.assertLessEqual(len(fs & set(ch)), 1)

    def test_engine_shows_exactly_the_source_visible_meshes_every_frame(self):
        models = models_for(self.channels)
        for name, seq in CLIPS.items():
            states = VC.apply_events(VC.events_for(seq, self.channels), len(seq), len(self.channels))
            for f, visible in enumerate(seq):
                got = engine_visible(models, states[f], len(DOBJS))
                want = {i for i, g in enumerate(DOBJS) if g is None or g in visible}
                self.assertEqual(got, want, f"{name} frame {f}")

    def test_a_never_visible_mesh_is_hidden(self):
        models = models_for(self.channels)
        states = VC.apply_events(VC.events_for(CLIPS["wait"], self.channels), 5, len(self.channels))
        self.assertNotIn(DOBJS.index("Hot"), engine_visible(models, states[0], len(DOBJS)))

    def test_every_channel_is_set_at_frame_zero(self):
        events = VC.events_for(CLIPS["wait"], self.channels)
        self.assertEqual(sorted(c for f, (c, s) in events if f == 0), list(range(len(self.channels))))

    def test_changes_after_frame_zero_name_only_the_channel_that_changed(self):
        events = VC.events_for(CLIPS["wait"], self.channels)
        later = [e for e in events if e[0] > 0]
        self.assertTrue(later)
        self.assertLess(len(later), len(events))
        self.assertTrue(all(e[1][0] != self.channels.index(next(c for c in self.channels if "MouthN" in c))
                            for e in later))

    def test_too_many_channels_is_an_error(self):
        groups = ["g%d" % i for i in range(VC.MAX_MODELS + 1)]
        with self.assertRaises(ValueError):
            VC.plan_channels([frozenset(groups)], groups)

    def test_two_meshes_of_one_channel_visible_together_is_an_error(self):
        with self.assertRaises(ValueError):
            VC.channel_states({"a", "b"}, [["a", "b"]])


class OldLayoutRegressionTest(unittest.TestCase):
    """The layout this module replaced: one model whose states are the distinct visible sets."""

    def test_overlapping_state_sets_hide_the_current_meshes(self):
        sets = sorted({frozenset(s) for seq in CLIPS.values() for s in seq}, key=sorted)
        models = [[[i for i, g in enumerate(DOBJS) if g in s] for s in sets]]
        for k, want_set in enumerate(sets):
            want = {i for i, g in enumerate(DOBJS) if g in want_set}
            got = engine_visible(models, [k], len(DOBJS)) - {0}
            if got != want:
                return
        self.fail("expected at least one state whose meshes the engine re-hides")


@unittest.skipUnless(os.path.isdir(os.path.join(HERE, "..", "..", "..", "experiment", "tooling", "ultimate",
                                               "workspace", "extracted", "fighter", "trail", "motion", "body", "c00")),
                     "Ultimate trail extraction not present")
class SoraRealClipsTest(unittest.TestCase):
    def test_idle_shows_open_eyes_and_no_blush_or_closed_lids(self):
        import convert_ultimate_anim as CA
        import install_ultimate as IU
        motion = os.path.join(CA.FIGHTERS, "trail", "motion", "body", "c00")
        base_anim = CA.decode(os.path.join(motion, "a00defaulteyelid.nuanmb"))
        base = {}
        for n in [g for g in base_anim["groups"] if g["group_type"] == "Visibility"][0]["nodes"]:
            v = n["tracks"][0]["values"]
            base[n["name"]] = (next(iter(v.values())) if isinstance(v, dict) else v)[0]
        seqs = {c: IU.vis_frames(CA.decode(os.path.join(motion, c + ".nuanmb")), base)
                for c in ("a00wait1", "f00damagehi1", "c00attack11")}
        frames = {s for seq in seqs.values() for s in seq} | {frozenset(k for k, on in base.items() if on)}
        controlled = sorted({g for s in frames for g in s} | set(base))
        channels = VC.plan_channels(frames, controlled)
        # a stand-in costume: one DObj per controlled mesh plus an always-visible body
        dobjs = [None] + controlled
        models = VC.state_lists(channels, dobjs)
        idle = seqs["a00wait1"]
        states = VC.apply_events(VC.events_for(idle, channels), len(idle), len(channels))
        shown = engine_visible(models, states[0], len(dobjs))
        names = {dobjs[i] for i in shown if dobjs[i]}
        self.assertEqual(names, set(idle[0]))
        self.assertIn("trail_Eye", names)
        self.assertIn("trail_Openblink", names)
        self.assertNotIn("trail_Hot", names)
        self.assertFalse([n for n in names if n.startswith("trail_Blink")])
        for seq in seqs.values():
            ev = VC.apply_events(VC.events_for(seq, channels), len(seq), len(channels))
            for f, visible in enumerate(seq):
                self.assertEqual({dobjs[i] for i in engine_visible(models, ev[f], len(dobjs)) if dobjs[i]},
                                 set(visible))


if __name__ == "__main__":
    unittest.main()
