import json
import tempfile
import unittest
from pathlib import Path

from privacyguard.pipeline import Pipeline


ROOT = Path(__file__).parents[1]


class ContractPropertyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = Pipeline.from_files(
            policy_path=ROOT / "data/policies/cv_scoring/1.0.json",
            placeholders_path=ROOT / "data/placeholders/1.0.json",
            labels_path=ROOT / "data/labels/1.0.json",
        )

    def test_twenty_runs_are_identical(self):
        request = {
            "request_id": "req-deterministic",
            "document_ref": "doc-deterministic",
            "text": "Nombre sintético, contacto synthetic@example.com, 03/2020 - 07/2024",
            "policy_id": "cv_scoring",
        }
        results = [self.pipeline.minimize(request) for _ in range(20)]
        self.assertEqual(results, [results[0]] * 20)

    def test_no_literal_detected_value_in_response(self):
        secret = "synthetic.person@example.com"
        response = self.pipeline.minimize(
            {
                "request_id": "req-literal",
                "document_ref": "doc-literal",
                "text": "Email: " + secret,
                "policy_id": "cv_scoring",
            }
        )
        self.assertNotIn(secret, json.dumps(response, ensure_ascii=False))

    def test_pipeline_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as directory:
            before = sorted(Path(directory).rglob("*"))
            for index in range(5):
                self.pipeline.minimize(
                    {
                        "request_id": "req-" + str(index),
                        "document_ref": "doc-" + str(index),
                        "text": "synthetic@example.com",
                        "policy_id": "cv_scoring",
                    }
                )
            after = sorted(Path(directory).rglob("*"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
