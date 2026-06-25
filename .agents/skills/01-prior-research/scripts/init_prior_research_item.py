#!/usr/bin/env python3
"""Create a prior_research item folder."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


METADATA_TEMPLATE = """title: ""
authors: []
year: ""
doi: ""
pmid: ""
pmcid: ""
paper_url: ""
pdf_url: ""
code_url: ""
local_pdf: "paper.pdf"
local_paper_markdown: "paper.md"
local_source_dir: "source/"
local_source_markdown: "source.md"
license_note: ""
access_note: ""
ingested_at: ""
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def idea_notes_template(name: str) -> str:
    return f"""# アイデアメモ

## この論文が行ったこと

## 未解決の点

## 弱点・限界

## 再利用できるデータ・コード

## 発展アイデア

## こちらの関心との関係

## 仮説候補

## 取得・変換ログ

- {utc_now()}: `prior_research/{name}/`を初期化した。
"""


def valid_slug(value: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    return bool(value) and all(character in allowed for character in value)


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"既存ファイルを保持: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return f"作成: {path}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Folder name under prior_research/, such as paper_a.")
    parser.add_argument(
        "--root",
        default=".",
        help="Workspace root. Defaults to the current directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing metadata and idea notes.",
    )
    args = parser.parse_args()

    if not valid_slug(args.name):
        parser.error("name must contain only letters, numbers, underscores, or hyphens")

    root = Path(args.root).expanduser().resolve()
    item_dir = root / "prior_research" / args.name
    item_dir.mkdir(parents=True, exist_ok=True)

    messages = [
        write_file(item_dir / "metadata.yaml", METADATA_TEMPLATE, args.force),
        write_file(item_dir / "idea_notes.md", idea_notes_template(args.name), args.force),
    ]

    print(f"先行研究アイテムを作成: {item_dir}")
    for message in messages:
        print(message)
    print(f"作成日時: {utc_now()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
