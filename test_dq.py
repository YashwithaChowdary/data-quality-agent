import unittest

import pandas as pd

from checks import check_duplicates, check_missing, check_rules, check_types, validate
from root_cause import explain_with_llm, hypothesize
from sample_data import KEY, REQUIRED, RULES, SCHEMA, make_orders


class CheckTests(unittest.TestCase):
    def test_missing_finds_blank_and_nan(self):
        df = pd.DataFrame({"a": ["x", "", None, "y"]})
        self.assertEqual(check_missing(df, ["a"])[0].rows, [1, 2])

    def test_duplicates_report_exact_copies(self):
        df = pd.DataFrame({"id": [1, 2, 1], "v": ["a", "b", "a"]})
        issue = check_duplicates(df, ["id"])[0]
        self.assertEqual(issue.rows, [2])
        self.assertIn("1 are exact copies", issue.detail)

    def test_types_flag_text_in_number_column(self):
        df = pd.DataFrame({"amount": ["10.5", "N/A", "7"]})
        issue = check_types(df, {"amount": "float"})[0]
        self.assertEqual(issue.rows, [1])

    def test_blank_is_not_a_type_error(self):
        df = pd.DataFrame({"amount": ["10", ""]})
        self.assertEqual(check_types(df, {"amount": "float"}), [])

    def test_rule_violation(self):
        df = pd.DataFrame({"q": [1, 0, 3]})
        rule = {"name": "q>=1", "column": "q", "violates": lambda d: d["q"] < 1}
        self.assertEqual(check_rules(df, [rule])[0].rows, [1])


class SampleDataTests(unittest.TestCase):
    def setUp(self):
        self.df = make_orders()
        self.issues = validate(self.df, SCHEMA, REQUIRED, KEY, RULES)

    def test_every_kind_of_issue_is_found(self):
        kinds = {i.check for i in self.issues}
        self.assertEqual(kinds, {"missing", "duplicate", "type", "rule"})

    def test_missing_customer_id_points_at_app_source(self):
        findings = hypothesize(self.df, self.issues, group_col="source")
        miss = [f for f in findings if f["check"] == "missing"][0]
        self.assertIn("source='app'", miss["hypothesis"])

    def test_placeholder_text_is_recognised(self):
        findings = hypothesize(self.df, self.issues, group_col="source")
        typ = [f for f in findings if f["check"] == "type" and f["column"] == "amount"][0]
        self.assertIn("placeholder", typ["hypothesis"])

    def test_placeholder_match_ignores_case(self):
        findings = hypothesize(self.df, self.issues, group_col="source")
        typ = [f for f in findings if f["check"] == "type" and f["column"] == "amount"][0]
        self.assertIn("N/A", typ["hypothesis"])
        self.assertIn("unknown", typ["hypothesis"])

    def test_duplicates_are_exact_copies(self):
        findings = hypothesize(self.df, self.issues, group_col="source")
        dup = [f for f in findings if f["check"] == "duplicate"][0]
        self.assertIn("exactly", dup["hypothesis"])

    def test_llm_explanation_uses_findings_only(self):
        findings = hypothesize(self.df, self.issues, group_col="source")
        seen = {}
        explain_with_llm(findings, lambda p: seen.setdefault("p", p) or "ok")
        self.assertIn("hypothesis", seen["p"])
        self.assertNotIn("C201", seen["p"])    # no raw customer data is sent


if __name__ == "__main__":
    unittest.main()
