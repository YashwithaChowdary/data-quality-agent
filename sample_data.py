"""A small, deterministic orders table with known problems built in."""
import pandas as pd

COLUMNS = ["order_id", "customer_id", "source", "order_date", "amount",
           "quantity", "country"]


def make_orders():
    rows = []
    for n in range(1, 31):
        rows.append({
            "order_id": 1000 + n,
            "customer_id": f"C{200 + n % 9}",
            "source": "web" if n % 3 else "app",
            "order_date": f"2026-09-{(n % 28) + 1:02d}",
            "amount": f"{20 + n * 3}.50",
            "quantity": 1 + n % 4,
            "country": ["SE", "NO", "DK"][n % 3],
        })
    df = pd.DataFrame(rows, columns=COLUMNS)
    # problems, chosen so each check has something to find
    for i in df.index[df["source"] == "app"]:
        df.at[i, "customer_id"] = ""                # app never sends customer_id
    df.at[4, "amount"] = "N/A"                      # placeholder in a number column
    df.at[11, "amount"] = "unknown"
    df.at[7, "amount"] = "-15.00"                   # negative amount
    df.at[19, "quantity"] = 0                       # zero quantity
    df.at[14, "order_date"] = "15/09/2026"          # different date format
    df = pd.concat([df, df.iloc[[2, 9]]], ignore_index=True)   # exact copies
    return df


SCHEMA = {"order_id": "int", "amount": "float", "quantity": "int",
          "order_date": "date"}
REQUIRED = ["order_id", "customer_id", "amount"]
KEY = ["order_id"]
RULES = [
    {"name": "amount must be positive", "column": "amount",
     "violates": lambda d: pd.to_numeric(d["amount"], errors="coerce") <= 0},
    {"name": "quantity must be at least 1", "column": "quantity",
     "violates": lambda d: pd.to_numeric(d["quantity"], errors="coerce") < 1},
]
