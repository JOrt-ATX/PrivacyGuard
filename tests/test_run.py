import unittest
from pathlib import Path

import run


class RunTests(unittest.TestCase):
    def test_build_pipeline_uses_versioned_data(self):
        pipeline = run.build_pipeline(Path(__file__).parents[1])
        self.assertEqual(pipeline.policy.policy_id, "cv_scoring")
        self.assertEqual(pipeline.catalog.version, "1.0")


if __name__ == "__main__":
    unittest.main()
