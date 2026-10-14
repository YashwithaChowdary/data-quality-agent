"""Data quality checks. Each check returns a list of Issue objects.

An Issue says what kind of problem it is, which column, which rows (by
DataFrame index) and a one-line detail. Nothing here guesses a cause; that
is done separately in root_cause.py.
"""
from dataclasses import dataclass, asdict

import pandas as pd

PLACEHOLDERS = {"", "n/a", "na", "null", "none", "unknown", "-", "?"}


@dataclass
class Issue:
    check: str      # missing | duplicate | type | rule
    column: str
    rows: list
    detail: str

    def to_dict(self):
        return asdict(self)


def _is_blank(value):
    return pd.isna(value) or str(value).strip().lower() in {"", "nan"}


def check_missing(df, required):
    """Rows where a required column is empty."""
    issues = []
    for col in required:
        rows = [i for i, v in df[col].items() if _is_blank(v)]
        if rows:
            issues.append(Issue("missing", col, rows,
                                f"{len(rows)} empty value(s) in required column"))
    return issues


def check_duplicates(df, key):
    """Rows that repeat an earlier key. Reports whether they are exact copies."""
    dup = df[df.duplicated(subset=key, keep="first")]
    if dup.empty:
        return []
    exact = df.duplicated(keep="first").loc[dup.index]
    name = ", ".join(key)
    detail = (f"{len(dup)} row(s) repeat an earlier {name}; "
              f"{int(exact.sum())} are exact copies of the whole row")
    return [Issue("duplicate", name, list(dup.index), detail)]


def _fits(value, kind):
    if _is_blank(value):
        return True            # emptiness is reported by check_missing
    text = str(value).strip()
    if kind == "int":
        return text.lstrip("-").isdigit()
    if kind == "float":
        try:
            float(text)
            return True
        except ValueError:
            return False
    if kind == "date":
        return pd.notna(pd.to_datetime(text, format="%Y-%m-%d", errors="coerce"))
    return True                # "str" accepts anything


def check_types(df, schema):
    """schema maps column -> 'int' | 'float' | 'date' (ISO yyyy-mm-dd) | 'str'."""
    issues = []
    for col, kind in schema.items():
        bad = [i for i, v in df[col].items() if not _fits(v, kind)]
        if bad:
            examples = sorted({str(df.at[i, col]) for i in bad})[:3]
            issues.append(Issue("type", col, bad,
                                f"{len(bad)} value(s) are not {kind}, e.g. {examples}"))
    return issues


def check_rules(df, rules):
    """Each rule: {'name', 'column', 'violates': fn(df) -> boolean Series}."""
    issues = []
    for rule in rules:
        mask = rule["violates"](df).fillna(False)
        rows = list(df.index[mask])
        if rows:
            issues.append(Issue("rule", rule["column"], rows,
                                f"{len(rows)} row(s) break rule: {rule['name']}"))
    return issues


def validate(df, schema, required, key, rules):
    return (check_missing(df, required) + check_duplicates(df, key)
            + check_types(df, schema) + check_rules(df, rules))
