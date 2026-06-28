#!/usr/bin/env python3
"""Download prior-research PDF and create Markdown artifacts listed in metadata.yaml."""

from __future__ import annotations

import argparse
import importlib.util
import html as html_lib
import json
import os
import re
import shutil
import subprocess
import ssl
import tarfile
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode, urljoin, urlparse


USER_AGENT = "IdeaDiscoveryWorkspace/0.1"
SEMANTIC_SCHOLAR_API_ROOT = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_FIELDS = "title,externalIds,openAccessPdf,isOpenAccess,url"
PMC_IDCONV_API_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
PMC_OA_API_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
PMC_FTP_HOST = "ftp.ncbi.nlm.nih.gov"
MAX_PMC_OA_TGZ_BYTES = 250 * 1024 * 1024
SUPPLEMENTAL_PDF_TOKENS = ("supplement", "supp", "mmc", "appendix")
DIRECT_PYTHON_OVERRIDE_ENV = "IDEA_DISCOVERY_ALLOW_DIRECT_PYTHON"
SCRIPT_RELATIVE_PATH = ".agents/skills/01-prior-research/scripts/download_prior_research.py"


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
                f"例: uv run python {script_relative_path} prior_research/<paper_id>",
                "`python ...`や`python3 ...`の直呼びは、.venv外のPythonを使い依存不足を起こすため停止しました。",
                f"一時的に直呼びを許可する場合だけ、{DIRECT_PYTHON_OVERRIDE_ENV}=1を明示してください。",
            ]
        )
    )


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


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def update_metadata_value(metadata_path: Path, key: str, value: str) -> str:
    line = f"{key}: {yaml_quote(value)}"

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


def append_metadata_note(metadata_path: Path, key: str, note: str) -> str:
    metadata = read_simple_metadata(metadata_path)
    current = metadata.get(key, "")
    if note in current:
        return f"metadata.yamlの{key}は指定した追記内容を既に含む"

    value = note if not current else f"{current}; {note}"
    return update_metadata_value(metadata_path, key, value)


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

    entry = f"\n- {utc_now()}: `{item_dir.name}`の公開PDF取得・source.md作成処理を実行した\n"
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


def is_pmc_pow_html(data: bytes) -> bool:
    head = data[:4096].decode("utf-8", errors="ignore")
    return "POW_CHALLENGE" in head or "Preparing to download" in head


def normalize_doi(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    return value.strip()


def extract_arxiv_id(*values: str) -> str:
    for value in values:
        if not value:
            continue
        patterns = [
            r"arxiv\.org/(?:abs|pdf)/([^?#\s]+)",
            r"arxiv[:.]\s*([A-Za-z0-9._/-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, value, flags=re.IGNORECASE)
            if not match:
                continue
            arxiv_id = match.group(1).strip().rstrip("/")
            arxiv_id = re.sub(r"\.pdf$", "", arxiv_id, flags=re.IGNORECASE)
            return arxiv_id
    return ""


def extract_semantic_scholar_id(*values: str) -> str:
    for value in values:
        if not value:
            continue
        if re.fullmatch(r"[a-f0-9]{40}", value.strip(), flags=re.IGNORECASE):
            return value.strip()
        if value.strip().isdigit():
            return f"CorpusId:{value.strip()}"
        match = re.search(
            r"semanticscholar\.org/paper/(?:[^/?#]+/)?([a-f0-9]{40})",
            value,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1)
    return ""


def extract_pmid(*values: str) -> str:
    for value in values:
        if not value:
            continue
        patterns = [
            r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)",
            r"(?:PMID|pmid)[:\s]+(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, value, flags=re.IGNORECASE)
            if match:
                return match.group(1)
    return ""


def normalize_pmcid(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    pmcid = extract_pmcid(value)
    if pmcid:
        return pmcid
    if value.isdigit():
        return f"PMC{value}"
    return ""


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().rstrip(".").casefold()


def semantic_scholar_headers() -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def fetch_semantic_scholar_json(url: str) -> tuple[dict[str, object] | None, str]:
    request = urllib.request.Request(url, headers=semantic_scholar_headers())
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        if error.code in {401, 403, 407, 429}:
            return None, f"Semantic Scholar取得を停止した: HTTP {error.code}。認証、rate limit、またはアクセス制限の可能性がある"
        if error.code == 404:
            return None, "Semantic Scholarに該当paperが見つからなかった: HTTP 404"
        return None, f"Semantic Scholar取得に失敗した: HTTP {error.code}"
    except Exception as error:  # noqa: BLE001
        return None, f"Semantic Scholar取得に失敗した: {error}"

    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, f"Semantic Scholar API応答をJSONとして読めなかった: {error}"

    if not isinstance(parsed, dict):
        return None, "Semantic Scholar API応答がJSON objectではないためスキップした"
    if "message" in parsed and not parsed.get("paperId") and not parsed.get("data"):
        return None, f"Semantic Scholar APIがエラーを返した: {parsed.get('message')}"
    return parsed, "Semantic Scholar API応答を取得した"


def semantic_scholar_identifiers(metadata: dict[str, str]) -> list[tuple[str, str]]:
    identifiers: list[tuple[str, str]] = []
    seen: set[str] = set()

    doi = normalize_doi(metadata.get("doi", ""))
    if doi:
        identifiers.append(("DOI", f"DOI:{doi}"))

    arxiv_id = extract_arxiv_id(
        metadata.get("doi", ""),
        metadata.get("paper_url", ""),
        metadata.get("pdf_url", ""),
    )
    if arxiv_id:
        identifiers.append(("arXiv", f"arXiv:{arxiv_id}"))

    semantic_scholar_id = extract_semantic_scholar_id(
        metadata.get("semantic_scholar_id", ""),
        metadata.get("semantic_scholar_paper_id", ""),
        metadata.get("paper_id", ""),
        metadata.get("paper_url", ""),
        metadata.get("pdf_url", ""),
    )
    if semantic_scholar_id:
        identifiers.append(("Semantic Scholar paperId", semantic_scholar_id))

    deduped: list[tuple[str, str]] = []
    for label, identifier in identifiers:
        if identifier in seen:
            continue
        seen.add(identifier)
        deduped.append((label, identifier))
    return deduped


def query_semantic_scholar_by_identifier(identifier: str) -> tuple[dict[str, object] | None, str]:
    encoded_identifier = quote(identifier, safe=":")
    url = f"{SEMANTIC_SCHOLAR_API_ROOT}/paper/{encoded_identifier}?fields={SEMANTIC_SCHOLAR_FIELDS}"
    return fetch_semantic_scholar_json(url)


def query_semantic_scholar_by_title(title: str) -> tuple[dict[str, object] | None, str]:
    normalized = normalize_title(title)
    if not normalized:
        return None, "titleが空のためSemantic Scholar title検索をスキップした"

    encoded_query = quote(title)
    url = (
        f"{SEMANTIC_SCHOLAR_API_ROOT}/paper/search"
        f"?query={encoded_query}&limit=5&fields={SEMANTIC_SCHOLAR_FIELDS}"
    )
    payload, message = fetch_semantic_scholar_json(url)
    if payload is None:
        return None, message

    data = payload.get("data")
    if not isinstance(data, list):
        return None, "Semantic Scholar title検索応答にdata配列がないためスキップした"

    for candidate in data:
        if not isinstance(candidate, dict):
            continue
        candidate_title = candidate.get("title")
        if isinstance(candidate_title, str) and normalize_title(candidate_title) == normalized:
            return candidate, f"Semantic Scholar title検索で完全一致候補を取得した: {candidate_title}"

    return None, "Semantic Scholar title検索に完全一致がないためPDF取得をスキップした"


def query_semantic_scholar(metadata: dict[str, str]) -> tuple[dict[str, object] | None, list[str]]:
    messages: list[str] = []
    for label, identifier in semantic_scholar_identifiers(metadata):
        payload, message = query_semantic_scholar_by_identifier(identifier)
        messages.append(f"{label}でSemantic Scholarを照会した: {message}")
        if payload is not None:
            title = payload.get("title")
            if isinstance(title, str) and title:
                messages.append(f"Semantic Scholar候補を取得した: {title}")
            return payload, messages

    title = metadata.get("title", "")
    if title:
        payload, message = query_semantic_scholar_by_title(title)
        messages.append(message)
        if payload is not None:
            return payload, messages

    if not messages:
        messages.append("Semantic Scholar検索に使えるDOI、arXiv ID、paperId、titleがないためスキップした")
    return None, messages


def normalize_open_access_pdf_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.endswith(".pdf") or "/pdf" in path:
        return url

    arxiv_id = extract_arxiv_id(url)
    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}"

    pmcid = extract_pmcid(url)
    if pmcid:
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/"

    return ""


def direct_pmcids_from_metadata(metadata: dict[str, str]) -> list[str]:
    values = [
        metadata.get("pmcid", ""),
        metadata.get("pmc_id", ""),
        metadata.get("paper_url", ""),
        metadata.get("pdf_url", ""),
        metadata.get("access_note", ""),
        metadata.get("license_note", ""),
    ]
    pmcids: list[str] = []
    for value in values:
        pmcid = normalize_pmcid(value)
        if pmcid and pmcid not in pmcids:
            pmcids.append(pmcid)
    return pmcids


def pmc_idconv_identifiers(metadata: dict[str, str]) -> list[str]:
    identifiers: list[str] = []

    pmid = extract_pmid(
        metadata.get("pmid", ""),
        metadata.get("pubmed_id", ""),
        metadata.get("paper_url", ""),
        metadata.get("pdf_url", ""),
        metadata.get("access_note", ""),
    )
    if pmid:
        identifiers.append(pmid)

    doi = normalize_doi(metadata.get("doi", ""))
    if doi:
        identifiers.append(doi)

    deduped: list[str] = []
    for identifier in identifiers:
        if identifier and identifier not in deduped:
            deduped.append(identifier)
    return deduped


def fetch_pmc_idconv_json(identifiers: list[str]) -> tuple[dict[str, object] | None, str]:
    if not identifiers:
        return None, "PMCID解決に使えるPMIDまたはDOIがないためPMC確認をスキップした"

    query = urlencode({"ids": ",".join(identifiers), "format": "json"})
    url = f"{PMC_IDCONV_API_URL}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        if error.code in {401, 403, 407, 429}:
            return None, f"NCBI PMC ID Converter取得を停止した: HTTP {error.code}。認証、rate limit、またはアクセス制限の可能性がある"
        return None, f"NCBI PMC ID Converter取得に失敗した: HTTP {error.code}"
    except Exception as error:  # noqa: BLE001
        return None, f"NCBI PMC ID Converter取得に失敗した: {error}"

    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, f"NCBI PMC ID Converter応答をJSONとして読めなかった: {error}"

    if not isinstance(parsed, dict):
        return None, "NCBI PMC ID Converter応答がJSON objectではないためスキップした"
    return parsed, "NCBI PMC ID Converter応答を取得した"


def pmcids_from_idconv_payload(payload: dict[str, object]) -> list[str]:
    records = payload.get("records")
    if not isinstance(records, list):
        return []

    pmcids: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        pmcid_value = record.get("pmcid")
        if not isinstance(pmcid_value, str):
            continue
        pmcid = normalize_pmcid(pmcid_value)
        if pmcid and pmcid not in pmcids:
            pmcids.append(pmcid)
    return pmcids


def resolve_pmcids(metadata: dict[str, str]) -> tuple[list[str], list[str]]:
    direct_pmcids = direct_pmcids_from_metadata(metadata)
    if direct_pmcids:
        return direct_pmcids, [f"metadata内のPMCIDを取得した: {', '.join(direct_pmcids)}"]

    identifiers = pmc_idconv_identifiers(metadata)
    payload, message = fetch_pmc_idconv_json(identifiers)
    messages = [f"PMID/DOIからPMCIDを確認した: {message}"]
    if payload is None:
        return [], messages

    pmcids = pmcids_from_idconv_payload(payload)
    if pmcids:
        messages.append(f"NCBI PMC ID ConverterからPMCIDを取得した: {', '.join(pmcids)}")
    else:
        messages.append("NCBI PMC ID ConverterにPMCIDがないためPMC PDF取得をスキップした")
    return pmcids, messages


def pmc_article_url(pmcid: str) -> str:
    return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"


def pmc_pdf_url(pmcid: str) -> str:
    return f"{pmc_article_url(pmcid)}pdf/"


def pmc_oa_api_url(pmcid: str) -> str:
    return f"{PMC_OA_API_URL}?{urlencode({'id': pmcid})}"


def normalize_pmc_oa_download_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() != PMC_FTP_HOST:
        return url

    path = parsed.path.lstrip("/")
    if path.startswith("pub/pmc/deprecated/"):
        normalized_path = path
    elif path.startswith("pub/pmc/"):
        normalized_path = f"pub/pmc/deprecated/{path.removeprefix('pub/pmc/')}"
    else:
        normalized_path = path

    return f"https://{PMC_FTP_HOST}/{normalized_path}"


def fetch_pmc_oa_xml(pmcid: str) -> tuple[ET.Element | None, str]:
    url = pmc_oa_api_url(pmcid)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        if error.code in {401, 403, 407, 429}:
            return None, f"PMC OA API取得を停止した: HTTP {error.code}。認証、rate limit、またはアクセス制限の可能性がある"
        return None, f"PMC OA API取得に失敗した: HTTP {error.code}"
    except Exception as error:  # noqa: BLE001
        return None, f"PMC OA API取得に失敗した: {error}"

    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        return None, f"PMC OA API応答をXMLとして読めなかった: {error}"
    return root, "PMC OA API応答を取得した"


def pmc_oa_links_from_xml(root: ET.Element) -> tuple[list[dict[str, str]], list[str]]:
    messages: list[str] = []
    error_node = root.find("error")
    if error_node is not None:
        code = error_node.get("code", "")
        detail = (error_node.text or "").strip()
        if code == "idIsNotOpenAccess":
            messages.append(
                "PMC OA APIではOpen Access Subset対象外だった。PMC Free Full Textページがあっても、"
                "OA APIでPDF/package配布されるとは限らない"
            )
        else:
            suffix = f": {detail}" if detail else ""
            messages.append(f"PMC OA APIがエラーを返した: {code}{suffix}")
        return [], messages

    links: list[dict[str, str]] = []
    for record in root.findall(".//record"):
        license_value = record.get("license", "")
        citation = record.get("citation", "")
        for link_node in record.findall("link"):
            format_value = (link_node.get("format", "") or "").lower()
            href = (link_node.get("href", "") or "").strip()
            if format_value not in {"pdf", "tgz"} or not href:
                continue
            normalized_url = normalize_pmc_oa_download_url(href)
            links.append(
                {
                    "format": format_value,
                    "url": normalized_url,
                    "original_url": href,
                    "license": license_value,
                    "citation": citation,
                }
            )

    if links:
        messages.append(
            "PMC OA APIから取得候補を得た: "
            + ", ".join(f"{link['format']}={link['url']}" for link in links)
        )
    else:
        messages.append("PMC OA API応答にPDFまたはtgz package候補がなかった")
    return links, messages


def pmc_oa_access_note(pmcid: str, api_url: str, source_url: str, license_value: str, member_path: str = "") -> str:
    parts = [
        f"PMC OA API経由で取得: {source_url}",
        f"PMCID={pmcid}",
        f"PMC OA API URL={api_url}",
    ]
    if member_path:
        parts.append(f"package内PDF={member_path}")
    if license_value:
        parts.append(f"license={license_value}")
    return "; ".join(parts)


def doi_suffix_token(metadata: dict[str, str]) -> str:
    doi = normalize_doi(metadata.get("doi", ""))
    if not doi or "/" not in doi:
        return ""
    suffix = doi.rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "", suffix.lower())


def is_supplemental_pdf_name(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in SUPPLEMENTAL_PDF_TOKENS)


def tgz_pdf_candidates(tgz_path: Path, pmcid: str) -> tuple[list[tarfile.TarInfo], str]:
    try:
        with tarfile.open(tgz_path, "r:gz") as archive:
            candidates: list[tarfile.TarInfo] = []
            supplemental_candidates: list[str] = []
            for member in archive.getmembers():
                member_name = member.name.strip("/")
                parts = member_name.split("/")
                if not member.isfile() or len(parts) < 2:
                    continue
                if parts[0].upper() != pmcid.upper():
                    continue
                filename = parts[-1]
                if not filename.lower().endswith(".pdf"):
                    continue
                if is_supplemental_pdf_name(filename):
                    supplemental_candidates.append(member_name)
                    continue
                candidates.append(member)
    except (tarfile.TarError, OSError) as error:
        return [], f"PMC OA packageをtar.gzとして読めなかった: {error}"

    if candidates:
        return candidates, f"PMC OA package内の本文PDF候補: {', '.join(member.name for member in candidates)}"
    if supplemental_candidates:
        return [], f"PMC OA package内に補足資料PDFしか見つからなかった: {', '.join(supplemental_candidates)}"
    return [], "PMC OA package内にPMCID配下の本文PDF候補が見つからなかった"


def choose_tgz_article_pdf(candidates: list[tarfile.TarInfo], metadata: dict[str, str]) -> tuple[tarfile.TarInfo | None, str]:
    if not candidates:
        return None, "本文PDF候補がないため選択できなかった"

    main_candidates = [member for member in candidates if Path(member.name).name.lower() == "main.pdf"]
    if len(main_candidates) == 1:
        return main_candidates[0], f"main.pdfを本文PDFとして選択した: {main_candidates[0].name}"

    suffix_token = doi_suffix_token(metadata)
    if suffix_token:
        suffix_matches = [
            member
            for member in candidates
            if re.sub(r"[^a-z0-9]+", "", Path(member.name).stem.lower()).startswith(suffix_token)
        ]
        if len(suffix_matches) == 1:
            return suffix_matches[0], f"DOI末尾に一致するPDFを本文PDFとして選択した: {suffix_matches[0].name}"

    if len(candidates) == 1:
        return candidates[0], f"非補足PDFが1件だけのため本文PDFとして選択した: {candidates[0].name}"

    return None, f"本文PDF候補が複数あり自動選択できなかった: {', '.join(member.name for member in candidates)}"


def download_url_to_temp(url: str, max_bytes: int) -> tuple[Path | None, str]:
    if looks_sensitive_url(url):
        return None, "URLに認証情報・token・privateを示す文字列があるため取得を停止した"
    if not is_http_url(url):
        return None, f"URLがHTTP(S)ではないため取得をスキップした: {url}"

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    temp_path: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            content_length = response.headers.get("Content-Length", "")
            if content_length.isdigit() and int(content_length) > max_bytes:
                return None, f"PMC OA packageが大きすぎるため取得しなかった: {content_length} bytes > {max_bytes} bytes"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as temp_file:
                temp_path = Path(temp_file.name)
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        temp_file.close()
                        temp_path.unlink(missing_ok=True)
                        return None, f"PMC OA packageが上限を超えたため取得を停止した: {total} bytes > {max_bytes} bytes"
                    temp_file.write(chunk)
    except urllib.error.HTTPError as error:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        if error.code in {401, 403, 407, 429}:
            return None, f"PMC OA package取得を停止した: HTTP {error.code}。認証、rate limit、またはアクセス制限の可能性がある"
        return None, f"PMC OA package取得に失敗した: HTTP {error.code}"
    except Exception as error:  # noqa: BLE001
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        return None, f"PMC OA package取得に失敗した: {error}"

    if temp_path is None:
        return None, "PMC OA packageを一時ファイルへ保存できなかった"
    return temp_path, f"PMC OA packageを一時ファイルへ取得した: {url}"


def extract_pdf_from_tgz(tgz_path: Path, member: tarfile.TarInfo, destination: Path) -> str:
    try:
        with tarfile.open(tgz_path, "r:gz") as archive:
            extracted = archive.extractfile(member.name)
            if extracted is None:
                return f"PMC OA package内PDFを開けなかった: {member.name}"
            data = extracted.read()
    except (tarfile.TarError, OSError) as error:
        return f"PMC OA package内PDFの抽出に失敗した: {error}"

    if not is_likely_pdf(data, "application/pdf"):
        return f"PMC OA package内PDFがPDFではない可能性があるため保存しなかった: {member.name}"

    destination.write_bytes(data)
    return f"PMC OA packageからPDFを抽出した: {member.name}"


def fetch_html(url: str) -> tuple[str | None, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        if error.code in {401, 403, 407, 429}:
            return None, f"HTML取得を停止した: HTTP {error.code}。認証、rate limit、またはアクセス制限の可能性がある"
        return None, f"HTML取得に失敗した: HTTP {error.code}"
    except Exception as error:  # noqa: BLE001
        return None, f"HTML取得に失敗した: {error}"

    return data.decode("utf-8", errors="replace"), "HTMLを取得した"


def is_pmc_pdf_candidate_url(url: str, pmcid: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in {"pmc.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov"}:
        return False
    path = parsed.path.lower()
    if extract_pmcid(url) == pmcid:
        return path.endswith(".pdf") or "/pdf" in path
    return path.endswith(".pdf") and "/articles/" in path


def extract_pmc_pdf_links(html_text: str, base_url: str, pmcid: str) -> list[str]:
    patterns = [
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        r'href=["\']([^"\']*\.pdf(?:\?[^"\']*)?)["\']',
        r'href=["\']([^"\']*/pdf/?[^"\']*)["\']',
    ]
    candidates: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, html_text, flags=re.IGNORECASE):
            candidate = html_lib.unescape(match.group(1).strip())
            candidate_url = urljoin(base_url, candidate)
            if not is_http_url(candidate_url):
                continue
            if not is_pmc_pdf_candidate_url(candidate_url, pmcid):
                continue
            if candidate_url not in candidates:
                candidates.append(candidate_url)
    return candidates


def pmc_article_pdf_candidates(pmcid: str) -> tuple[list[str], str]:
    article_url = pmc_article_url(pmcid)
    html_text, message = fetch_html(article_url)
    if html_text is None:
        return [], f"PMC article pageからPDF候補を取得できなかった: {message}"

    candidates = extract_pmc_pdf_links(html_text, article_url, pmcid)
    if not candidates:
        return [], "PMC article pageにPDF候補リンクが見つからなかった"
    return candidates, f"PMC article pageからPDF候補を取得した: {', '.join(candidates)}"


def semantic_scholar_pdf_candidates(paper: dict[str, object]) -> tuple[list[str], str]:
    open_access_pdf = paper.get("openAccessPdf")
    if not isinstance(open_access_pdf, dict):
        return [], "Semantic ScholarにopenAccessPdfがないためPDF候補を取得できなかった"

    pdf_url = open_access_pdf.get("url")
    if not isinstance(pdf_url, str) or not pdf_url.strip():
        return [], "Semantic Scholar openAccessPdf.urlが空のためPDF候補を取得できなかった"

    candidates: list[str] = []
    for candidate in [pdf_url.strip(), normalize_open_access_pdf_url(pdf_url.strip())]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    status = open_access_pdf.get("status")
    status_text = f"; OA status={status}" if status else ""
    return candidates, f"Semantic Scholar openAccessPdfからPDF候補を取得した{status_text}"


def semantic_scholar_access_note(paper: dict[str, object], pdf_url: str) -> str:
    parts = [f"Semantic Scholar openAccessPdf経由で取得: {pdf_url}"]
    paper_url = paper.get("url")
    if isinstance(paper_url, str) and paper_url:
        parts.append(f"Semantic Scholar paper URL={paper_url}")

    open_access_pdf = paper.get("openAccessPdf")
    if isinstance(open_access_pdf, dict):
        status = open_access_pdf.get("status")
        license_value = open_access_pdf.get("license")
        if status:
            parts.append(f"OA status={status}")
        if license_value:
            parts.append(f"license={license_value}")
    return "; ".join(parts)


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
        if is_pmc_pow_html(data):
            return "PMC proof-of-work HTMLが返ったためpaper.pdfとして保存しなかった。自動アクセス防御は回避しない"
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


def download_semantic_scholar_pdf(
    metadata: dict[str, str],
    metadata_path: Path,
    destination: Path,
    force: bool,
) -> list[str]:
    messages = ["Semantic Scholar openAccessPdfによるPDF取得を試行した"]
    paper, query_messages = query_semantic_scholar(metadata)
    messages.extend(query_messages)
    if paper is None:
        return messages

    candidates, candidate_message = semantic_scholar_pdf_candidates(paper)
    messages.append(candidate_message)
    if not candidates:
        return messages

    for candidate_url in candidates:
        if looks_sensitive_url(candidate_url):
            messages.append("Semantic Scholar候補URLに認証情報・token・privateを示す文字列があるためPDF保存を停止した")
            continue
        if not is_http_url(candidate_url):
            messages.append(f"Semantic Scholar候補URLがHTTP(S)ではないためスキップした: {candidate_url}")
            continue

        pdf_message = download_pdf(candidate_url, destination, force)
        messages.append(f"Semantic Scholar候補PDFの取得結果: {pdf_message}")
        if destination.exists():
            messages.append(update_metadata_value(metadata_path, "pdf_url", candidate_url))
            access_note = semantic_scholar_access_note(paper, candidate_url)
            messages.append(append_metadata_note(metadata_path, "access_note", access_note))
            return messages

    messages.append("Semantic Scholar候補からpaper.pdfを保存できなかった")
    return messages


def download_pmc_oa_pdf(
    pmcid: str,
    metadata: dict[str, str],
    metadata_path: Path,
    destination: Path,
    force: bool,
) -> list[str]:
    api_url = pmc_oa_api_url(pmcid)
    messages = [f"PMC OA APIによるPDF/package取得を試行した: {api_url}"]
    root, fetch_message = fetch_pmc_oa_xml(pmcid)
    messages.append(fetch_message)
    if root is None:
        return messages

    links, link_messages = pmc_oa_links_from_xml(root)
    messages.extend(link_messages)
    if not links:
        return messages

    pdf_links = [link for link in links if link["format"] == "pdf"]
    tgz_links = [link for link in links if link["format"] == "tgz"]

    for link in pdf_links:
        candidate_url = link["url"]
        messages.append(f"PMC OA APIのPDF候補を試行した: {candidate_url}")
        pdf_message = download_pdf(candidate_url, destination, force)
        messages.append(f"PMC OA API PDF候補の取得結果: {pdf_message}")
        if destination.exists():
            messages.append(update_metadata_value(metadata_path, "pdf_url", candidate_url))
            messages.append(
                append_metadata_note(
                    metadata_path,
                    "access_note",
                    pmc_oa_access_note(pmcid, api_url, candidate_url, link.get("license", "")),
                )
            )
            return messages

    for link in tgz_links:
        package_url = link["url"]
        messages.append(f"PMC OA APIのtgz package候補を試行した: {package_url}")
        temp_path, download_message = download_url_to_temp(package_url, MAX_PMC_OA_TGZ_BYTES)
        messages.append(download_message)
        if temp_path is None:
            continue
        try:
            candidates, candidate_message = tgz_pdf_candidates(temp_path, pmcid)
            messages.append(candidate_message)
            selected, select_message = choose_tgz_article_pdf(candidates, metadata)
            messages.append(select_message)
            if selected is None:
                continue

            extract_message = extract_pdf_from_tgz(temp_path, selected, destination)
            messages.append(extract_message)
            if destination.exists():
                messages.append(
                    append_metadata_note(
                        metadata_path,
                        "access_note",
                        pmc_oa_access_note(
                            pmcid,
                            api_url,
                            package_url,
                            link.get("license", ""),
                            member_path=selected.name,
                        ),
                    )
                )
                return messages
        finally:
            temp_path.unlink(missing_ok=True)

    messages.append("PMC OA API候補からpaper.pdfを保存できなかった")
    return messages


def pmc_access_note(pmcid: str, pdf_url: str) -> str:
    return (
        f"PMC Free Full Text経由で取得: {pdf_url}; "
        f"PMCID={pmcid}; PMC article URL={pmc_article_url(pmcid)}"
    )


def download_pmc_pdf(
    metadata: dict[str, str],
    metadata_path: Path,
    destination: Path,
    force: bool,
) -> list[str]:
    messages = ["PMC Free Full TextによるPDF取得を試行した"]
    pmcids, resolve_messages = resolve_pmcids(metadata)
    messages.extend(resolve_messages)
    if not pmcids:
        return messages

    messages.append(update_metadata_value(metadata_path, "pmcid", pmcids[0]))

    for pmcid in pmcids:
        oa_messages = download_pmc_oa_pdf(pmcid, metadata, metadata_path, destination, force)
        messages.extend(oa_messages)
        if destination.exists():
            if pmcid != pmcids[0]:
                messages.append(update_metadata_value(metadata_path, "pmcid", pmcid))
            return messages

        candidate_urls = [pmc_pdf_url(pmcid)]
        for candidate_url in candidate_urls:
            pdf_message = download_pdf(candidate_url, destination, force)
            messages.append(f"PMC候補PDFの取得結果: {pdf_message}")
            if destination.exists():
                if pmcid != pmcids[0]:
                    messages.append(update_metadata_value(metadata_path, "pmcid", pmcid))
                messages.append(update_metadata_value(metadata_path, "pdf_url", candidate_url))
                messages.append(append_metadata_note(metadata_path, "access_note", pmc_access_note(pmcid, candidate_url)))
                return messages

        article_candidates, article_message = pmc_article_pdf_candidates(pmcid)
        messages.append(article_message)
        for candidate_url in article_candidates:
            if looks_sensitive_url(candidate_url):
                messages.append("PMC候補URLに認証情報・token・privateを示す文字列があるためPDF保存を停止した")
                continue
            pdf_message = download_pdf(candidate_url, destination, force)
            messages.append(f"PMC article page候補PDFの取得結果: {pdf_message}")
            if destination.exists():
                if pmcid != pmcids[0]:
                    messages.append(update_metadata_value(metadata_path, "pmcid", pmcid))
                messages.append(update_metadata_value(metadata_path, "pdf_url", candidate_url))
                messages.append(append_metadata_note(metadata_path, "access_note", pmc_access_note(pmcid, candidate_url)))
                return messages

    messages.append("PMC候補からpaper.pdfを保存できなかった")
    return messages


def manual_pdf_candidate_urls(metadata: dict[str, str]) -> list[str]:
    candidates: list[str] = []

    pdf_url = metadata.get("pdf_url", "").strip()
    if is_http_url(pdf_url):
        candidates.append(pdf_url)

    pmcids = direct_pmcids_from_metadata(metadata)
    for pmcid in pmcids:
        api_url = pmc_oa_api_url(pmcid)
        if api_url not in candidates:
            candidates.append(api_url)
        candidate = pmc_pdf_url(pmcid)
        if candidate not in candidates:
            candidates.append(candidate)

    paper_url = metadata.get("paper_url", "").strip()
    if is_http_url(paper_url) and paper_url not in candidates:
        candidates.append(paper_url)

    doi = normalize_doi(metadata.get("doi", ""))
    if doi:
        doi_url = f"https://doi.org/{doi}"
        if doi_url not in candidates:
            candidates.append(doi_url)

    return candidates


def urls_from_messages(messages: list[str]) -> list[str]:
    urls: list[str] = []
    for message in messages:
        for url in re.findall(r"https?://[^\s,;]+", message):
            cleaned = url.rstrip(").]")
            if cleaned not in urls:
                urls.append(cleaned)
    return urls


def manual_pdf_download_guidance(
    metadata: dict[str, str],
    destination: Path,
    extra_candidates: list[str] | None = None,
) -> str:
    candidates = manual_pdf_candidate_urls(metadata)
    for candidate in extra_candidates or []:
        if is_http_url(candidate) and candidate not in candidates:
            candidates.append(candidate)
    candidate_text = ", ".join(candidates) if candidates else "候補URLなし。paper_url、pdf_url、doi、pmcidをmetadata.yamlに追記してください"
    return f"手動PDF取得候補URL: {candidate_text}; 保存先: {destination}"


def load_ingest_module() -> object:
    script_path = Path(__file__).with_name("ingest_prior_research.py")
    spec = importlib.util.spec_from_file_location("ingest_prior_research", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"ingest scriptを読み込めない: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_ingest_after_download(
    item_dir: Path,
    force: bool,
    pdf_only: bool,
    code_only: bool,
    source_url: str = "",
) -> list[str]:
    module = load_ingest_module()
    ingest_prior_research = getattr(module, "ingest_prior_research")
    ingest_messages = ingest_prior_research(
        item_dir,
        force,
        pdf_only=pdf_only,
        source_only=code_only,
        source_url=source_url,
    )
    return [f"Markdown化: {message}" for message in ingest_messages]


def download_prior_research(
    item_dir: Path,
    force: bool,
    pdf_only: bool,
    code_only: bool,
    ingest_after_download: bool = True,
) -> list[str]:
    metadata_path = item_dir / "metadata.yaml"
    metadata = read_simple_metadata(metadata_path)
    pdf_url = metadata.get("pdf_url", "")
    code_url = metadata.get("code_url", "")
    pdf_path = item_dir / "paper.pdf"

    messages: list[str] = []
    if not code_only:
        pdf_message = download_pdf(pdf_url, pdf_path, force)
        messages.append(pdf_message)
        if not pdf_path.exists():
            pmc_messages = download_pmc_pdf(
                metadata,
                metadata_path,
                pdf_path,
                force,
            )
            messages.extend(pmc_messages)
        if not pdf_path.exists():
            semantic_scholar_messages = download_semantic_scholar_pdf(
                metadata,
                metadata_path,
                pdf_path,
                force,
            )
            messages.extend(semantic_scholar_messages)
        if not pdf_path.exists():
            messages.append("paper.pdfを保存できなかったためpaper.mdは作成しない。paper.mdは必ずpaper.pdfから変換する")
            latest_metadata = read_simple_metadata(metadata_path)
            messages.append(manual_pdf_download_guidance(latest_metadata, pdf_path, urls_from_messages(messages)))
    if not pdf_only:
        if code_url:
            if ingest_after_download:
                messages.append("code_urlはsource/へcloneせず、gitingest Python APIでsource.mdへ直接変換する")
            else:
                messages.append("source code本体は保存しない方針のため、--no-ingestではcode_urlからsource.mdを作成しない")
        else:
            messages.append("code_urlが空のためsource.md作成をスキップした")

    append_fetch_log(item_dir, messages)
    if ingest_after_download:
        try:
            source_url = code_url if not pdf_only else ""
            messages.extend(run_ingest_after_download(item_dir, force, pdf_only, code_only, source_url=source_url))
        except Exception as error:  # noqa: BLE001
            message = f"Markdown化をスキップした: {error}"
            messages.append(message)
            append_fetch_log(item_dir, [message])
    return messages


def extract_pmcid(url_or_text: str) -> str:
    match = re.search(r"PMC\s*\d+", url_or_text, flags=re.IGNORECASE)
    return re.sub(r"\s+", "", match.group(0)).upper() if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item_dir", help="Path such as prior_research/paper_a.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing paper.pdf, paper.md, or source.md.")
    parser.add_argument("--pdf-only", action="store_true", help="Only download paper.pdf.")
    parser.add_argument("--code-only", action="store_true", help="Only create source.md from code_url or local source/.")
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="Only download PDF and skip paper.md/source.md conversion. code_url is not cloned.",
    )
    args = parser.parse_args()

    if args.pdf_only and args.code_only:
        parser.error("--pdf-only and --code-only cannot be used together")
    require_uv_run(SCRIPT_RELATIVE_PATH)

    item_dir = Path(args.item_dir).expanduser().resolve()
    if not item_dir.exists():
        parser.error(f"item_dirが存在しません: {item_dir}")
    if not item_dir.is_dir():
        parser.error(f"item_dirはディレクトリではありません: {item_dir}")

    messages = download_prior_research(
        item_dir,
        args.force,
        args.pdf_only,
        args.code_only,
        ingest_after_download=not args.no_ingest,
    )
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
