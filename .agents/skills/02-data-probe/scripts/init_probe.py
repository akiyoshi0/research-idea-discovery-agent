#!/usr/bin/env python3
"""Create a lightweight data-probe folder."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


PROBE_TEMPLATE = """# プローブ

## 問い

## 関連する仮説

## データソース

## 方法

## 結果

## 解釈

## 仮説を支持するか

High / Medium / Low

## 仮説を弱めるか

High / Medium / Low

## 次のアクション
"""


SCRIPT_TEMPLATE = '''#!/usr/bin/env python3
"""Lightweight data probe.

Keep this script small. It should check data availability, basic structure, or a simple trend.
It should not become a publication-grade analysis pipeline.
"""

from __future__ import annotations


def main() -> int:
    print("このplaceholderを軽量なデータ確認コードに置き換えてください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


RUN_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail

python script.py
"""


def valid_slug(value: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    return bool(value) and all(character in allowed for character in value)


def write_file(path: Path, content: str, force: bool, executable: bool = False) -> str:
    if path.exists() and not force:
        return f"既存ファイルを保持: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    if executable:
        current_mode = path.stat().st_mode
        os.chmod(path, current_mode | 0o111)
    return f"作成: {path}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "name",
        help="Folder name under probes/, such as probe_001_gene_expression_check.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Workspace root. Defaults to the current directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing probe files.",
    )
    args = parser.parse_args()

    if not valid_slug(args.name):
        parser.error("name must contain only letters, numbers, underscores, or hyphens")

    root = Path(args.root).expanduser().resolve()
    probe_dir = root / "probes" / args.name
    outputs_dir = probe_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    messages = [
        write_file(probe_dir / "probe.md", PROBE_TEMPLATE, args.force),
        write_file(probe_dir / "script.py", SCRIPT_TEMPLATE, args.force, executable=True),
        write_file(probe_dir / "run.sh", RUN_TEMPLATE, args.force, executable=True),
    ]

    print(f"プローブを作成: {probe_dir}")
    print(f"outputsディレクトリを作成: {outputs_dir}")
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
