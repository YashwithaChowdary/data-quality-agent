import json


def to_json(findings):
    return json.dumps(findings, indent=2, default=int)


def to_markdown(df, findings, llm_text=None):
    lines = ["# Data quality report", "",
             f"Rows checked: {len(df)}. Findings: {len(findings)}.", "",
             "| Check | Column | Rows affected | Hypothesis (not a fact) | Evidence |",
             "|---|---|---|---|---|"]
    for f in findings:
        lines.append(f"| {f['check']} | {f['column']} | {len(f['rows'])} | "
                     f"{f['hypothesis']} | {f['evidence']} |")
    if llm_text:
        lines += ["", "## Model explanation (suggestion, please verify)", "",
                  llm_text.strip()]
    return "\n".join(lines) + "\n"
