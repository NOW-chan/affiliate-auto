"""生成された記事が CLAUDE.md の絶対ルールを守っているか機械的に検証する。

  python scripts/validate_article.py <id>

問題があればエラー内容を出力して exit 1。
ここで落ちた記事は、はてなに投稿されない。
"""
from __future__ import annotations

import re
import sys

from common import article_dir, find_case, load_cases, load_yaml_file

PR_LINE = "【PR】本記事はアフィリエイト広告を利用しています。"
SCOPE = ".nowc-article"

# 一人称の利用体験・誇大表現・効果効能の断定（必要に応じて追加）
FORBIDDEN = [
    r"使ってみ", r"実際に使っ", r"試してみ", r"愛用", r"効果を実感", r"私も使", r"僕も使",
    r"絶対に?(稼|儲|痩|生え)", r"必ず(稼|儲|痩)", r"誰でも(簡単に)?稼", r"100\s?[%％]\s?(稼|成功|効果)",
    r"髪が生え", r"発毛", r"(が|を)治(る|す)", r"業界\s?(No\.?1|ナンバーワン|1位)",
]

ALLOWED_AT_RULES = ("@media", "@supports", "@container")


def check_css_scope(html: str) -> list[str]:
    errors = []
    for style in re.findall(r"<style[^>]*>(.*?)</style>", html, flags=re.S | re.I):
        css = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
        depth_stack: list[str] = []  # 外側のブロックの種類
        for m in re.finditer(r"([^{}]*)([{}])", css):
            head, brace = m.group(1).strip(), m.group(2)
            if brace == "}":
                if depth_stack:
                    depth_stack.pop()
                continue
            inside_keyframes = any(k == "keyframes" for k in depth_stack)
            if head.startswith("@"):
                if "keyframes" in head:
                    name = head.split()[-1] if len(head.split()) > 1 else ""
                    if not name.startswith("nowc-"):
                        errors.append(f"@keyframes 名は nowc- で始めてください: {head}")
                    depth_stack.append("keyframes")
                elif head.startswith(ALLOWED_AT_RULES):
                    depth_stack.append("at")
                else:
                    errors.append(f"使えない @ルールです: {head}")
                    depth_stack.append("at")
                continue
            depth_stack.append("rule")
            if inside_keyframes:
                continue
            for sel in head.split(","):
                sel = sel.strip()
                if sel and not sel.startswith(SCOPE):
                    errors.append(f"CSSセレクタが {SCOPE} で始まっていません: {sel}")
    return errors


def check_links(html: str, aff_link: str) -> list[str]:
    errors = []
    anchors = re.findall(r"<a\s[^>]*>", html, flags=re.I)
    aff_anchors = [a for a in anchors if "a8.net" in a or (aff_link and aff_link in a)]
    if not aff_anchors:
        errors.append("アフィリエイトリンクが1つもありません（cases.yaml の link を使ってください）")
    for a in aff_anchors:
        rel = re.search(r'rel="([^"]*)"', a)
        rel_vals = rel.group(1).split() if rel else []
        if "sponsored" not in rel_vals or "nofollow" not in rel_vals:
            errors.append(f'アフィリエイトリンクに rel="sponsored nofollow" がありません: {a[:120]}')
        if 'target="_blank"' not in a:
            errors.append(f'アフィリエイトリンクに target="_blank" がありません: {a[:120]}')
    if len(aff_anchors) > 4:
        errors.append(f"アフィリエイトリンクが多すぎます（{len(aff_anchors)}個。CTAは2〜3か所まで）")
    return errors


def validate(case_id: str) -> list[str]:
    errors: list[str] = []
    d = article_dir(case_id)
    html_path, meta_path = d / "article.html", d / "meta.yaml"
    if not html_path.exists():
        return [f"{html_path} がありません"]
    if not meta_path.exists():
        errors.append(f"{meta_path} がありません")
    else:
        meta = load_yaml_file(meta_path) or {}
        if not meta.get("title"):
            errors.append("meta.yaml に title がありません")
        if "PR" not in (meta.get("categories") or []):
            errors.append('meta.yaml の categories に "PR" を入れてください')

    html = html_path.read_text(encoding="utf-8")

    if not re.search(r'<div\s+class="nowc-article"', html):
        errors.append('全体を <div class="nowc-article"> で包んでください')
    if re.search(r"<(html|head|body)[\s>]", html, flags=re.I):
        errors.append("<html> <head> <body> は書かないでください（本文の断片にする）")

    # PR表記：本文テキストの先頭付近にあること
    pr_pos = html.find(PR_LINE)
    first_text = re.search(r">\s*([^<\s][^<]*)<", re.sub(r"<style.*?</style>", "", html, flags=re.S | re.I))
    if pr_pos == -1:
        errors.append(f"PR表記がありません: {PR_LINE}")
    elif first_text and PR_LINE not in first_text.group(1):
        errors.append("PR表記が本文の最初の要素になっていません")

    body_text = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    body_text = re.sub(r"<[^>]+>", " ", body_text)
    for pat in FORBIDDEN:
        for m in re.finditer(pat, body_text):
            ctx = body_text[max(0, m.start() - 20): m.end() + 20].replace("\n", " ")
            errors.append(f"禁止表現「{m.group(0)}」があります: …{ctx}…")

    if "NOW" not in body_text or "フリーランス" not in body_text:
        errors.append("著者プロフィール（NOW／フリーランス）がありません")

    case = find_case(load_cases(), case_id)
    errors += check_links(html, str(case.get("link", "")))
    errors += check_css_scope(html)
    return errors


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("使い方: python scripts/validate_article.py <id>")
    errors = validate(sys.argv[1])
    if errors:
        print("検証エラー:")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)
    print("OK: 検証を通過しました")


if __name__ == "__main__":
    main()
