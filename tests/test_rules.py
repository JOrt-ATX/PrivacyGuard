import unittest

from privacyguard.rules import detect


class RulesTests(unittest.TestCase):
    def test_detects_reference_identifiers_without_rewriting(self):
        text = (
            "juan.perez@example.com | +34 612 345 678 | DNI 12345678Z | "
            "ES91 2100 0418 4502 0005 1332 | https://example.com | CP: 28001 | "
            "Nacido el 10 de julio de 1990"
        )
        detections = detect(text)
        self.assertEqual(
            [item.label for item in detections],
            ["EMAIL", "PHONE", "DNI_NIE", "IBAN", "URL", "POSTAL_CODE", "DATE_FULL"],
        )
        self.assertEqual(text[detections[0].start:detections[0].end], "juan.perez@example.com")

    def test_preserves_month_year_ranges_and_bare_years(self):
        text = "Quality Manager, 03/2020 - 07/2024. Graduado en 2015."
        self.assertEqual(detect(text), [])

    def test_email_split_by_layout_is_detected_after_normalization(self):
        from privacyguard.normalize import normalize

        normalized = normalize("juan.perez @ empresa . com")
        detections = detect(normalized.text)
        self.assertEqual(len(detections), 1)
        self.assertEqual(normalized.text[detections[0].start:detections[0].end], "juan.perez@empresa.com")

    def test_postal_range_and_six_digits(self):
        self.assertEqual([d.label for d in detect("28001 Madrid")], ["POSTAL_CODE"])
        self.assertEqual(detect("99999 987654"), [])

    def test_iso_exception_can_be_enabled(self):
        self.assertEqual([d.label for d in detect("ISO 14001")], ["POSTAL_CODE"])
        self.assertEqual(detect("ISO 14001", exclude_standard_numbers=True), [])


if __name__ == "__main__":
    unittest.main()
