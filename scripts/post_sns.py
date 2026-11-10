"""公開済み記事の告知を Threads（と任意で X）に投稿する。

  python scripts/post_sns.py <id> [--dry-run]

環境変数:
  THREADS_ACCESS_TOKEN   Threads の長期アクセストークン（必須）
  X_ENABLED=true         X にも投稿する場合のみ
  X_INCLUDE_LINK=true    X の投稿にリンクを入れる場合のみ（1件あたりの料金が高くなる）
  X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET   X を使う場合
  X_API_BASE             既定 https://api.x.com

二重投稿を防ぐため、各SNSの投稿IDを cases.yaml に記録し、記録済みのSNSはスキップする。
"""
from __future__ import annotations

import argparse
import sys
import time
import unicodedata

import requests

from common import article_dir, env, find_case, load_cases, load_yaml_file, now_jst, save_cases

THREADS_API = "https://graph.threads.net/v1.0"


def x_length(text: str) -> int:
    """X の文字数（全角=2, 半角=1 として数え、140字=280）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WFA" else 1 for ch in text)


def post_threads(text: str) -> str:
    token = env("THREADS_ACCESS_TOKEN")
    r = requests.post(f"{THREADS_API}/me/threads",
                      data={"media_type": "TEXT", "text": text, "access_token": token}, timeout=60)
    if not r.ok:
        sys.exit(f"Threads コンテナ作成に失敗: HTTP {r.status_code} {r.text[:300]}")
    creation_id = r.json()["id"]
    time.sleep(5)  # 公式ドキュメントは公開前に少し待つことを推奨
    r = requests.post(f"{THREADS_API}/me/threads_publish",
                      data={"creation_id": creation_id, "access_token": token}, timeout=60)
    if not r.ok:
        sys.exit(f"Threads 公開に失敗: HTTP {r.status_code} {r.text[:300]}")
    return r.json()["id"]


def post_x(text: str) -> str:
    from requests_oauthlib import OAuth1

    auth = OAuth1(env("X_API_KEY"), env("X_API_SECRET"), env("X_ACCESS_TOKEN"), env("X_ACCESS_SECRET"))
    base = env("X_API_BASE", required=False, default="https://api.x.com")
    r = requests.post(f"{base}/2/tweets", json={"text": text}, auth=auth, timeout=60)
    if not r.ok:
        sys.exit(f"X への投稿に失敗: HTTP {r.status_code} {r.text[:300]}")
    return r.json()["data"]["id"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("id")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    data = load_cases()
    case = find_case(data, a.id)
    if case.get("status") != "published":
        sys.exit(f"[{a.id}] status が published ではありません（{case.get('status')}）")
    url = case.get("public_url") or ""
    sns_path = article_dir(a.id) / "sns.yaml"
    if not sns_path.exists():
        sys.exit(f"{sns_path} がありません")
    sns = load_yaml_file(sns_path) or {}

    posted = case.get("sns") or {}

    # --- Threads ---
    threads_text = (sns.get("threads") or "").strip().replace("{URL}", url)
    if not threads_text:
        sys.exit("sns.yaml に threads がありません")
    if len(threads_text) > 500:
        sys.exit(f"Threads の文面が500文字を超えています（{len(threads_text)}文字）")
    if "#PR" not in threads_text:
        sys.exit("Threads の文面に #PR がありません")
    if posted.get("threads_id"):
        print("Threads は投稿済みなのでスキップ")
    elif a.dry_run:
        print(f"[dry-run] Threads:\n{threads_text}\n")
    else:
        posted["threads_id"] = post_threads(threads_text)
        case["sns"] = posted
        save_cases(data)  # 1件ごとに保存（途中で失敗しても二重投稿しない）
        print(f"Threads に投稿しました: {posted['threads_id']}")

    # --- X（任意）---
    if env("X_ENABLED", required=False, default="false").lower() == "true":
        x_text = (sns.get("x") or "").strip()
        include_link = env("X_INCLUDE_LINK", required=False, default="false").lower() == "true"
        if "http" in x_text or ("{URL}" in x_text and not include_link):
            sys.exit("X の文面にリンクが含まれています（X_INCLUDE_LINK=true でない限り不可。料金対策）")
        x_text = x_text.replace("{URL}", url)
        if x_length(x_text) > 280:
            sys.exit(f"X の文面が長すぎます（{x_length(x_text)}/280）")
        if posted.get("x_id"):
            print("X は投稿済みなのでスキップ")
        elif a.dry_run:
            print(f"[dry-run] X:\n{x_text}\n")
        else:
            posted["x_id"] = post_x(x_text)
            case["sns"] = posted
            save_cases(data)
            print(f"X に投稿しました: {posted['x_id']}")

    if not a.dry_run:
        case["status"] = "sns_posted"
        case["sns_posted_at"] = now_jst()
        save_cases(data)


if __name__ == "__main__":
    main()
