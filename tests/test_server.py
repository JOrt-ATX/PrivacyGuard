import hashlib
import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from privacyguard.config import Settings
from privacyguard.pipeline import Pipeline
from privacyguard.server import create_server


ROOT = Path(__file__).parents[1]


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = Pipeline.from_files(
            policy_path=ROOT / "data/policies/cv_scoring/1.0.json",
            placeholders_path=ROOT / "data/placeholders/1.0.json",
            labels_path=ROOT / "data/labels/1.0.json",
        )

    def setUp(self):
        token = "synthetic-token"
        self.settings = Settings(
            "127.0.0.1", 0, None, None, "https://llm/v1", "m", None,
            1, 1, 2, 204800, False,
            {"test": hashlib.sha256(token.encode()).hexdigest()}, None,
        )
        self.logs = io.StringIO()
        self.server = create_server(self.settings, self.pipeline, log_stream=self.logs)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_address[1])
        self.token = token

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _request(self, method, path, body=None, auth=True):
        headers = {}
        if auth:
            headers["Authorization"] = "Bearer " + self.token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(data))
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_minimize_requires_auth_before_body(self):
        status, result = self._request(
            "POST", "/v1/minimize",
            {"request_id": "r", "document_ref": "d", "text": "secret", "policy_id": "cv_scoring"},
            auth=False,
        )
        self.assertEqual(status, 401)
        self.assertNotIn("secret", json.dumps(result))

    def test_minimize_and_health(self):
        status, result = self._request(
            "POST", "/v1/minimize",
            {"request_id": "r", "document_ref": "d", "text": "a@x.com", "policy_id": "cv_scoring"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["sanitized_text"], "[EMAIL_1]")
        status, result = self._request("GET", "/v1/health", auth=False)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "ok")

    def test_body_limit(self):
        status, result = self._request(
            "POST", "/v1/minimize",
            {"request_id": "r", "document_ref": "d", "text": "x", "policy_id": "cv_scoring"},
        )
        self.assertEqual(status, 200)
        self.assertNotIn("a@x.com", self.logs.getvalue())

    def test_configured_text_limit_returns_413(self):
        self.server.settings = Settings(
            "127.0.0.1", 0, None, None, "https://llm/v1", "m", None,
            1, 1, 2, 3, False,
            {"test": hashlib.sha256(self.token.encode()).hexdigest()}, None,
        )
        status, result = self._request(
            "POST", "/v1/minimize",
            {"request_id": "r", "document_ref": "d", "text": "four", "policy_id": "cv_scoring"},
        )
        self.assertEqual(status, 413)
        self.assertEqual(result["error_code"], "TEXT_TOO_LARGE")


if __name__ == "__main__":
    unittest.main()
