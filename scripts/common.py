"""共通処理：cases.yaml の読み書き、パス、環境変数。"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = ROOT / "cases.yaml"
ARTICLES_DIR = ROOT / "articles"
JST = timezone(timedelta(hours=9))

_yaml = YAML()  # コメントを保持したまま読み書きする
_yaml.preserve_quotes = True
_yaml.width = 4096
_yaml.indent(mapping=2, sequence=4, offset=2)  # 手で書いたときと同じインデントを保つ


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def load_cases():
    with CASES_FILE.open(encoding="utf-8") as f:
        data = _yaml.load(f)
    if not data or "cases" not in data:
        sys.exit("cases.yaml に cases: がありません")
    return data


def save_cases(data) -> None:
    with CASES_FILE.open("w", encoding="utf-8") as f:
        _yaml.dump(data, f)


def find_case(data, case_id: str):
    for c in data["cases"]:
        if c.get("id") == case_id:
            return c
    sys.exit(f"cases.yaml に id: {case_id} が見つかりません")


def article_dir(case_id: str) -> Path:
    return ARTICLES_DIR / case_id


def load_yaml_file(path: Path):
    with path.open(encoding="utf-8") as f:
        return YAML(typ="safe").load(f)


def env(name: str, required: bool = True, default: str | None = None) -> str | None:
    val = os.environ.get(name, default)
    if required and not val:
        sys.exit(f"環境変数 {name} が設定されていません")
    return val
