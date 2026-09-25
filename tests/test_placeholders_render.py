import unittest

from privacyguard.placeholders import PlaceholderAllocator, PlaceholderCatalog
from privacyguard.render import RenderFinding, render


class PlaceholderRenderTests(unittest.TestCase):
    def setUp(self):
        self.catalog = PlaceholderCatalog(
            {"PERSON_NAME": "PERSONA", "EMAIL": "EMAIL", "LOCATION_CITY": "LOCALIDAD"},
            "1.0",
        )

    def test_same_entity_reuses_index(self):
        allocator = PlaceholderAllocator(self.catalog)
        self.assertEqual(allocator.allocate("PERSON_NAME", "Ana Pérez"), "[PERSONA_1]")
        self.assertEqual(allocator.allocate("PERSON_NAME", " ana   pérez "), "[PERSONA_1]")
        self.assertEqual(allocator.allocate("PERSON_NAME", "Luis Pérez"), "[PERSONA_2]")

    def test_render_uses_original_text_and_neutral_placeholders(self):
        allocator = PlaceholderAllocator(self.catalog)
        text = "Ana Pérez, Ana Pérez"
        result = render(
            text,
            [
                RenderFinding(0, 9, "PERSON_NAME", "REDACT"),
                RenderFinding(11, 20, "PERSON_NAME", "REDACT"),
            ],
            allocator,
        )
        self.assertEqual(result, "[PERSONA_1], [PERSONA_1]")
        self.assertNotIn("Ana", result)

    def test_generalize_uses_callback(self):
        allocator = PlaceholderAllocator(self.catalog)
        result = render(
            "Madrid",
            [RenderFinding(0, 6, "LOCATION_CITY", "GENERALIZE")],
            allocator,
            generalize=lambda label, value: "Madrid Comunidad",
        )
        self.assertEqual(result, "Madrid Comunidad")

    def test_unknown_generalization_fails_closed_to_placeholder(self):
        allocator = PlaceholderAllocator(self.catalog)
        result = render(
            "Madrid",
            [RenderFinding(0, 6, "LOCATION_CITY", "GENERALIZE")],
            allocator,
            generalize=lambda label, value: None,
        )
        self.assertEqual(result, "[LOCALIDAD_1]")


if __name__ == "__main__":
    unittest.main()
