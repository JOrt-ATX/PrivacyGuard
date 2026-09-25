import unittest
from pathlib import Path

from privacyguard.pipeline import Pipeline


ROOT = Path(__file__).parents[1]


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = Pipeline.from_files(
            policy_path=ROOT / "data/policies/cv_scoring/1.0.json",
            placeholders_path=ROOT / "data/placeholders/1.0.json",
            labels_path=ROOT / "data/labels/1.0.json",
            generalization_path=ROOT / "data/generalization/municipio_provincia/1.0.json",
        )

    def test_minimizes_structured_identifiers_and_preserves_offsets(self):
        response = self.pipeline.minimize(
            {
                "request_id": "req-1",
                "document_ref": "doc-1",
                "text": "Contacto: ana@example.com. Trabajo en Airbus.",
                "policy_id": "cv_scoring",
                "policy_version": "1.0",
            }
        )
        self.assertEqual(response["sanitized_text"], "Contacto: [EMAIL_1]. Trabajo en Airbus.")
        self.assertEqual(response["detections"][0]["start"], 10)
        self.assertEqual(response["detections"][0]["end"], 25)
        self.assertIsNone(response["versions"]["llm_model"])

    def test_dry_run_does_not_return_sanitized_text(self):
        response = self.pipeline.minimize(
            {
                "request_id": "req-2",
                "document_ref": "doc-2",
                "text": "ana@example.com",
                "policy_id": "cv_scoring",
                "mode": "dry_run",
            }
        )
        self.assertIsNone(response["sanitized_text"])
        self.assertEqual(response["stats"]["by_action"]["REDACT"], 1)

    def test_deterministic_serializable_result(self):
        request = {
            "request_id": "req-3",
            "document_ref": "doc-3",
            "text": "ana@example.com y ana@example.com",
            "policy_id": "cv_scoring",
        }
        first = self.pipeline.minimize(request)
        second = self.pipeline.minimize(request)
        self.assertEqual(first, second)
        self.assertEqual(first["sanitized_text"], "[EMAIL_1] y [EMAIL_1]")


if __name__ == "__main__":
    unittest.main()
