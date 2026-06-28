from __future__ import annotations

import io
import importlib.util
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "01-prior-research"
    / "scripts"
    / "download_prior_research.py"
)

spec = importlib.util.spec_from_file_location("download_prior_research", SCRIPT_PATH)
download_prior_research = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(download_prior_research)


class FakeResponse:
    def __init__(
        self,
        data: bytes,
        content_type: str = "",
        final_url: str = "",
        content_length: int | None = None,
    ) -> None:
        self._data = data
        self._offset = 0
        self.headers = {"Content-Type": content_type}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        self._final_url = final_url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk = self._data[self._offset :]
            self._offset = len(self._data)
            return chunk
        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self._final_url


def write_item(root: Path, metadata: dict[str, str]) -> Path:
    item_dir = root / "prior_research" / "paper_a"
    item_dir.mkdir(parents=True)
    defaults = {
        "title": "",
        "doi": "",
        "pmid": "",
        "pmcid": "",
        "paper_url": "",
        "pdf_url": "",
        "code_url": "",
        "access_note": "",
    }
    defaults.update(metadata)
    lines = [f'{key}: "{value}"' for key, value in defaults.items()]
    (item_dir / "metadata.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (item_dir / "idea_notes.md").write_text("# アイデアメモ\n\n## 取得・変換ログ\n", encoding="utf-8")
    return item_dir


def semantic_scholar_payload(
    pdf_url: str,
    *,
    title: str = "Example Paper",
    status: str = "GREEN",
    license_value: str | None = None,
) -> bytes:
    return json.dumps(
        {
            "paperId": "a" * 40,
            "title": title,
            "url": "https://www.semanticscholar.org/paper/" + "a" * 40,
            "isOpenAccess": True,
            "openAccessPdf": {
                "url": pdf_url,
                "status": status,
                "license": license_value,
            },
        }
    ).encode("utf-8")


def pmc_idconv_payload(pmcid: str = "", *, pmid: str = "12345678", doi: str = "10.123/example") -> bytes:
    record: dict[str, str] = {"pmid": pmid, "doi": doi}
    if pmcid:
        record["pmcid"] = pmcid
    return json.dumps({"status": "ok", "records": [record]}).encode("utf-8")


def pmc_oa_payload(
    pmcid: str,
    links: list[tuple[str, str]],
    *,
    license_value: str = "CC BY",
) -> bytes:
    link_text = "".join(f'<link format="{format_value}" href="{href}" />' for format_value, href in links)
    return (
        f'<OA><request id="{pmcid}">https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}</request>'
        f'<records returned-count="1" total-count="1"><record id="{pmcid}" citation="Example" '
        f'license="{license_value}" retracted="no">{link_text}</record></records></OA>'
    ).encode("utf-8")


def pmc_oa_not_open_payload(pmcid: str) -> bytes:
    return (
        f"<OA><request>https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}</request>"
        f'<error code="idIsNotOpenAccess">identifier {pmcid!r} is not Open Access</error></OA>'
    ).encode("utf-8")


def make_tgz(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class DownloadPriorResearchTests(unittest.TestCase):
    def test_require_uv_run_rejects_direct_python(self) -> None:
        with mock.patch.dict(download_prior_research.os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as raised:
                download_prior_research.require_uv_run("script.py")

        self.assertIn("uv経由で実行してください", str(raised.exception))

    def test_require_uv_run_allows_uv_run_environment(self) -> None:
        with mock.patch.dict(download_prior_research.os.environ, {"UV_RUN_RECURSION_DEPTH": "1"}, clear=True):
            download_prior_research.require_uv_run("script.py")

    def run_with_fake_network(
        self,
        item_dir: Path,
        route: object,
        *,
        ingest_after_download: bool = False,
        pdf_only: bool = True,
        code_only: bool = False,
    ) -> tuple[list[str], list[str]]:
        calls: list[str] = []

        def fake_urlopen(request: object, timeout: int = 45) -> FakeResponse:
            del timeout
            url = request.full_url  # type: ignore[attr-defined]
            calls.append(url)
            response = route(url)
            if isinstance(response, Exception):
                raise response
            return response

        with mock.patch.dict(download_prior_research.os.environ, {}, clear=True):
            with mock.patch.object(download_prior_research.urllib.request, "urlopen", side_effect=fake_urlopen):
                messages = download_prior_research.download_prior_research(
                    item_dir,
                    force=False,
                    pdf_only=pdf_only,
                    code_only=code_only,
                    ingest_after_download=ingest_after_download,
                )
        return messages, calls

    def test_direct_pdf_success_does_not_call_semantic_scholar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {"pdf_url": "https://example.org/paper.pdf", "doi": "10.123/example"},
            )

            def route(url: str) -> FakeResponse:
                self.assertNotIn("api.semanticscholar.org", url)
                return FakeResponse(b"%PDF-1.4\n", "application/pdf", url)

            messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertTrue((item_dir / "paper.pdf").exists())
            self.assertEqual(calls, ["https://example.org/paper.pdf"])
            self.assertTrue(any("PDFを取得した" in message for message in messages))
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn('pdf_url: "https://example.org/paper.pdf"', metadata)

    def test_empty_pdf_url_uses_semantic_scholar_open_access_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {"doi": "10.123/example", "title": "Example Paper"},
            )

            def route(url: str) -> FakeResponse:
                if "pmc/utils/idconv" in url:
                    return FakeResponse(pmc_idconv_payload(), "application/json", url)
                if "api.semanticscholar.org" in url:
                    return FakeResponse(
                        semantic_scholar_payload("https://open.example/paper.pdf", license_value="CC-BY"),
                        "application/json",
                        url,
                    )
                if url == "https://open.example/paper.pdf":
                    return FakeResponse(b"%PDF-1.4\n", "application/pdf", url)
                raise AssertionError(f"unexpected URL: {url}")

            messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertTrue((item_dir / "paper.pdf").exists())
            self.assertTrue(any("api.semanticscholar.org" in call for call in calls))
            self.assertTrue(any("Semantic Scholar候補PDFの取得結果" in message for message in messages))
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn('pdf_url: "https://open.example/paper.pdf"', metadata)
            self.assertIn("Semantic Scholar openAccessPdf経由で取得", metadata)
            self.assertIn("license=CC-BY", metadata)

    def test_html_direct_response_falls_back_to_pmc_pdf_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {
                    "doi": "10.123/example",
                    "pdf_url": "https://publisher.example/paper",
                    "title": "Example Paper",
                },
            )

            def route(url: str) -> FakeResponse:
                if url == "https://publisher.example/paper":
                    return FakeResponse(b"<html>not pdf</html>", "text/html", url)
                if "pmc/utils/idconv" in url:
                    return FakeResponse(pmc_idconv_payload(), "application/json", url)
                if "api.semanticscholar.org" in url:
                    return FakeResponse(
                        semantic_scholar_payload("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567"),
                        "application/json",
                        url,
                    )
                if url == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567":
                    return FakeResponse(b"<html>pmc landing</html>", "text/html", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/":
                    return FakeResponse(b"%PDF-1.4\n", "application/pdf", url)
                raise AssertionError(f"unexpected URL: {url}")

            _messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertTrue((item_dir / "paper.pdf").exists())
            self.assertIn("https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/", calls)
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn('pdf_url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/"', metadata)

    def test_publisher_failure_uses_pmc_pdf_from_pubmed_idconv_before_semantic_scholar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {
                    "doi": "10.1016/j.ctarc.2020.100174",
                    "paper_url": "https://pubmed.ncbi.nlm.nih.gov/32413603/",
                    "pdf_url": "https://publisher.example/pdfft",
                    "title": "Example Paper",
                },
            )

            def route(url: str) -> FakeResponse:
                if url == "https://publisher.example/pdfft":
                    raise HTTPError(url, 403, "Forbidden", hdrs=None, fp=None)
                if "pmc/utils/idconv" in url:
                    return FakeResponse(
                        pmc_idconv_payload("PMC7572629", pmid="32413603", doi="10.1016/j.ctarc.2020.100174"),
                        "application/json",
                        url,
                    )
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(pmc_oa_not_open_payload("PMC7572629"), "text/xml", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC7572629/pdf/":
                    return FakeResponse(b"%PDF-1.4\n", "application/pdf", url)
                if "api.semanticscholar.org" in url:
                    raise AssertionError("Semantic Scholar should not be called after PMC PDF success")
                raise AssertionError(f"unexpected URL: {url}")

            messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertTrue((item_dir / "paper.pdf").exists())
            self.assertTrue(any("pmc/utils/idconv" in call for call in calls))
            self.assertIn("https://pmc.ncbi.nlm.nih.gov/articles/PMC7572629/pdf/", calls)
            self.assertFalse(any("api.semanticscholar.org" in call for call in calls))
            self.assertTrue(any("PMC候補PDFの取得結果" in message for message in messages))
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn('pmcid: "PMC7572629"', metadata)
            self.assertIn('pdf_url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7572629/pdf/"', metadata)
            self.assertIn("PMC Free Full Text経由で取得", metadata)

    def test_pmc_article_page_citation_pdf_url_is_used_when_pmc_pdf_path_returns_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {
                    "paper_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/",
                    "pdf_url": "https://publisher.example/paper",
                },
            )

            def route(url: str) -> FakeResponse:
                if url == "https://publisher.example/paper":
                    return FakeResponse(b"<html>not pdf</html>", "text/html", url)
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(pmc_oa_not_open_payload("PMC1234567"), "text/xml", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/":
                    return FakeResponse(b"<html>pmc pdf landing</html>", "text/html", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/":
                    return FakeResponse(
                        b'<html><meta name="citation_pdf_url" content="/articles/PMC1234567/pdf/main.pdf"></html>',
                        "text/html",
                        url,
                    )
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/main.pdf":
                    return FakeResponse(b"%PDF-1.4\n", "application/pdf", url)
                raise AssertionError(f"unexpected URL: {url}")

            _messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertTrue((item_dir / "paper.pdf").exists())
            self.assertIn("https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/main.pdf", calls)
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn('pmcid: "PMC1234567"', metadata)
            self.assertIn('pdf_url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/main.pdf"', metadata)

    def test_pmc_oa_api_pdf_link_is_normalized_to_deprecated_https(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {
                    "pmcid": "PMC3531057",
                    "doi": "10.1093/nar/gks1111",
                },
            )
            normalized_pdf_url = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_pdf/f8/10/gks1111.PMC3531057.pdf"

            def route(url: str) -> FakeResponse:
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(
                        pmc_oa_payload(
                            "PMC3531057",
                            [("pdf", "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/f8/10/gks1111.PMC3531057.pdf")],
                            license_value="CC BY-NC",
                        ),
                        "text/xml",
                        url,
                    )
                if url == normalized_pdf_url:
                    return FakeResponse(b"%PDF-1.4\n", "application/pdf", url)
                if "api.semanticscholar.org" in url:
                    raise AssertionError("Semantic Scholar should not be called after PMC OA PDF success")
                raise AssertionError(f"unexpected URL: {url}")

            messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertTrue((item_dir / "paper.pdf").exists())
            self.assertIn(normalized_pdf_url, calls)
            self.assertFalse(any("api.semanticscholar.org" in call for call in calls))
            self.assertTrue(any("PMC OA API PDF候補の取得結果" in message for message in messages))
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn(f'pdf_url: "{normalized_pdf_url}"', metadata)
            self.assertIn("PMC OA API経由で取得", metadata)
            self.assertIn("license=CC BY-NC", metadata)

    def test_pmc_oa_api_tgz_extracts_main_pdf_without_pdf_url_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {
                    "pmcid": "PMC4967469",
                    "doi": "10.1016/j.cell.2016.06.017",
                },
            )
            tgz_url = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_package/74/87/PMC4967469.tar.gz"
            tgz_data = make_tgz(
                {
                    "PMC4967469/main.pdf": b"%PDF-1.4\nmain",
                    "PMC4967469/mmc1.pdf": b"%PDF-1.4\nsupplement",
                }
            )

            def route(url: str) -> FakeResponse:
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(
                        pmc_oa_payload(
                            "PMC4967469",
                            [("tgz", "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/74/87/PMC4967469.tar.gz")],
                        ),
                        "text/xml",
                        url,
                    )
                if url == tgz_url:
                    return FakeResponse(tgz_data, "application/x-gzip", url, content_length=len(tgz_data))
                if "api.semanticscholar.org" in url:
                    raise AssertionError("Semantic Scholar should not be called after PMC OA tgz success")
                raise AssertionError(f"unexpected URL: {url}")

            messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertTrue((item_dir / "paper.pdf").exists())
            self.assertIn(tgz_url, calls)
            self.assertTrue(any("main.pdfを本文PDFとして選択した" in message for message in messages))
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn('pdf_url: ""', metadata)
            self.assertIn("package内PDF=PMC4967469/main.pdf", metadata)

    def test_pmc_oa_tgz_over_size_does_not_save_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(Path(tmpdir), {"pmcid": "PMC9999999", "title": "Example Paper"})
            tgz_url = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_package/aa/bb/PMC9999999.tar.gz"

            def route(url: str) -> FakeResponse:
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(
                        pmc_oa_payload(
                            "PMC9999999",
                            [("tgz", "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/aa/bb/PMC9999999.tar.gz")],
                        ),
                        "text/xml",
                        url,
                    )
                if url == tgz_url:
                    return FakeResponse(
                        b"",
                        "application/x-gzip",
                        url,
                        content_length=download_prior_research.MAX_PMC_OA_TGZ_BYTES + 1,
                    )
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC9999999/pdf/":
                    return FakeResponse(b"<html>not pdf</html>", "text/html", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC9999999/":
                    return FakeResponse(b"<html>no pdf</html>", "text/html", url)
                if "api.semanticscholar.org" in url:
                    raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)
                raise AssertionError(f"unexpected URL: {url}")

            messages, _calls = self.run_with_fake_network(item_dir, route)

            self.assertFalse((item_dir / "paper.pdf").exists())
            self.assertTrue(any("大きすぎる" in message for message in messages))
            self.assertTrue(any("手動PDF取得候補URL" in message for message in messages))

    def test_pmc_oa_tgz_supplement_only_does_not_save_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(Path(tmpdir), {"pmcid": "PMC9999998", "title": "Example Paper"})
            tgz_url = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_package/aa/bb/PMC9999998.tar.gz"
            tgz_data = make_tgz({"PMC9999998/article-supplement-1.pdf": b"%PDF-1.4\nsupp"})

            def route(url: str) -> FakeResponse:
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(
                        pmc_oa_payload(
                            "PMC9999998",
                            [("tgz", "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/aa/bb/PMC9999998.tar.gz")],
                        ),
                        "text/xml",
                        url,
                    )
                if url == tgz_url:
                    return FakeResponse(tgz_data, "application/x-gzip", url, content_length=len(tgz_data))
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC9999998/pdf/":
                    return FakeResponse(b"<html>not pdf</html>", "text/html", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC9999998/":
                    return FakeResponse(b"<html>no pdf</html>", "text/html", url)
                if "api.semanticscholar.org" in url:
                    raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)
                raise AssertionError(f"unexpected URL: {url}")

            messages, _calls = self.run_with_fake_network(item_dir, route)

            self.assertFalse((item_dir / "paper.pdf").exists())
            self.assertTrue(any("補足資料PDFしか" in message for message in messages))

    def test_pmc_oa_tgz_multiple_article_pdfs_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(Path(tmpdir), {"pmcid": "PMC9999997", "title": "Example Paper"})
            tgz_url = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_package/aa/bb/PMC9999997.tar.gz"
            tgz_data = make_tgz(
                {
                    "PMC9999997/article-a.pdf": b"%PDF-1.4\na",
                    "PMC9999997/article-b.pdf": b"%PDF-1.4\nb",
                }
            )

            def route(url: str) -> FakeResponse:
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(
                        pmc_oa_payload(
                            "PMC9999997",
                            [("tgz", "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/aa/bb/PMC9999997.tar.gz")],
                        ),
                        "text/xml",
                        url,
                    )
                if url == tgz_url:
                    return FakeResponse(tgz_data, "application/x-gzip", url, content_length=len(tgz_data))
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC9999997/pdf/":
                    return FakeResponse(b"<html>not pdf</html>", "text/html", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC9999997/":
                    return FakeResponse(b"<html>no pdf</html>", "text/html", url)
                if "api.semanticscholar.org" in url:
                    raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)
                raise AssertionError(f"unexpected URL: {url}")

            messages, _calls = self.run_with_fake_network(item_dir, route)

            self.assertFalse((item_dir / "paper.pdf").exists())
            self.assertTrue(any("複数あり自動選択できなかった" in message for message in messages))

    def test_pmc_proof_of_work_html_is_logged_and_not_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {
                    "pmcid": "PMC1234567",
                    "pdf_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/",
                    "title": "Example Paper",
                },
            )
            pow_html = b"<html><title>Preparing to download ...</title><script>const POW_CHALLENGE = 'x'</script></html>"

            def route(url: str) -> FakeResponse:
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/":
                    return FakeResponse(pow_html, "text/html", url)
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(pmc_oa_not_open_payload("PMC1234567"), "text/xml", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/":
                    return FakeResponse(b"<html>no pdf</html>", "text/html", url)
                if "api.semanticscholar.org" in url:
                    raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)
                raise AssertionError(f"unexpected URL: {url}")

            messages, _calls = self.run_with_fake_network(item_dir, route)

            self.assertFalse((item_dir / "paper.pdf").exists())
            self.assertTrue(any("PMC proof-of-work HTML" in message for message in messages))

    def test_semantic_scholar_429_logs_without_metadata_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {"doi": "10.123/example", "title": "Example Paper"},
            )

            def route(url: str) -> FakeResponse:
                if "pmc/utils/idconv" in url:
                    return FakeResponse(pmc_idconv_payload(), "application/json", url)
                if "api.semanticscholar.org" in url:
                    raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)
                raise AssertionError(f"unexpected URL: {url}")

            messages, _calls = self.run_with_fake_network(item_dir, route)

            self.assertFalse((item_dir / "paper.pdf").exists())
            self.assertTrue(any("HTTP 429" in message for message in messages))
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn('pdf_url: ""', metadata)
            self.assertIn('access_note: ""', metadata)
            notes = (item_dir / "idea_notes.md").read_text(encoding="utf-8")
            self.assertIn("HTTP 429", notes)
            self.assertIn("手動PDF取得候補URL", notes)
            self.assertIn(str(item_dir / "paper.pdf"), notes)

    def test_pmc_xml_does_not_create_markdown_without_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(
                Path(tmpdir),
                {
                    "doi": "10.123/example",
                    "title": "Example Paper",
                    "paper_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/",
                    "pdf_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/",
                },
            )

            def route(url: str) -> FakeResponse:
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/":
                    return FakeResponse(b"<html>not pdf</html>", "text/html", url)
                if "pmc/utils/oa/oa.fcgi" in url:
                    return FakeResponse(pmc_oa_not_open_payload("PMC1234567"), "text/xml", url)
                if url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/":
                    return FakeResponse(b"<html>no pdf link</html>", "text/html", url)
                if "api.semanticscholar.org" in url:
                    raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)
                if "eutils.ncbi.nlm.nih.gov" in url:
                    raise AssertionError("PMC XML fallback must not be called")
                raise AssertionError(f"unexpected URL: {url}")

            messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertFalse((item_dir / "paper.pdf").exists())
            self.assertFalse((item_dir / "paper.md").exists())
            self.assertFalse(any("eutils.ncbi.nlm.nih.gov" in call for call in calls))
            self.assertTrue(any("paper.mdは作成しない" in message for message in messages))
            self.assertTrue(any("手動PDF取得候補URL" in message for message in messages))
            self.assertTrue(any(str(item_dir / "paper.pdf") in message for message in messages))
            notes = (item_dir / "idea_notes.md").read_text(encoding="utf-8")
            self.assertIn("paper.mdは作成しない", notes)
            self.assertIn("https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/", notes)
            self.assertIn(str(item_dir / "paper.pdf"), notes)

    def test_title_search_requires_exact_match_when_ids_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(Path(tmpdir), {"title": "Exact Paper"})

            def route(url: str) -> FakeResponse:
                if "api.semanticscholar.org" in url:
                    return FakeResponse(
                        json.dumps(
                            {
                                "data": [
                                    {
                                        "paperId": "b" * 40,
                                        "title": "Different Paper",
                                        "openAccessPdf": {"url": "https://wrong.example/paper.pdf"},
                                    },
                                    json.loads(
                                        semantic_scholar_payload(
                                            "https://open.example/exact.pdf",
                                            title="Exact Paper",
                                        ).decode("utf-8")
                                    ),
                                ]
                            }
                        ).encode("utf-8"),
                        "application/json",
                        url,
                    )
                if url == "https://open.example/exact.pdf":
                    return FakeResponse(b"%PDF-1.4\n", "application/pdf", url)
                raise AssertionError(f"unexpected URL: {url}")

            _messages, calls = self.run_with_fake_network(item_dir, route)

            self.assertTrue(any("/paper/search" in call for call in calls))
            self.assertTrue((item_dir / "paper.pdf").exists())
            metadata = (item_dir / "metadata.yaml").read_text(encoding="utf-8")
            self.assertIn('pdf_url: "https://open.example/exact.pdf"', metadata)

    def test_pdf_download_can_run_markdown_ingest_after_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(Path(tmpdir), {"pdf_url": "https://example.org/paper.pdf"})

            def route(url: str) -> FakeResponse:
                return FakeResponse(b"%PDF-1.4\n", "application/pdf", url)

            with mock.patch.object(
                download_prior_research,
                "run_ingest_after_download",
                return_value=["Markdown化: paper.mdを作成した"],
            ) as mocked_ingest:
                messages, _calls = self.run_with_fake_network(
                    item_dir,
                    route,
                    ingest_after_download=True,
                )

            mocked_ingest.assert_called_once_with(item_dir, False, True, False, source_url="")
            self.assertIn("Markdown化: paper.mdを作成した", messages)

    def test_code_url_uses_gitingest_without_cloning_source_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = write_item(Path(tmpdir), {"code_url": "https://github.com/example/repo.git"})

            def route(url: str) -> FakeResponse:
                raise AssertionError(f"unexpected network request: {url}")

            with mock.patch.object(
                download_prior_research,
                "run_ingest_after_download",
                return_value=["Markdown化: source.mdを作成した"],
            ) as mocked_ingest:
                messages, calls = self.run_with_fake_network(
                    item_dir,
                    route,
                    ingest_after_download=True,
                    pdf_only=False,
                    code_only=True,
                )

            self.assertEqual(calls, [])
            self.assertFalse((item_dir / "source").exists())
            mocked_ingest.assert_called_once_with(
                item_dir,
                False,
                False,
                True,
                source_url="https://github.com/example/repo.git",
            )
            self.assertTrue(any("source/へcloneせず" in message for message in messages))
            self.assertIn("Markdown化: source.mdを作成した", messages)


if __name__ == "__main__":
    unittest.main()
