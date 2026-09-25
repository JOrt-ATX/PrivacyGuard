import tempfile
import unittest
from pathlib import Path

from privacyguard.config import load_settings


class ConfigTests(unittest.TestCase):
    def test_loads_toml_and_environment_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                'host = "127.0.0.1"\n'
                'port = 8090\n'
                'tls_cert = ""\n'
                'tls_key = ""\n'
                'llm_base_url = "https://llm.internal/v1"\n'
                'llm_model = "synthetic-model"\n'
                'llm_ca_file = ""\n'
                'llm_timeout_s = 30.0\n'
                'llm_seed = 1\n'
                'max_concurrency = 4\n'
                'max_text_bytes = 204800\n'
                'diagnostic_mode = false\n'
                '[consumer_tokens]\n'
                'aicrew = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n',
                encoding="utf-8",
            )
            settings = load_settings(path, environ={"PRIVACYGUARD_LLM_API_KEY": "outside-repo"})
        self.assertEqual(settings.llm_api_key, "outside-repo")
        self.assertEqual(len(settings.llm_endpoint_id), 16)

    def test_non_loopback_requires_tls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                'host = "10.0.0.2"\nport = 8090\n'
                'llm_base_url = "https://llm.internal/v1"\nllm_model = "m"\n'
                'llm_timeout_s = 1\nllm_seed = 1\nmax_concurrency = 1\n'
                'max_text_bytes = 1\ndiagnostic_mode = false\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "tls_required"):
                load_settings(path)


if __name__ == "__main__":
    unittest.main()
