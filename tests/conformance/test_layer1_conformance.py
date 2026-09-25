import unittest
from pathlib import Path

from privacyguard.pipeline import Pipeline
from reference.aicrew import anon_layer1 as layer1


ROOT = Path(__file__).parents[2]


class Layer1ConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = Pipeline.from_files(
            policy_path=ROOT / "data/policies/cv_scoring/1.0.json",
            placeholders_path=ROOT / "data/placeholders/1.0.json",
            labels_path=ROOT / "data/labels/1.0.json",
        )

    def assert_service_covers_layer1(self, text: str) -> None:
        expected = layer1.anonymize_layer1(text)
        response = self.pipeline.minimize(
            {
                "request_id": "conformance",
                "document_ref": "synthetic",
                "text": text,
                "policy_id": "cv_scoring",
            }
        )
        self.assertEqual(layer1.anonymize_layer1(response["sanitized_text"]).total_removals, 0)
        if expected.total_removals:
            self.assertNotEqual(response["sanitized_text"], text)

    def test_reference_identifier_battery(self):
        cases = (
            "Email: juan.perez@empresa.com",
            "Email: juan.perez@\nempresa.com",
            "juan.perez @ empresa . com",
            "Tel: +34 612 345 678",
            "Tel: 912345678",
            "DNI: 12345678Z",
            "NIE: X1234567L",
            "IBAN: ES9121000418450200051332",
            "Perfil: https://www.linkedin.com/in/synthetic",
            "CP: 28001",
            "28001 Madrid",
            "Nacido el 10 de julio de 1990",
            "Fecha: 1990-07-10",
        )
        for text in cases:
            with self.subTest(text=text):
                self.assert_service_covers_layer1(text)

    def test_preserves_non_absolute_periods_and_plain_text(self):
        for text in (
            "Quality Manager, 03/2020 - 07/2024",
            "Graduado en 2015",
            "Responsable de calidad con experiencia en ISO 9001.",
        ):
            with self.subTest(text=text):
                response = self.pipeline.minimize(
                    {
                        "request_id": "conformance",
                        "document_ref": "synthetic",
                        "text": text,
                        "policy_id": "cv_scoring",
                    }
                )
                self.assertEqual(response["sanitized_text"], text)


if __name__ == "__main__":
    unittest.main()
