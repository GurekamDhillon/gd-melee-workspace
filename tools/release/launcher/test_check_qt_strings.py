import os, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import check_qt_strings as C

BS = chr(92)


class Pairs(unittest.TestCase):
    def run_on(self, src):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "w.cpp"), "w", encoding="utf-8") as f:
            f.write(src)
        return C.scan(d)

    def test_finds_pairs_and_counts_untranslated(self):
        r = self.run_on('t("PLAY", "JUGAR"); t("Copy", "Copy"); t("Name", "Nombre");')
        self.assertEqual(r["pairs"], 3); self.assertEqual(r["untranslated"], ["Copy"]); self.assertEqual(r["problems"], [])

    def test_same_english_two_translations_is_a_problem(self):
        r = self.run_on('t("Open", "Abrir"); t("Open", "Abre");')
        self.assertTrue(any("Open" in p for p in r["problems"]))

    def test_same_english_same_translation_is_fine(self):
        r = self.run_on('t("Open", "Abrir"); t("Open", "Abrir");')
        self.assertEqual(r["problems"], [])

    def test_placeholders_must_agree(self):
        r = self.run_on('t("Found %1 discs", "Encontrados discos");')
        self.assertTrue(r["problems"])

    def test_empty_english_is_a_problem(self):
        self.assertTrue(self.run_on('t("", "x");')["problems"])

    def test_escapes_are_kept_as_written(self):
        r = self.run_on('t("Line one' + BS + 'nLine two", "Una' + BS + 'nDos"); t("Say ' + BS + '"hi' + BS + '"", "Di ' + BS + '"hola' + BS + '""); t("Mods", "Mods");')
        self.assertEqual(r["pairs"], 3); self.assertEqual(r["problems"], [])

    def test_method_calls_named_t_are_not_pairs(self):
        r = self.run_on('x.t("a", "b"); y->t("a", "c"); int t = 1; auto s = QString::fromUtf8(t);')
        self.assertEqual(r["pairs"], 0)

    def test_the_real_sources_have_no_problem(self):
        r = C.scan(os.path.join(HERE, "qt"))
        self.assertEqual(r["problems"], []); self.assertGreater(r["pairs"], 50)


if __name__ == "__main__":
    unittest.main()
