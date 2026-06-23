#!/usr/bin/env python3
"""Download public prior-research PDF/code listed in metadata.yaml."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import ssl
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree


USER_AGENT = "IdeaDiscoveryWorkspace/0.1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_simple_metadata(metadata_path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if not metadata_path.exists():
        raise SystemExit(f"metadata.yamlが見つかりません: {metadata_path}")

    for line in metadata_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open("a", encoding="utf-8") as file:
            file.write(text)
    else:
        path.write_text(text, encoding="utf-8")


def append_fetch_log(item_dir: Path, messages: list[str]) -> None:
    notes_path = item_dir / "idea_notes.md"
    if notes_path.exists():
        existing = notes_path.read_text(encoding="utf-8")
        has_log_heading = "## 取得・変換ログ" in existing or "## Intake / Ingest Log" in existing
        heading = "" if has_log_heading else "\n## 取得・変換ログ\n"
    else:
        heading = "# アイデアメモ\n\n## 取得・変換ログ\n"

    entry = f"\n- {utc_now()}: `{item_dir.name}`の公開PDF/source取得を実行した\n"
    entry += "".join(f"  - {message}\n" for message in messages)
    append_text(notes_path, heading + entry)


def looks_sensitive_url(url: str) -> bool:
    lowered = url.lower()
    return (
        "@" in url
        or "token=" in lowered
        or "access_token=" in lowered
        or "apikey=" in lowered
        or "api_key=" in lowered
        or "private" in lowered
    )


def is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_likely_pdf(data: bytes, content_type: str) -> bool:
    head = data[:1024].lower()
    if data.startswith(b"%PDF"):
        return True
    if "pdf" in content_type.lower() and b"<html" not in head:
        return True
    return False


def download_pdf(pdf_url: str, destination: Path, force: bool) -> str:
    if not pdf_url:
        return "pdf_urlが空のためPDF取得をスキップした"
    if looks_sensitive_url(pdf_url):
        return "pdf_urlに認証情報・token・privateを示す文字列があるためPDF取得を停止した"
    if not is_http_url(pdf_url):
        return f"pdf_urlがHTTP(S)ではないためPDF取得をスキップした: {pdf_url}"
    if destination.exists() and not force:
        return f"既存のpaper.pdfを保持した: {destination}"

    request = urllib.request.Request(pdf_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
            final_url = response.geturl()
    except urllib.error.HTTPError as error:
        if error.code in {401, 403, 407, 429}:
            return f"PDF取得を停止した: HTTP {error.code}。認証、rate limit、またはアクセス制限の可能性がある"
        return f"PDF取得に失敗した: HTTP {error.code}"
    except urllib.error.URLError as error:
        if isinstance(error.reason, ssl.SSLCertVerificationError):
            curl_result = download_pdf_with_curl(pdf_url)
            if isinstance(curl_result, str):
                return curl_result
            data = curl_result
            content_type = ""
            final_url = pdf_url
        else:
            return f"PDF取得に失敗した: {error}"
    except Exception as error:  # noqa: BLE001
        return f"PDF取得に失敗した: {error}"

    if looks_sensitive_url(final_url):
        return "redirect先URLに認証情報・token・privateを示す文字列があるためPDF保存を停止した"
    if not is_likely_pdf(data, content_type):
        return "PDFではない応答の可能性があるため保存しなかった。HTML、login、paywall、landing pageの可能性がある"

    destination.write_bytes(data)
    return f"PDFを取得した: {destination}"


def download_pdf_with_curl(pdf_url: str) -> bytes | str:
    executable = shutil.which("curl")
    if executable is None:
        return "PythonのTLS証明書検証に失敗し、curlも見つからないためPDF取得に失敗した"

    command = [
        executable,
        "-L",
        "--fail",
        "--silent",
        "--show-error",
        "--max-time",
        "45",
        "-A",
        USER_AGENT,
        pdf_url,
    ]
    completed = subprocess.run(command, capture_output=True, check=False)
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        return f"PythonのTLS証明書検証に失敗し、curlでのPDF取得にも失敗した: {message}"
    return completed.stdout


def clone_public_code(code_url: str, destination: Path, force: bool) -> str:
    if not code_url:
        return "code_urlが空のためsource取得をスキップした"
    if looks_sensitive_url(code_url):
        return "code_urlに認証情報・token・privateを示す文字列があるためsource取得を停止した"
    if not is_http_url(code_url):
        return f"code_urlがHTTP(S)ではないためsource取得をスキップした: {code_url}"
    if destination.exists() and any(destination.iterdir()) and not force:
        return f"既存のsource/を保持した: {destination}"
    if destination.exists() and force:
        shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = ["git", "clone", "--depth", "1", code_url, str(destination)]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
    except FileNotFoundError:
        return "gitコマンドが見つからないためsource取得に失敗した"

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        return f"source取得に失敗した: {message}"

    return f"sourceを取得した: {destination}"


def download_prior_research(item_dir: Path, force: bool, pdf_only: bool, code_only: bool) -> list[str]:
    metadata = read_simple_metadata(item_dir / "metadata.yaml")
    pdf_url = metadata.get("pdf_url", "")
    paper_url = metadata.get("paper_url", "")
    code_url = metadata.get("code_url", "")

    messages: list[str] = []
    if not code_only:
        pdf_message = download_pdf(pdf_url, item_dir / "paper.pdf", force)
        messages.append(pdf_message)
        if not (item_dir / "paper.pdf").exists():
            messages.append(download_pmc_markdown(paper_url or pdf_url, item_dir / "paper.md", force))
    if not pdf_only:
        messages.append(clone_public_code(code_url, item_dir / "source", force))

    append_fetch_log(item_dir, messages)
    return messages


def extract_pmcid(url_or_text: str) -> str:
    match = re.search(r"PMC\d+", url_or_text, flags=re.IGNORECASE)
    return match.group(0).upper() if match else ""


def download_pmc_markdown(paper_url: str, destination: Path, force: bool) -> str:
    pmcid = extract_pmcid(paper_url)
    if not pmcid:
        return "PMCIDが見つからないためPMC XMLからのpaper.md作成をスキップした"
    if destination.exists() and not force:
        return f"既存のpaper.mdを保持した: {destination}"

    xml_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pmc&id={pmcid}&retmode=xml"
    )
    request = urllib.request.Request(xml_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
    except Exception as error:  # noqa: BLE001
        return f"PMC XMLからのpaper.md作成に失敗した: {error}"

    head = data[:512].lower()
    if b"<html" in head or b"recaptcha" in head:
        return "PMC XMLではない応答の可能性があるためpaper.mdを作成しなかった"

    try:
        markdown = pmc_xml_to_markdown(data, pmcid)
    except Exception as error:  # noqa: BLE001
        return f"PMC XMLのMarkdown変換に失敗した: {error}"

    destination.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return f"PMC XMLからpaper.mdを作成した: {destination}"


def clean_inline_text(text: str) -> str:
    return " ".join(text.split())


def element_text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    return clean_inline_text("".join(element.itertext()))


def pmc_xml_to_markdown(data: bytes, pmcid: str) -> str:
    root = ElementTree.fromstring(data)
    title = element_text(root.find(".//article-title")) or pmcid
    doi = element_text(root.find(".//article-id[@pub-id-type='doi']"))
    pmid = element_text(root.find(".//article-id[@pub-id-type='pmid']"))
    abstract = element_text(root.find(".//abstract"))

    lines = [
        f"<!-- PMC XMLから{utc_now()}に変換 -->",
        "",
        f"# {title}",
        "",
        f"- PMCID: {pmcid}",
    ]
    if pmid:
        lines.append(f"- PMID: {pmid}")
    if doi:
        lines.append(f"- DOI: {doi}")

    if abstract:
        lines.extend(["", "## Abstract", "", textwrap.fill(abstract, width=100)])

    body = root.find(".//body")
    if body is not None:
        lines.extend(["", "## Body"])
        for section in body.iter("sec"):
            heading = element_text(section.find("title"))
            if heading:
                lines.extend(["", f"### {heading}"])
            for paragraph in section.findall("p"):
                text = element_text(paragraph)
                if text:
                    lines.extend(["", textwrap.fill(text, width=100)])

        if not any(line.startswith("### ") for line in lines):
            for paragraph in body.findall(".//p"):
                text = element_text(paragraph)
                if text:
                    lines.extend(["", textwrap.fill(text, width=100)])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item_dir", help="Path such as prior_research/paper_a.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing paper.pdf or source/.")
    parser.add_argument("--pdf-only", action="store_true", help="Only download paper.pdf.")
    parser.add_argument("--code-only", action="store_true", help="Only clone source/.")
    args = parser.parse_args()

    if args.pdf_only and args.code_only:
        parser.error("--pdf-only and --code-only cannot be used together")

    item_dir = Path(args.item_dir).expanduser().resolve()
    if not item_dir.exists():
        parser.error(f"item_dirが存在しません: {item_dir}")
    if not item_dir.is_dir():
        parser.error(f"item_dirはディレクトリではありません: {item_dir}")

    messages = download_prior_research(item_dir, args.force, args.pdf_only, args.code_only)
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
