"""cases.yaml を操作する小さなCLI。

  python scripts/cases.py next                     # status: todo の先頭の id を出力（なければ何も出力しない）
  python scripts/cases.py list --status published  # 指定 status の id を1行ずつ出力
  python scripts/cases.py show <id>                # 案件の中身を表示
"""
from __future__ import annotations

import argparse
import sys

from common import find_case, load_cases


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("next")
    lp = sub.add_parser("list")
    lp.add_argument("--status", required=True)
    sp = sub.add_parser("show")
    sp.add_argument("id")
    a = p.parse_args()

    data = load_cases()
    if a.cmd == "next":
        for c in data["cases"]:
            if c.get("status") == "todo":
                print(c["id"])
                return
    elif a.cmd == "list":
        for c in data["cases"]:
            if c.get("status") == a.status:
                print(c["id"])
    elif a.cmd == "show":
        c = find_case(data, a.id)
        for k, v in c.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
