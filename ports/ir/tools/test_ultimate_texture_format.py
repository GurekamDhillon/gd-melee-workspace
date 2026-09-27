#!/usr/bin/env python3
"""Offline format decisions for Ultimate costume textures."""
import unittest
from unittest import mock

from PIL import Image

import export_ultimate_mesh as EM


def pixels(*alphas):
    return bytes(channel for alpha in alphas for channel in (40, 80, 120, alpha))


class TextureFormatTest(unittest.TestCase):
    def setUp(self):
        if not hasattr(EM, "auto_texture_format"):
            self.fail("exporter has no auto texture format policy")

    def test_opaque_and_nearly_opaque_pixels_use_cmpr(self):
        self.assertEqual(EM.auto_texture_format(pixels(255, 254, 252)), "CMPR")

    def test_binary_alpha_uses_cmpr(self):
        self.assertEqual(EM.auto_texture_format(pixels(0, 255, 0, 255)), "CMPR")

    def test_small_smooth_edge_uses_rgb5a3(self):
        self.assertEqual(EM.auto_texture_format(pixels(0, 32, 128, 255, 255, 255)), "RGB5A3")

    def test_broad_smooth_gradient_keeps_rgba8(self):
        self.assertEqual(EM.auto_texture_format(pixels(0, 32, 64, 96, 128, 159)), "RGBA8")

    def test_texture_export_only_changes_format_when_opted_in(self):
        def decode_to_png(args, **_):
            Image.frombytes("RGBA", (2, 2), pixels(0, 64, 255, 255)).save(args[2])

        with mock.patch.object(EM.subprocess, "run", side_effect=decode_to_png):
            legacy = EM.texture("fixture.nutexb", 256)
            automatic = EM.texture("fixture.nutexb", 256, "auto")
        self.assertEqual(legacy["fmt"], "RGBA8")
        self.assertEqual(automatic["fmt"], "RGB5A3")
        self.assertEqual(automatic["alpha_intermediate_pixels"], 1)
        self.assertEqual(legacy["rgba"], automatic["rgba"])


if __name__ == "__main__":
    unittest.main()
