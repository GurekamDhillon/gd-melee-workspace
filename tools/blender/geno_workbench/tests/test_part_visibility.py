"""Model-part visibility selection (authored fixture; the real tables come from the disc via HsdExport --parts)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "falcon"))
import part_visibility as pv


def doc():
    names = ["Joint_0_Object_%d" % i for i in range(6)] + ["Joint_9_Object_0_SINGLE", "Joint_9_Object_1_SINGLE"]
    dobjs = [{"index": i, "joint": 0 if i < 6 else 9, "rank": i if i < 6 else i - 6, "name": n} for i, n in enumerate(names)]
    dobjs[3]["alpha"] = 0.4
    dobjs[2]["cull"] = "front"
    return {"dobjs": dobjs, "model_num": 2, "rows": [
        {"costume": 0, "lods": {
            "high": [[[0, 1]], [[4], [5]]],            # part 0: one state; part 1: two states
            "low": [[[2, 3]], [[6], [7]]],
            "metal": [[[0]]],                           # the metal model's own list: never ours
            "metal_main": [[[1]], []]}},
        {"costume": 1, "lods": {"high": None, "low": None}}]}


def test_high_poly_hides_low_set_and_unchosen_states():
    d = doc()
    assert pv.select_hidden(d) == [2, 3, 5, 6, 7]       # low set, part 1's state 1, and the low part-1 states
    assert pv.hidden_names(d)[:2] == ["Joint_0_Object_2", "Joint_0_Object_3"]


def test_state_choice_and_low_lod():
    d = doc()
    assert pv.select_hidden(d, states={1: 1}) == [2, 3, 4, 6, 7]
    assert pv.select_hidden(d, lod="low") == [0, 1, 4, 5, 7]      # low shows state 0 of each part only (6, 2, 3 drawn)


def test_metal_table_is_not_in_the_main_list_and_metal_main_stays_hidden_unless_high_shows_it():
    d = doc()
    d["rows"][0]["lods"]["metal_main"] = [[[1, 2]], []]
    assert 1 not in pv.select_hidden(d)                  # high shows 1 again, as the engine draws high last
    assert 2 in pv.select_hidden(d)                      # 2 is in low and metal_main only


def test_missing_costume_row_falls_back_to_row_zero():
    d = doc()
    assert pv.select_hidden(d, costume=1) == pv.select_hidden(d, costume=0)
    assert pv.select_hidden(d, costume=7) == pv.select_hidden(d, costume=0)


def test_no_rows_hides_nothing():
    assert pv.select_hidden({"dobjs": [], "rows": []}) == []


def test_alpha_and_cull_tables():
    d = doc()
    assert pv.alpha_by_name(d) == {"Joint_0_Object_3": 0.4}
    assert pv.cull_names(d) == {"Joint_0_Object_2"}


def test_apply_to_objects_reports_missing_names():
    class Obj(SimpleNamespace):
        def __setitem__(self, k, v):
            self._p[k] = v
    objs = [Obj(name=n, hide_render=False, hide_viewport=False, _p={}) for n in "ab"]
    found, missing = pv.apply_to_objects(objs, ["a", "zz"])
    assert found == ["a"] and missing == ["zz"]
    assert objs[0].hide_render and objs[0].hide_viewport and objs[0]._p == {"geno_part_hidden": 1}
    assert not objs[1].hide_render


def test_replace_diffuse_whitens_the_multiply_factor():
    class Sock(SimpleNamespace):
        pass
    def mix(b, linked=False):
        socks = [Sock(links=[], default_value=(0, 0, 0, 1)) for _ in range(10)]
        socks[7] = Sock(links=[1] if linked else [], default_value=b)
        return SimpleNamespace(type='MIX', data_type='RGBA', blend_type='MULTIPLY', inputs=socks)
    a, linked = mix((0.7, 0.7, 0.7, 1)), mix((0.7, 0.7, 0.7, 1), True)
    mat = SimpleNamespace(use_nodes=True, node_tree=SimpleNamespace(nodes=[a, linked]))
    obj = SimpleNamespace(data=SimpleNamespace(materials=[mat, None]))
    assert pv.apply_replace_diffuse([obj]) == 1
    assert tuple(a.inputs[7].default_value) == (1.0, 1.0, 1.0, 1.0)
    assert tuple(linked.inputs[7].default_value) == (0.7, 0.7, 0.7, 1)
    assert pv.apply_replace_diffuse([obj]) == 0
