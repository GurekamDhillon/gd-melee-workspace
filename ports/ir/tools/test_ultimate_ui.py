#!/usr/bin/env python3
"""Offline checks for the Ultimate UI resize and GX palette conversion."""
import unittest

from PIL import Image, ImageDraw

import ultimate_ui as UI


class UltimateUiArtTest(unittest.TestCase):
    def test_stock_resize_and_ci4_quantise_preserve_shape_and_colour(self):
        source = Image.new("RGBA", (64, 64))
        draw = ImageDraw.Draw(source)
        draw.ellipse((12, 6, 51, 57), fill=(235, 55, 28, 255))
        draw.ellipse((27, 20, 36, 29), fill=(30, 100, 240, 255))

        fitted = UI.fit_art(source, (24, 24), inset=1)
        pixels, palette, entries = UI.encode_art(fitted, UI.G.GX_TF_C4)
        decoded = UI.G.decode(pixels, UI.G.GX_TF_C4, 24, 24, palette)

        self.assertEqual((len(pixels), len(palette), entries), (288, 32, 16))
        self.assertEqual(decoded.getpixel((0, 0))[3], 0)
        self.assertGreater(decoded.getpixel((12, 12))[3], 200)
        self.assertGreater(decoded.getpixel((12, 12))[0], 150)

    def test_csp_costumes_keep_distinct_shapes_and_palettes(self):
        portraits = []
        for colour, shape in (((235, 40, 35), "rectangle"),
                              ((35, 80, 235), "ellipse")):
            im = Image.new("RGBA", (80, 80))
            getattr(ImageDraw.Draw(im), shape)((5, 5, 74, 74), fill=(*colour, 255))
            portraits.append(UI.portrait_art(im, (136, 188)))
        costumes = UI.encode_csp_costumes(portraits)
        red = UI.G.decode(costumes[0][0], UI.G.GX_TF_C8, 136, 188, costumes[0][1])
        blue = UI.G.decode(costumes[1][0], UI.G.GX_TF_C8, 136, 188, costumes[1][1])

        self.assertEqual([len(pixels) for pixels, _ in costumes],
                         [UI.G.size_of(UI.G.GX_TF_C8, 136, 188)] * 2)
        self.assertEqual([len(palette) for _, palette in costumes], [512, 512])
        self.assertGreater(red.getpixel((68, 100))[0], red.getpixel((68, 100))[2])
        self.assertGreater(blue.getpixel((68, 100))[2], blue.getpixel((68, 100))[0])
        self.assertGreater(red.getpixel((5, 5))[3], blue.getpixel((5, 5))[3])


if __name__ == "__main__":
    unittest.main()
