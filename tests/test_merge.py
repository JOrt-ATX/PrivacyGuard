import unittest

from privacyguard.merge import Finding, merge_findings


class MergeTests(unittest.TestCase):
    def test_longest_span_wins(self):
        findings = [
            Finding(0, 8, "PERSON_NAME", "MODEL", "HIGH"),
            Finding(0, 16, "THIRD_PARTY", "MODEL", "HIGH"),
        ]
        self.assertEqual([item.label for item in merge_findings(findings)], ["THIRD_PARTY"])

    def test_rule_wins_at_equal_length(self):
        findings = [
            Finding(0, 8, "PERSON_NAME", "MODEL", "CRITICAL"),
            Finding(0, 8, "DNI_NIE", "RULE", "HIGH"),
        ]
        self.assertEqual([item.label for item in merge_findings(findings)], ["DNI_NIE"])

    def test_risk_then_label_are_stable_tiebreakers(self):
        findings = [
            Finding(0, 4, "Z_LABEL", "MODEL", "LOW"),
            Finding(0, 4, "A_LABEL", "MODEL", "HIGH"),
        ]
        self.assertEqual([item.label for item in merge_findings(findings)], ["A_LABEL"])

    def test_non_overlapping_findings_preserve_document_order(self):
        findings = [
            Finding(10, 12, "B", "RULE", "LOW"),
            Finding(0, 4, "A", "RULE", "LOW"),
        ]
        self.assertEqual([item.label for item in merge_findings(findings)], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
