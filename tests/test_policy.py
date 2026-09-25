import unittest

from privacyguard.policy import Policy, decide


def policy() -> Policy:
    return Policy.from_mapping(
        {
            "policy_id": "synthetic",
            "version": "1.0",
            "default_action": "REVIEW",
            "review": {"provisional_action": "REDACT"},
            "rules": {"EMAIL": "REDACT", "ORGANIZATION": "KEEP"},
        }
    )


class PolicyTests(unittest.TestCase):
    def test_rule_action(self):
        self.assertEqual(decide("EMAIL", policy()).action, "REDACT")

    def test_unknown_label_review_never_becomes_keep(self):
        decision = decide("UNKNOWN", policy())
        self.assertEqual(decision.action, "REDACT")
        self.assertTrue(decision.provisional)

    def test_override_is_limited_to_label_action(self):
        decision = decide("ORGANIZATION", policy(), policy_override={"ORGANIZATION": "REDACT"})
        self.assertEqual(decision.action, "REDACT")
        self.assertTrue(decision.overridden)

    def test_review_override_remains_conservative(self):
        decision = decide("ORGANIZATION", policy(), policy_override={"ORGANIZATION": "REVIEW"})
        self.assertEqual(decision.action, "REDACT")
        self.assertTrue(decision.provisional)

    def test_invalid_override_fails_closed(self):
        with self.assertRaises(ValueError):
            decide("EMAIL", policy(), policy_override={"EMAIL": "INVALID"})


if __name__ == "__main__":
    unittest.main()
