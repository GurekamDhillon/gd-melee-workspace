import importlib
import importlib.util
import math

import pytest

import figatree_decode as D
import wbspace as W
from figatree_fixtures import F, archive, model, stream

IDENTITY = ((1., 0., 0., 0.), (0., 1., 0., 0.), (0., 0., 1., 0.), (0., 0., 0., 1.))


def importer():
    assert importlib.util.find_spec("figatree_import") is not None, "figatree pose importer is missing"
    return importlib.import_module("figatree_import")


def assert_matrix(got, want, tol=1e-7):
    for g, w in zip(got, want):
        assert g == pytest.approx(w, abs=tol)


def test_rest_pose_is_identity_even_with_nonidentity_rest_and_bone_axes():
    I = importer()
    rest = D.read_model(model([(None, (.2, -.3, .4), (3, 4, 5), (1, 1, 1), 8)]))
    bone = ((0., -1., 0., 3.), (1., 0., 0., 5.), (0., 0., 1., 4.), (0., 0., 0., 1.))
    plan = {"joints": [{"index": 0, "name": "root", "parent": None}]}
    sampler = I.PoseSampler(rest, plan, {"root": bone}, {"root": None})
    clip = D.read_bank(archive([[]]))[0]
    assert_matrix(sampler.bases(clip, 0)["root"], IDENTITY)


def test_absolute_translation_is_converted_to_bone_basis_not_copied():
    I = importer()
    rest = (D.RestJoint(None, (0, 0, 0), (0, 2, 0), (1, 1, 1)),)
    # Bone-local +Y points along model-space +Y; C moves it to Blender +Z.
    bone = W.mul(W.C4, I.srt_matrix((0, 0, 0), (0, 2, 0), (1, 1, 1)))
    plan = {"joints": [{"index": 0, "name": "source", "parent": None}]}
    sampler = I.PoseSampler(rest, plan, {"actual": bone}, {"actual": None}, aliases={"source": "actual"})
    clip = D.read_bank(archive([[(6, *F.encode_const(5)[:3])]]))[0]
    got = sampler.bases(clip, 0)["actual"]
    assert [got[i][3] for i in range(3)] == pytest.approx([0, 3, 0])
    assert sampler.jointmap.by_index == {0: "actual"}


def test_synthesized_parent_animation_reaches_mapped_child():
    I = importer()
    rest = (D.RestJoint(None, (0, 0, 0), (0, 0, 0), (1, 1, 1)),
            D.RestJoint(0, (0, 0, 0), (0, 2, 0), (1, 1, 1)))
    plan = {"joints": [{"index": 0, "name": "pivot", "parent": None, "synth": True},
                       {"index": 1, "name": "Child", "parent": 0}]}
    bone = I.srt_matrix((0, 0, 0), (0, 2, 0), (1, 1, 1))
    sampler = I.PoseSampler(rest, plan, {"Child": bone}, {"Child": None}, model_to_arm=IDENTITY)
    clip = D.read_bank(archive([[(3, *F.encode_const(math.pi/2, 0)[:3])], []]))[0]
    got = sampler.bases(clip, 0)["Child"]
    assert [got[i][3] for i in range(3)] == pytest.approx([-2, -2, 0], abs=2e-7)
    assert sampler.jointmap.skipped_synth == [0]


def test_scale_restoration_for_untracked_axes_and_following_action():
    I = importer()
    rest = (D.RestJoint(None, (0, 0, 0), (0, 0, 0), (1, 2, 1)),)
    bone = IDENTITY
    plan = {"joints": [{"index": 0, "name": "root", "parent": None}]}
    sampler = I.PoseSampler(rest, plan, {"root": bone}, {"root": None}, model_to_arm=IDENTITY)
    stretch = D.read_bank(archive([[(8, *F.encode_const(3)[:3])]]))[0]
    reset = D.read_bank(archive([[]]))[0]
    assert_matrix(sampler.bases(stretch, 0)["root"], ((3, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    assert_matrix(sampler.bases(reset, 0)["root"], IDENTITY)


def test_nonclassical_scale_compensation_matches_hsd():
    I = importer()
    rest = (D.RestJoint(None, (0, 0, 0), (0, 0, 0), (2, 4, 2), flags=0),
            D.RestJoint(0, (0, 0, math.pi/2), (0, 1, 0), (1, 1, 1), flags=0))
    # HSD parent-scale ratios cancel shear of the child's rotated axes.
    world = I.world_matrices(rest)
    assert_matrix(world[1], ((0, -4, 0, 0), (2, 0, 0, 4), (0, 0, 2, 0), (0, 0, 0, 1)))


def test_invalid_mapping_and_unsupported_tracks_are_explicit():
    I = importer()
    rest = (D.RestJoint(None, (0, 0, 0), (0, 0, 0), (1, 1, 1)),)
    plan = {"joints": [{"index": 0, "name": "root", "parent": None}]}
    with pytest.raises(ValueError, match="mapped"):
        I.PoseSampler(rest, plan, {"wrong": IDENTITY}, {"wrong": None})
    sampler = I.PoseSampler(rest, plan, {"root": IDENTITY}, {"root": None})
    path_clip = D.read_bank(archive([[(4, *F.encode_const(1)[:3])]]))[0]
    with pytest.raises(ValueError, match="channel 4"):
        sampler.bases(path_clip, 0)


def test_sampling_boundaries_include_signed_offsets_and_fractional_end():
    I = importer()
    body = stream([(1, 1, None, 2), (1, 3, None, None)])
    clip = D.read_bank(archive([[(5, body, 0, 0)]], frames=4.5, starts={0: -1}))[0]
    times = I.sample_times(clip, step=1)
    assert times == [0, 1, 2, 3, 4, 4.5]
