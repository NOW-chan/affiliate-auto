"""検証済みの記事を、はてなブログに「下書き」として投稿する。

  python scripts/post_hatena.py <id> [--dry-run]

必要な環境変数: HATENA_ID, HATENA_BLOG_DOMAIN, HATENA_API_KEY
成功すると cases.yaml の status を hatena_draft にし、編集用URLを保存する。
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import requests

from common import article_dir, env, find_case, load_cases, load_yaml_file, now_jst, save_cases

NS = {"atom": "http://www.w3.org/2005/Atom", "app": "http://www.w3.org/2007/app"}


def build_entry(title: str, html: str, categories: list[str]) -> str:
    cats = "\n".join(f'  <category term="{escape(c, {chr(34): "&quot;"})}" />' for c in categories)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">
  <title>{escape(title)}</title>
  <author><name>{escape(env("HATENA_ID", required=False, default="nowchan"))}</name></author>
  <content type="text/html">{escape(html)}</content>
{cats}
  <app:control><app:draft>yes</app:draft></app:control>
</entry>"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("id")
    p.add_argument("--dry-run", action="store_true", help="送信せず、送る内容だけ表示する")
    a = p.parse_args()

    d = article_dir(a.id)
    meta = load_yaml_file(d / "meta.yaml")
    html = (d / "article.html").read_text(encoding="utf-8")
    body = build_entry(meta["title"], html, meta.get("categories") or ["PR"])

    if a.dry_run:
        print(body[:1500] + ("\n…（省略）" if len(body) > 1500 else ""))
        print(f"\n[dry-run] {len(body)} bytes を下書き投稿する予定です")
        return

    hatena_id = env("HATENA_ID")
    url = f"https://blog.hatena.ne.jp/{hatena_id}/{env('HATENA_BLOG_DOMAIN')}/atom/entry"
    r = requests.post(
        url,
        data=body.encode("utf-8"),
        auth=(hatena_id, env("HATENA_API_KEY")),
        headers={"Content-Type": "application/xml; charset=utf-8"},
        timeout=60,
    )
    if r.status_code != 201:
        sys.exit(f"はてなへの投稿に失敗しました: HTTP {r.status_code}\n{r.text[:500]}")

    root = ET.fromstring(r.content)
    edit = root.find("atom:link[@rel='edit']", NS)
    edit_url = edit.get("href") if edit is not None else r.headers.get("Location", "")

    data = load_cases()
    case = find_case(data, a.id)
    case["status"] = "hatena_draft"
    case["hatena_edit_url"] = edit_url
    case["drafted_at"] = now_jst()
    save_cases(data)
    print(f"下書きを投稿しました: {meta['title']}\n編集URL: {edit_url}")


if __name__ == "__main__":
    main()
