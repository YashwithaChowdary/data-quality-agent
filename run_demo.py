"""Run all checks on the sample orders table and write a report.

    py run_demo.py            offline, rule-based hypotheses only
    py run_demo.py --llm      also asks a model for a plain-language explanation
"""
import sys

from checks import validate
from llm_client import ask_llm
from report import to_json, to_markdown
from root_cause import explain_with_llm, hypothesize
from sample_data import KEY, REQUIRED, RULES, SCHEMA, make_orders


def main(use_llm=False):
    df = make_orders()
    issues = validate(df, SCHEMA, REQUIRED, KEY, RULES)
    findings = hypothesize(df, issues, group_col="source")
    llm_text = explain_with_llm(findings, ask_llm) if use_llm else None
    text = to_markdown(df, findings, llm_text)
    print(text)
    open("report.md", "w", encoding="utf-8").write(text)
    open("report.json", "w", encoding="utf-8").write(to_json(findings))
    print("Saved report.md and report.json")


if __name__ == "__main__":
    main("--llm" in sys.argv)
