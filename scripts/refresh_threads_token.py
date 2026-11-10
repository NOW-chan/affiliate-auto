"""Threads の長期アクセストークン（有効期限60日）を更新し、新しいトークンだけを標準出力に出す。

  python scripts/refresh_threads_token.py

ワークフロー refresh-threads-token.yml が月1回実行し、GitHub Secrets を上書きする。
トークンの発行から24時間以上経っていて、期限が切れる前でないと更新できない点に注意。
"""
from __future__ import annotations

import sys

import requests

from common import env


def main() -> None:
    r = requests.get(
        "https://graph.threads.net/refresh_access_token",
        params={"grant_type": "th_refresh_token", "access_token": env("THREADS_ACCESS_TOKEN")},
        timeout=60,
    )
    if not r.ok:
        sys.exit(f"トークン更新に失敗: HTTP {r.status_code} {r.text[:300]}")
    j = r.json()
    print(j["access_token"])
    print(f"新しいトークンの有効期限: 約{int(j.get('expires_in', 0)) // 86400}日", file=sys.stderr)


if __name__ == "__main__":
    main()
