import unittest

from privacyguard.schemas import (
    SchemaError,
    validate_error_response,
    validate_minimize_request,
    validate_minimize_response,
)


class RequestSchemaTests(unittest.TestCase):
    def test_accepts_minimize_request(self):
        result = validate_minimize_request(
            {
                "request_id": "req-1",
                "document_ref": "doc-1",
                "text": "Texto sintético",
                "policy_id": "cv_scoring",
                "mode": "enforce",
            }
        )
        self.assertEqual(result["policy_id"], "cv_scoring")

    def test_rejects_unknown_field_without_echoing_value(self):
        with self.assertRaises(SchemaError) as raised:
            validate_minimize_request(
                {
                    "request_id": "req-1",
                    "document_ref": "doc-1",
                    "text": "dato-sintetico",
                    "policy_id": "cv_scoring",
                    "unexpected": "dato-sintetico",
                }
            )
        self.assertNotIn("dato-sintetico", str(raised.exception))

    def test_rejects_oversized_text(self):
        with self.assertRaises(SchemaError) as raised:
            validate_minimize_request(
                {
                    "request_id": "req-1",
                    "document_ref": "doc-1",
                    "text": "x",
                    "policy_id": "cv_scoring",
                },
                max_text_bytes=0,
            )
        self.assertEqual(raised.exception.code, "text_too_large")


class ResponseSchemaTests(unittest.TestCase):
    def test_offsets_are_not_checked_against_sanitized_text(self):
        result = validate_minimize_response(
            {
                "request_id": "req-1",
                "status": "OK",
                "sanitized_text": "[EMAIL_1]",
                "detections": [
                    {
                        "index": 0,
                        "label": "EMAIL",
                        "start": 120,
                        "end": 140,
                        "action": "REDACT",
                        "placeholder": "[EMAIL_1]",
                        "confidence": 1.0,
                        "risk": "HIGH",
                        "source": "RULE",
                        "reason": "STRUCTURED_IDENTIFIER",
                    }
                ],
                "review_items": [],
                "stats": {},
                "versions": {
                    "service": "1.0.0",
                    "rules": "1.0",
                    "policy": "cv_scoring@1.0",
                    "preprocessing": "1.0",
                    "placeholders": "1.0",
                    "llm_model": None,
                    "prompt_version": None,
                    "llm_endpoint_id": None,
                },
                "timing_ms": 1,
            }
        )
        self.assertEqual(result["detections"][0]["start"], 120)

    def test_review_status_must_match_review_items(self):
        response = {
            "request_id": "req-1",
            "status": "OK",
            "sanitized_text": "",
            "detections": [],
            "review_items": [
                {
                    "index": 0,
                    "start": 0,
                    "end": 1,
                    "label": "PERSON_NAME",
                    "confidence": 0.4,
                    "reason": "UNCERTAIN",
                    "provisional_action": "REDACT",
                    "options": ["REDACT", "KEEP"],
                }
            ],
            "stats": {},
            "versions": {
                "service": "1.0.0",
                "rules": "1.0",
                "policy": "cv_scoring@1.0",
                "preprocessing": "1.0",
                "placeholders": "1.0",
                "llm_model": None,
                "prompt_version": None,
                "llm_endpoint_id": None,
            },
            "timing_ms": 1,
        }
        with self.assertRaises(SchemaError) as raised:
            validate_minimize_response(response)
        self.assertEqual(raised.exception.code, "status_inconsistent")


class ErrorSchemaTests(unittest.TestCase):
    def test_error_shape(self):
        result = validate_error_response(
            {"error_code": "INVALID_REQUEST", "message": "Petición inválida", "request_id": "req-1"}
        )
        self.assertEqual(result["error_code"], "INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()
