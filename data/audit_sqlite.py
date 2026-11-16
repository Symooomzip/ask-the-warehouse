"""Phase 0 audit: how much of the public text-to-SQL data really runs in SQLite?

For every example the `sql_context` (CREATE TABLE and INSERT statements) is
loaded into a fresh in-memory SQLite database and the gold `sql` is executed.
This measures two things the dataset card does not tell us:
  - dialect compatibility with the engine we can run in a browser, and
  - label quality (queries that error even on their own schema).

    python data/audit_sqlite.py data/raw/gretel_train.parquet [--n 20000]
"""
from __future__ import annotations

import argparse
import collections
import re
import sqlite3

import pandas as pd


def run_example(context: str, sql: str) -> tuple[str, str]:
    """Return (status, detail). status in ok, empty, error."""
    con = sqlite3.connect(":memory:")
    try:
        try:
            con.executescript(context)
        except sqlite3.Error as e:
            return "context_error", str(e)[:80]
        try:
            rows = con.execute(sql).fetchall()
        except sqlite3.Error as e:
            return "error", str(e)[:80]
        return ("ok" if rows else "empty"), ""
    finally:
        con.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("parquet")
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    df = pd.read_parquet(args.parquet)
    sample = df.sample(n=min(args.n, len(df)), random_state=args.seed)

    status = collections.Counter()
    reasons = collections.Counter()
    by_complexity = collections.defaultdict(collections.Counter)
    non_select = 0
    for row in sample.itertuples():
        s, detail = run_example(row.sql_context, row.sql)
        status[s] += 1
        by_complexity[row.sql_complexity][s] += 1
        if s in ("error", "context_error"):
            # group error messages by shape: strip identifiers and quoted bits
            reasons[re.sub(r"'[^']*'|\"[^\"]*\"|\b\w+\.\w+\b", "_", detail)] += 1
        if not row.sql.lstrip().lower().startswith(("select", "with")):
            non_select += 1

    n = len(sample)
    print(f"examples audited: {n}")
    for k, v in status.most_common():
        print(f"  {k:14s} {v:6d}  {100 * v / n:5.1f}%")
    print(f"  not a SELECT/WITH statement: {non_select} ({100 * non_select / n:.1f}%)")
    print("\nby complexity (share executing without error, ok + empty):")
    for c, cnt in sorted(by_complexity.items(), key=lambda kv: -sum(kv[1].values())):
        tot = sum(cnt.values())
        good = cnt["ok"] + cnt["empty"]
        print(f"  {c:18s} n={tot:6d}  runs={100 * good / tot:5.1f}%  empty={100 * cnt['empty'] / tot:5.1f}%")
    print("\ntop error shapes:")
    for r, v in reasons.most_common(10):
        print(f"  {v:5d}  {r}")


if __name__ == "__main__":
    main()
