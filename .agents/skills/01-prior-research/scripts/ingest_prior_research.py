#!/usr/bin/env python3
"""Convert a prior_research item into Markdown artifacts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


MAX_SOURCE_FILE_BYTES = 100 * 1024
IGNORED_DIR_NAMES = {".git", "__pycache__", ".ipynb_checkpoints"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_bytes(size: int) -> str:
    return f"{size / 1024:.1f}KB"


def write_text(path: Path, text: str, force: bool) -> str:
    if path.exists() and not force:
        return f"既存ファイルを保持: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return f"作成: {path}"


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open("a", encoding="utf-8") as file:
            file.write(text)
    else:
        path.write_text(text, encoding="utf-8")


def update_metadata_value(metadata_path: Path, key: str, value: str) -> str:
    line = f'{key}: "{value}"'

    if not metadata_path.exists():
        metadata_path.write_text(line + "\n", encoding="utf-8")
        return f"metadata.yamlを作成し、{key}を設定した"

    lines = metadata_path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    replaced = False

    for existing_line in lines:
        if existing_line.startswith(f"{key}:"):
            updated.append(line)
            replaced = True
        else:
            updated.append(existing_line)

    if not replaced:
        updated.append(line)

    metadata_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return f"metadata.yamlの{key}を更新した"


def append_ingest_log(item_dir: Path, messages: list[str]) -> None:
    notes_path = item_dir / "idea_notes.md"
    if notes_path.exists():
        existing = notes_path.read_text(encoding="utf-8")
        has_log_heading = "## 取得・変換ログ" in existing or "## Intake / Ingest Log" in existing
        heading = "" if has_log_heading else "\n## 取得・変換ログ\n"
    else:
        heading = "# アイデアメモ\n\n## 取得・変換ログ\n"

    entry = f"\n- {utc_now()}: `{item_dir.name}`のingestを実行した\n"
    entry += "".join(f"  - {message}\n" for message in messages)
    append_text(notes_path, heading + entry)


def ingest_pdf(item_dir: Path, force: bool) -> str:
    pdf_path = item_dir / "paper.pdf"
    out_path = item_dir / "paper.md"
    if not pdf_path.exists():
        return f"paper.pdfが存在しないためPDF変換をスキップした: {pdf_path}"
    if out_path.exists() and not force:
        return f"既存のpaper.mdを保持した: {out_path}"

    try:
        markdown = pdf_to_markdown(pdf_path)
    except ImportError:
        return "pymupdf4llm/PyMuPDFが未導入のためPDF変換をスキップした。paper.mdを手動作成してもよい"
    except Exception as error:  # noqa: BLE001
        return f"PDF変換をスキップした: {error}"

    header = f"<!-- paper.pdfから{utc_now()}に変換 -->\n\n"
    return write_text(out_path, header + markdown, force=True)


def pdf_to_markdown(pdf_path: Path) -> str:
    try:
        import pymupdf4llm  # type: ignore[import-not-found]
    except ImportError:
        return pdf_to_markdown_with_pymupdf(pdf_path)

    return pymupdf4llm.to_markdown(str(pdf_path))


def pdf_to_markdown_with_pymupdf(pdf_path: Path) -> str:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as error:
        raise ImportError from error

    sections: list[str] = [f"# {pdf_path.parent.name}"]
    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                sections.append(f"## Page {index}\n\n{text}")

    return "\n\n".join(sections)


def should_skip_source_path(path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def prepare_small_source_tree(source_dir: Path, filtered_dir: Path) -> tuple[int, list[str]]:
    copied_count = 0
    skipped_messages: list[str] = []

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(source_dir)
        if should_skip_source_path(relative_path):
            continue

        file_size = path.stat().st_size
        if file_size > MAX_SOURCE_FILE_BYTES:
            skipped_messages.append(
                f"source/{relative_path}は{format_bytes(file_size)}で100KBを超えるためスキップした"
            )
            continue

        destination = filtered_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied_count += 1

    return copied_count, skipped_messages


def format_gitingest_result(result: object) -> str:
    if isinstance(result, tuple):
        if len(result) == 3:
            summary, tree, content = result
            return (
                "# ソースコードダイジェスト\n\n"
                f"## Summary\n\n{summary}\n\n"
                f"## ディレクトリ構造\n\n```text\n{tree}\n```\n\n"
                f"## 内容\n\n{content}"
            )
        return "\n\n".join(str(part) for part in result)
    return str(result)


def ingest_source_with_python_api(source_dir: Path) -> str | None:
    try:
        from gitingest import ingest  # type: ignore[import-not-found]
    except ImportError:
        return None

    result = ingest(str(source_dir))
    return format_gitingest_result(result)


def ingest_source_with_cli(source_dir: Path) -> str | None:
    executable = shutil.which("gitingest")
    if executable is None:
        return None

    with tempfile.TemporaryDirectory(prefix="idea_discovery_gitingest_") as temp_dir:
        out_path = Path(temp_dir) / "source.md"
        commands = [
            [executable, str(source_dir), "-o", str(out_path)],
            [executable, str(source_dir), "--output", str(out_path)],
        ]
        for command in commands:
            completed = subprocess.run(command, text=True, capture_output=True, check=False)
            if completed.returncode == 0 and out_path.exists():
                return out_path.read_text(encoding="utf-8")
    return None


def ingest_source(item_dir: Path, force: bool) -> list[str]:
    source_dir = item_dir / "source"
    out_path = item_dir / "source.md"
    if not source_dir.exists():
        return [f"sourceディレクトリが存在しないためコード変換をスキップした: {source_dir}"]
    if out_path.exists() and not force:
        return [f"既存のsource.mdを保持した: {out_path}"]

    with tempfile.TemporaryDirectory(prefix="idea_discovery_source_") as temp_dir:
        filtered_dir = Path(temp_dir) / "source"
        copied_count, skipped_messages = prepare_small_source_tree(source_dir, filtered_dir)

        if copied_count == 0:
            messages = ["100KB以下のsourceファイルが見つからないためコード変換をスキップした"]
            messages.extend(skipped_messages)
            return messages

        try:
            markdown = ingest_source_with_python_api(filtered_dir)
        except Exception as error:  # noqa: BLE001
            messages = [f"Python APIでのコード変換をスキップした: {error}"]
            messages.extend(skipped_messages)
            return messages

        if markdown is None:
            try:
                markdown = ingest_source_with_cli(filtered_dir)
            except Exception as error:  # noqa: BLE001
                messages = [f"CLIでのコード変換をスキップした: {error}"]
                messages.extend(skipped_messages)
                return messages

    if markdown is None:
        messages = ["gitingestが未導入のためコード変換をスキップした。source.mdを手動作成してもよい"]
        messages.extend(skipped_messages)
        return messages

    header = (
        f"<!-- source/から{utc_now()}に変換 -->\n"
        f"<!-- 対象ファイル数: {copied_count}; 1ファイル上限: 100KB -->\n\n"
    )
    messages = [write_text(out_path, header + markdown, force=True)]
    messages.extend(skipped_messages)
    return messages


def ingest_prior_research(item_dir: Path, force: bool) -> list[str]:
    messages = [ingest_pdf(item_dir, force)]
    messages.extend(ingest_source(item_dir, force))
    messages.append(update_metadata_value(item_dir / "metadata.yaml", "ingested_at", utc_now()))
    append_ingest_log(item_dir, messages)
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item_dir", help="Path such as prior_research/paper_a.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing paper.md or source.md.",
    )
    args = parser.parse_args()

    item_dir = Path(args.item_dir).expanduser().resolve()
    if not item_dir.exists():
        parser.error(f"item_dirが存在しません: {item_dir}")
    if not item_dir.is_dir():
        parser.error(f"item_dirはディレクトリではありません: {item_dir}")

    messages = ingest_prior_research(item_dir, args.force)
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
