import unittest

from privacyguard.normalize import normalize


class NormalizeTests(unittest.TestCase):
    def test_nfc_and_non_breaking_space_keep_original_offsets(self):
        result = normalize("A\u0301\u00a0B")
        self.assertEqual(result.text, "Á B")
        self.assertEqual(result.original_span(0, 1), (0, 2))

    def test_email_spacing_is_removed(self):
        result = normalize("Contacto: juan.perez @ empresa . com")
        self.assertEqual(result.text, "Contacto: juan.perez@empresa.com")
        start = result.text.index("juan")
        end = start + len("juan.perez@empresa.com")
        original_start, original_end = result.original_span(start, end)
        self.assertEqual(original_start, 10)
        self.assertEqual(original_end, len("Contacto: juan.perez @ empresa . com"))

    def test_line_break_hyphen_is_removed(self):
        result = normalize("mejo-\nra")
        self.assertEqual(result.text, "mejora")
        self.assertEqual(result.original_span(3, 5), (3, 7))

    def test_regular_hyphen_is_preserved(self):
        result = normalize("alta-calidad")
        self.assertEqual(result.text, "alta-calidad")

    def test_empty_text_has_empty_map(self):
        result = normalize("")
        self.assertEqual(result.text, "")
        self.assertEqual(result.offsets, ())


if __name__ == "__main__":
    unittest.main()
