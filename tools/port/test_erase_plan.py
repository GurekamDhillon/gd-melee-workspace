"""Pins the Atlas Erase Data plan table to the retail handlers: python tools/port/test_erase_plan.py

pc/platform/gw_ui_erase.h lists, for each of the six retail operations, the state-changing calls in order. src/melee/mn/mndatadel.c holds the retail code (the five
case arms of fn_8024F318, mnDataDel_8024E940 for case 1, mnDataDel_8024EA6C for everything) and mnDataDel_RunCall, which turns a plan id into the real call. This test
reads all three as text: the calls each retail operation makes, in order, must be the table's, and every id must run the call it names. A change to the retail code or
to the table is then seen here, not found by erasing something. No test touches a save.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")

STATE = re.compile(r"\b(gm_[0-9A-Fa-f]{8}|gmMainLib_[0-9A-Fa-f]{8}|Toy_[0-9A-Fa-f]{8}|lbCardGame_SaveChanges|lbLang_GetSavedLanguage|lbLang_SetSavedLanguage)\s*\(")
# what each plan id calls, in the order the retail code makes the calls
EXPAND = {
    "AT_ER_SAVE": ["lbCardGame_SaveChanges"],
    "AT_ER_STAGE_RELOCK": ["gm_80164430", "gm_801641CC", "gm_801641E4"],
    "AT_ER_LANG_SAVE": ["lbLang_GetSavedLanguage"],
    "AT_ER_LANG_RESTORE": ["lbLang_GetSavedLanguage", "lbLang_SetSavedLanguage"],
    "AT_ER_DEFLICKER_APPLY": ["gmMainLib_8015F588", "gmMainLib_8015F4E8"],
}


def read(*p):
    with open(os.path.join(GAME, *p), encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n")


def plan():
    text = read("pc", "platform", "gw_ui_erase.h")
    body = re.search(r"at_erase_plan\[6\]\[9\] = \{(.*?)\n\};", text, re.S).group(1)
    rows = [re.findall(r"AT_ER_\w+", r) for r in re.findall(r"\{([^{}]*)\}", body)]
    return rows


def default_name(ident):
    m = re.match(r"AT_ER_(GM|MAINLIB|TOY)_([0-9A-F]{8})$", ident)
    if not m:
        return None
    return {"GM": "gm_", "MAINLIB": "gmMainLib_", "TOY": "Toy_"}[m.group(1)] + m.group(2)


def expected_names(row):
    out = []
    for ident in row:
        out += EXPAND.get(ident) or [default_name(ident)]
    return out


def func_body(src, name):
    m = re.search(r"\n(?:static )?(?:void|int) %s\([^)]*\)\n\{" % re.escape(name), src)
    start = m.end()
    end = src.index("\n}\n", start)
    return src[start:end]


def retail_sequences():
    src = read("src", "melee", "mn", "mndatadel.c")
    src = src[:src.index("#if defined(TARGET_PC)\n/* ---- Atlas")] if "#if defined(TARGET_PC)\n/* ---- Atlas" in src else src
    think = func_body(src, "fn_8024F318")
    arms = re.split(r"\n\s*case (\d+):", think)
    seq = {}
    for i in range(1, len(arms), 2):
        n = int(arms[i])
        arm = arms[i + 1].split("break;")[0]
        if n in (0, 1, 2, 3, 4):
            seq[n] = STATE.findall(arm)
    seq[1] = STATE.findall(func_body(src, "mnDataDel_8024E940"))      # case 1 is a call
    seq[5] = STATE.findall(func_body(src, "mnDataDel_8024EA6C"))
    return seq


class ErasePlan(unittest.TestCase):
    def test_six_operations(self):
        self.assertEqual(len(plan()), 6)

    def test_plan_matches_the_retail_call_order(self):
        seq, rows = retail_sequences(), plan()
        self.assertEqual(sorted(seq), [0, 1, 2, 3, 4, 5])
        for n in range(6):
            self.assertEqual(expected_names(rows[n]), seq[n], "operation %d: the plan table and the retail handler disagree" % n)

    def test_every_id_runs_the_call_it_names(self):
        src = read("src", "melee", "mn", "mndatadel.c")
        run = func_body(src, "mnDataDel_RunCall")
        cases = dict(re.findall(r"case (AT_ER_\w+):(.*?)(?=\n    case |\n    default)", run, re.S))
        ids = sorted({i for row in plan() for i in row})
        self.assertEqual(sorted(cases), ids, "every plan id has a case, and every case a plan id")
        for ident in ids:
            names = STATE.findall(cases[ident])
            if ident == "AT_ER_STAGE_RELOCK":
                self.assertIn("mnDataDel_StageRelock", cases[ident])
                continue
            if ident == "AT_ER_LANG_SAVE":
                self.assertEqual(names, ["lbLang_GetSavedLanguage"])
                continue
            if ident == "AT_ER_LANG_RESTORE":
                self.assertEqual(names, ["lbLang_GetSavedLanguage", "lbLang_SetSavedLanguage"])
                continue
            if ident == "AT_ER_DEFLICKER_APPLY":
                self.assertEqual(names, ["gmMainLib_8015F588", "gmMainLib_8015F4E8"])
                continue
            self.assertEqual(names, expected_names([ident]), ident)

    def test_stage_relock_is_the_retail_loop(self):
        src = read("src", "melee", "mn", "mndatadel.c")
        relock = func_body(src, "mnDataDel_StageRelock")
        retail = func_body(src, "mnDataDel_8024E940")
        for needle in ("i < 0x1D", "gm_80164430(gm_801641CC(i))", "gm_IsStageUnlocked((u16) i)", "gm_801641E4(0U, 1U)"):
            self.assertIn(needle, relock)
            self.assertIn(needle, retail)

    def test_the_erase_screen_names_what_the_header_names(self):
        """The rows of fe_items_erase carry the plan's labels: what the screen says is what the table runs."""
        header = read("pc", "platform", "gw_ui_erase.h")
        names = re.search(r"names\[6\] = \{(.*?)\};", header, re.S).group(1)
        labels = re.findall(r'"([^"]+)"', names)
        settings = read("src", "melee", "gm", "gmfrontend_settings.inc")
        table = settings[settings.index("fe_items_erase[] = {"):]
        table = table[:table.index(chr(10) + "};")]
        rows = re.findall(r'\{ FE_ACTION, FE_DO_CALL, "([^"]+)"', table)
        self.assertEqual(rows, labels)
        self.assertEqual(re.findall(r"fse_ask(\d),", table), ["0", "1", "2", "3", "4", "5"])      # row n asks about operation n

    def test_erase_is_confirmed_only(self):
        src = read("src", "melee", "mn", "mndatadel.c")
        self.assertIn("at_erase_run(category, 1, mnDataDel_RunCall);", src)
        self.assertNotIn("HSD_JObj", func_body(src, "mnDataDel_RunCall"))     # no animation in the Atlas path: it runs with no retail screen


if __name__ == "__main__":
    unittest.main()
