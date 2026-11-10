"""status: hatena_draft の記事が、はてなで「公開」されたかを確認する。

  python scripts/check_published.py

公開されていれば status を published にし、公開URLを保存する。
（あなたがスマホで公開ボタンを押したことを、ここで検知する）
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

import requests

from common import env, load_cases, now_jst, save_cases

NS = {"atom": "http://www.w3.org/2005/Atom", "app": "http://www.w3.org/2007/app"}


def main() -> None:
    data = load_cases()
    targets = [c for c in data["cases"] if c.get("status") == "hatena_draft"]
    if not targets:
        print("確認対象の下書きはありません")
        return

    auth = (env("HATENA_ID"), env("HATENA_API_KEY"))
    changed = False
    for c in targets:
        url = c.get("hatena_edit_url")
        if not url:
            print(f"[{c['id']}] hatena_edit_url がないのでスキップ", file=sys.stderr)
            continue
        r = requests.get(url, auth=auth, timeout=60)
        if r.status_code == 404:
            c["status"] = "hatena_missing"
            changed = True
            print(f"[{c['id']}] はてな側で記事が見つかりません（削除された？）→ hatena_missing")
            continue
        r.raise_for_status()
        root = ET.fromstring(r.content)
        draft = root.findtext("app:control/app:draft", default="no", namespaces=NS).strip()
        if draft == "no":
            alt = root.find("atom:link[@rel='alternate']", NS)
            c["status"] = "published"
            c["public_url"] = alt.get("href") if alt is not None else ""
            c["published_at"] = now_jst()
            changed = True
            print(f"[{c['id']}] 公開を検知しました: {c['public_url']}")
        else:
            print(f"[{c['id']}] まだ下書きです")

    if changed:
        save_cases(data)


if __name__ == "__main__":
    main()
