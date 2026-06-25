#!/usr/bin/env python3
"""Convert a prior_research item into Markdown artifacts."""

from __future__ import annotations

import argparse
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


MAX_SOURCE_FILE_BYTES = 100 * 1024
PDF_IMAGE_DIR_NAME = "figures"
DIRECT_PYTHON_OVERRIDE_ENV = "IDEA_DISCOVERY_ALLOW_DIRECT_PYTHON"
SCRIPT_RELATIVE_PATH = ".agents/skills/01-prior-research/scripts/ingest_prior_research.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def running_under_uv() -> bool:
    return bool(os.environ.get("UV_RUN_RECURSION_DEPTH"))


def require_uv_run(script_relative_path: str) -> None:
    if os.environ.get(DIRECT_PYTHON_OVERRIDE_ENV) == "1":
        return
    if running_under_uv():
        return

    raise SystemExit(
        "\n".join(
            [
                "このscriptはuv経由で実行してください。",
                f"例: uv run python {script_relative_path} <prior_research_dir>",
                "`python ...`や`python3 ...`の直呼びは、.venv外のPythonを使い依存不足を起こすため停止しました。",
                f"一時的に直呼びを許可する場合だけ、{DIRECT_PYTHON_OVERRIDE_ENV}=1を明示してください。",
            ]
        )
    )


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


def read_metadata_value(metadata_path: Path, key: str) -> str:
    if not metadata_path.exists():
        return ""
    for line in metadata_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        existing_key, value = line.split(":", 1)
        if existing_key.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


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


@contextmanager
def working_directory(path: Path):
    previous_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous_cwd)


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
        return "pymupdf4llmが未導入のためPDF変換をスキップした。別方式のfallbackは追加せず、人間に導入または手動作成を確認する"
    except Exception as error:  # noqa: BLE001
        return f"PDF変換をスキップした: {error}"

    header = f"<!-- paper.pdfから{utc_now()}に変換 -->\n\n"
    write_message = write_text(out_path, header + markdown, force=True)
    return f"{write_message}; PDF内画像の保存先: {PDF_IMAGE_DIR_NAME}/"


def pdf_to_markdown(pdf_path: Path) -> str:
    import pymupdf4llm  # type: ignore[import-not-found]

    image_dir = pdf_path.parent / PDF_IMAGE_DIR_NAME
    image_dir.mkdir(parents=True, exist_ok=True)
    with working_directory(pdf_path.parent):
        return pymupdf4llm.to_markdown(
            pdf_path.name,
            write_images=True,
            image_path=PDF_IMAGE_DIR_NAME,
            image_format="png",
            dpi=200,
        )


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


def ingest_source_with_python_api(source: str) -> str | None:
    try:
        from gitingest import ingest  # type: ignore[import-not-found]
    except ImportError:
        return None

    result = ingest(source, max_file_size=MAX_SOURCE_FILE_BYTES)
    return format_gitingest_result(result)


def source_markdown_header(source_label: str) -> str:
    return (
        f"<!-- {source_label}から{utc_now()}にgitingestで変換 -->\n"
        f"<!-- gitingest max_file_size: 100KB; source code本体は保存しない -->\n\n"
    )


def write_source_markdown(out_path: Path, markdown: str, source_label: str) -> str:
    return write_text(out_path, source_markdown_header(source_label) + markdown, force=True)


def looks_sensitive_source(value: str) -> bool:
    lowered = value.lower()
    return (
        "@" in value
        or "token=" in lowered
        or "access_token=" in lowered
        or "apikey=" in lowered
        or "api_key=" in lowered
        or "private" in lowered
    )


def is_http_url(value: str) -> bool:
    return value.startswith("https://") or value.startswith("http://")


def ingest_source_url(item_dir: Path, code_url: str, force: bool) -> list[str]:
    out_path = item_dir / "source.md"
    if not code_url:
        return ["code_urlが空のためsource.md作成をスキップした"]
    if looks_sensitive_source(code_url):
        return ["code_urlに認証情報・token・privateを示す文字列があるためsource.md作成を停止した"]
    if not is_http_url(code_url):
        return [f"code_urlがHTTP(S)ではないためsource.md作成をスキップした: {code_url}"]
    if out_path.exists() and not force:
        return [f"既存のsource.mdを保持した: {out_path}"]

    try:
        markdown = ingest_source_with_python_api(code_url)
    except Exception as error:  # noqa: BLE001
        return [f"gitingest Python APIでのcode_url変換をスキップした: {error}"]

    if markdown is None:
        return ["gitingestが未導入のためcode_url変換をスキップした。別方式のfallbackは追加せず、人間に導入または手動作成を確認する"]

    return [write_source_markdown(out_path, markdown, code_url)]


def ingest_source(item_dir: Path, force: bool) -> list[str]:
    source_dir = item_dir / "source"
    out_path = item_dir / "source.md"
    if not source_dir.exists():
        return [f"sourceディレクトリが存在しないためローカルsource変換をスキップした: {source_dir}"]
    if out_path.exists() and not force:
        return [f"既存のsource.mdを保持した: {out_path}"]

    try:
        markdown = ingest_source_with_python_api(str(source_dir))
    except Exception as error:  # noqa: BLE001
        return [f"gitingest Python APIでのローカルsource変換をスキップした: {error}"]

    if markdown is None:
        return ["gitingestが未導入のためローカルsource変換をスキップした。別方式のfallbackは追加せず、人間に導入または手動作成を確認する"]

    return [write_source_markdown(out_path, markdown, "source/")]


def ingest_prior_research(
    item_dir: Path,
    force: bool,
    pdf_only: bool = False,
    source_only: bool = False,
    source_url: str = "",
) -> list[str]:
    if pdf_only and source_only:
        raise ValueError("pdf_only and source_only cannot both be true")

    messages: list[str] = []
    if not source_only:
        messages.append(ingest_pdf(item_dir, force))
    if not pdf_only:
        if not source_url:
            source_url = read_metadata_value(item_dir / "metadata.yaml", "code_url")
        if source_url:
            messages.extend(ingest_source_url(item_dir, source_url, force))
        else:
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
    parser.add_argument("--pdf-only", action="store_true", help="Only convert paper.pdf to paper.md.")
    parser.add_argument("--source-only", action="store_true", help="Only create source.md from metadata code_url or local source/.")
    args = parser.parse_args()

    if args.pdf_only and args.source_only:
        parser.error("--pdf-only and --source-only cannot be used together")
    require_uv_run(SCRIPT_RELATIVE_PATH)

    item_dir = Path(args.item_dir).expanduser().resolve()
    if not item_dir.exists():
        parser.error(f"item_dirが存在しません: {item_dir}")
    if not item_dir.is_dir():
        parser.error(f"item_dirはディレクトリではありません: {item_dir}")

    messages = ingest_prior_research(item_dir, args.force, args.pdf_only, args.source_only)
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
