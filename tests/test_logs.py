import io
import json
import unittest

from privacyguard.logs import write_event


class LogsTests(unittest.TestCase):
    def test_only_allowlisted_metadata_is_written(self):
        stream = io.StringIO()
        write_event(
            {
                "event": "minimize",
                "request_id": "req-1",
                "text": "synthetic-secret",
                "detections_total": 1,
            },
            stream=stream,
        )
        value = json.loads(stream.getvalue())
        self.assertNotIn("text", value)
        self.assertNotIn("synthetic-secret", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
