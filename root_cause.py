"""Root-cause hypotheses for the issues found by checks.py.

These are hypotheses with the evidence that supports them, never facts.
The rule-based part runs offline. explain_with_llm() optionally asks a
model to turn the same evidence into a short explanation for a person.
"""
import json

from checks import PLACEHOLDERS


def _share_of_top(values):
    counts = values.value_counts()
    return counts.index[0], counts.iloc[0] / len(values)


def _missing(df, issue, group_col):
    rows = issue.rows
    if group_col and len(rows) >= 3:
        top, share = _share_of_top(df.loc[rows, group_col])
        if share >= 0.8:
            return (f"Missing '{issue.column}' clusters in {group_col}='{top}' "
                    f"({share:.0%} of the {len(rows)} rows). That source may not "
                    f"send this field.",
                    f"{group_col}='{top}' holds {share:.0%} of the empty rows")
    return (f"Missing '{issue.column}' is scattered across the data, so it looks "
            f"like random omission at entry rather than one broken source.",
            "no single group holds most of the empty rows")


def _duplicate(df, issue):
    exact = df.duplicated(keep="first").loc[issue.rows].all()
    if exact:
        return ("Whole rows repeat exactly, which usually means the same record "
                "was loaded or submitted twice.",
                "every repeated row equals an earlier row in all columns")
    return ("The key repeats but other values differ, so a record may have been "
            "re-sent with changes. Decide which version is current.",
            "repeated keys have different values elsewhere")


def _type(df, issue):
    values = {str(df.at[i, issue.column]).strip() for i in issue.rows}
    found = sorted(v for v in values if v.lower() in PLACEHOLDERS)
    if found:
        return (f"'{issue.column}' contains placeholder text such as {found}. "
                f"The source probably writes text where a value is unknown.",
                f"placeholder values found: {found[:3]}")
    return (f"'{issue.column}' mixes formats, e.g. {sorted(values)[:3]}. Two "
            f"sources or entry screens may use different formats.",
            f"non-conforming examples: {sorted(values)[:3]}")


def _rule(df, issue):
    return (f"Rule violations in '{issue.column}' may be genuine exceptions or "
            f"entry errors. Check with the data owner before correcting.",
            f"{len(issue.rows)} row(s) violate the rule")


def hypothesize(df, issues, group_col=None):
    out = []
    for issue in issues:
        if issue.check == "missing":
            text, evidence = _missing(df, issue, group_col)
        elif issue.check == "duplicate":
            text, evidence = _duplicate(df, issue)
        elif issue.check == "type":
            text, evidence = _type(df, issue)
        else:
            text, evidence = _rule(df, issue)
        out.append({"check": issue.check, "column": issue.column,
                    "rows": issue.rows, "hypothesis": text,
                    "evidence": evidence})
    return out


def explain_with_llm(findings, llm):
    """Ask a model to summarise the findings. The reply is a suggestion only."""
    prompt = ("You are helping a data engineer. Below are data quality findings "
              "with rule-based hypotheses. For each, say in one or two plain "
              "sentences what is most likely wrong and the first thing to check. "
              "Label every cause as a hypothesis. Do not invent facts.\n\n"
              + json.dumps([{k: f[k] for k in ("check", "column", "hypothesis",
                                               "evidence")} for f in findings],
                           indent=2))
    return llm(prompt)
