from __future__ import annotations

import builtins
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "01-prior-research"
    / "scripts"
    / "ingest_prior_research.py"
)

spec = importlib.util.spec_from_file_location("ingest_prior_research", SCRIPT_PATH)
ingest_prior_research = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ingest_prior_research)


def make_item(root: Path) -> Path:
    item_dir = root / "prior_research" / "paper_a"
    (item_dir / "source").mkdir(parents=True)
    (item_dir / "metadata.yaml").write_text('ingested_at: ""\n', encoding="utf-8")
    (item_dir / "idea_notes.md").write_text("# アイデアメモ\n\n## 取得・変換ログ\n", encoding="utf-8")
    return item_dir


class IngestPriorResearchTests(unittest.TestCase):
    def test_require_uv_run_rejects_direct_python(self) -> None:
        with mock.patch.dict(ingest_prior_research.os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as raised:
                ingest_prior_research.require_uv_run("script.py")

        self.assertIn("uv経由で実行してください", str(raised.exception))

    def test_require_uv_run_allows_uv_run_environment(self) -> None:
        with mock.patch.dict(ingest_prior_research.os.environ, {"UV_RUN_RECURSION_DEPTH": "1"}, clear=True):
            ingest_prior_research.require_uv_run("script.py")

    def test_pdf_ingest_saves_images_to_figures_with_relative_markdown_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = make_item(Path(tmpdir))
            (item_dir / "paper.pdf").write_bytes(b"%PDF-1.4\n")
            calls: list[tuple[Path, str, dict[str, object]]] = []

            def fake_to_markdown(pdf_path: str, **kwargs: object) -> str:
                calls.append((Path.cwd(), pdf_path, dict(kwargs)))
                figure_dir = Path(str(kwargs["image_path"]))
                figure_dir.mkdir(parents=True, exist_ok=True)
                (figure_dir / "figure-1.png").write_bytes(b"fake png")
                return "本文\n\n![Figure 1](figures/figure-1.png)\n"

            fake_module = types.SimpleNamespace(to_markdown=fake_to_markdown)
            with mock.patch.dict(sys.modules, {"pymupdf4llm": fake_module}):
                message = ingest_prior_research.ingest_pdf(item_dir, force=False)

            self.assertIn("PDF内画像の保存先: figures/", message)
            self.assertTrue((item_dir / "figures" / "figure-1.png").exists())
            paper_markdown = (item_dir / "paper.md").read_text(encoding="utf-8")
            self.assertIn("![Figure 1](figures/figure-1.png)", paper_markdown)
            self.assertEqual(calls[0][0].resolve(), item_dir.resolve())
            self.assertEqual(calls[0][1], "paper.pdf")
            self.assertEqual(calls[0][2]["write_images"], True)
            self.assertEqual(calls[0][2]["image_path"], "figures")
            self.assertEqual(calls[0][2]["image_format"], "png")
            self.assertEqual(calls[0][2]["dpi"], 200)

    def test_missing_pymupdf4llm_does_not_use_other_pdf_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = make_item(Path(tmpdir))
            (item_dir / "paper.pdf").write_bytes(b"%PDF-1.4\n")

            real_import = builtins.__import__

            def fake_import(name: str, *args: object, **kwargs: object) -> object:
                if name == "pymupdf4llm":
                    raise ImportError("missing pymupdf4llm")
                return real_import(name, *args, **kwargs)

            with mock.patch.object(builtins, "__import__", side_effect=fake_import):
                message = ingest_prior_research.ingest_pdf(item_dir, force=False)

            self.assertIn("pymupdf4llmが未導入", message)
            self.assertIn("fallbackは追加せず", message)
            self.assertFalse((item_dir / "paper.md").exists())

    def test_missing_gitingest_does_not_create_builtin_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = make_item(Path(tmpdir))
            (item_dir / "source" / "model.py").write_text("print('hello')\n", encoding="utf-8")

            real_import = builtins.__import__

            def fake_import(name: str, *args: object, **kwargs: object) -> object:
                if name == "gitingest":
                    raise ImportError("missing gitingest")
                return real_import(name, *args, **kwargs)

            with mock.patch.object(builtins, "__import__", side_effect=fake_import):
                messages = ingest_prior_research.ingest_source(item_dir, force=False)

            joined = "\n".join(messages)
            self.assertIn("gitingestが未導入", joined)
            self.assertIn("fallbackは追加せず", joined)
            self.assertFalse((item_dir / "source.md").exists())

    def test_local_source_uses_gitingest_max_file_size_without_copying(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = make_item(Path(tmpdir))
            (item_dir / "source" / "model.py").write_text("print('hello')\n", encoding="utf-8")
            calls: list[tuple[str, dict[str, object]]] = []

            def fake_ingest(source: str, **kwargs: object) -> tuple[str, str, str]:
                calls.append((source, dict(kwargs)))
                return ("summary", "tree", "content")

            fake_module = types.SimpleNamespace(ingest=fake_ingest)
            with mock.patch.dict(sys.modules, {"gitingest": fake_module}):
                messages = ingest_prior_research.ingest_source(item_dir, force=False)

            self.assertIn("作成:", "\n".join(messages))
            self.assertTrue((item_dir / "source.md").exists())
            self.assertEqual(Path(calls[0][0]), item_dir / "source")
            self.assertEqual(calls[0][1]["max_file_size"], 100 * 1024)
            source_markdown = (item_dir / "source.md").read_text(encoding="utf-8")
            self.assertIn("gitingest max_file_size: 100KB", source_markdown)

    def test_source_url_uses_gitingest_directly_without_source_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = Path(tmpdir) / "prior_research" / "paper_a"
            item_dir.mkdir(parents=True)
            calls: list[tuple[str, dict[str, object]]] = []

            def fake_ingest(source: str, **kwargs: object) -> tuple[str, str, str]:
                calls.append((source, dict(kwargs)))
                return ("summary", "tree", "content")

            fake_module = types.SimpleNamespace(ingest=fake_ingest)
            with mock.patch.dict(sys.modules, {"gitingest": fake_module}):
                messages = ingest_prior_research.ingest_source_url(
                    item_dir,
                    "https://github.com/example/repo.git",
                    force=False,
                )

            self.assertIn("作成:", "\n".join(messages))
            self.assertFalse((item_dir / "source").exists())
            self.assertTrue((item_dir / "source.md").exists())
            self.assertEqual(calls[0][0], "https://github.com/example/repo.git")
            self.assertEqual(calls[0][1]["max_file_size"], 100 * 1024)

    def test_pdf_only_mode_skips_source_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = make_item(Path(tmpdir))

            with mock.patch.object(ingest_prior_research, "ingest_pdf", return_value="paper.mdを作成した"):
                with mock.patch.object(ingest_prior_research, "ingest_source") as mocked_source:
                    messages = ingest_prior_research.ingest_prior_research(
                        item_dir,
                        force=False,
                        pdf_only=True,
                    )

            mocked_source.assert_not_called()
            self.assertIn("paper.mdを作成した", messages)

    def test_source_only_mode_skips_pdf_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = make_item(Path(tmpdir))

            with mock.patch.object(ingest_prior_research, "ingest_pdf") as mocked_pdf:
                with mock.patch.object(ingest_prior_research, "ingest_source", return_value=["source.mdを作成した"]):
                    messages = ingest_prior_research.ingest_prior_research(
                        item_dir,
                        force=False,
                        source_only=True,
                    )

            mocked_pdf.assert_not_called()
            self.assertIn("source.mdを作成した", messages)

    def test_source_url_is_used_in_prior_research_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item_dir = make_item(Path(tmpdir))

            with mock.patch.object(ingest_prior_research, "ingest_pdf", return_value="paper.mdを作成した"):
                with mock.patch.object(
                    ingest_prior_research,
                    "ingest_source_url",
                    return_value=["source.mdをURLから作成した"],
                ) as mocked_source_url:
                    with mock.patch.object(ingest_prior_research, "ingest_source") as mocked_local_source:
                        messages = ingest_prior_research.ingest_prior_research(
                            item_dir,
                            force=False,
                            source_url="https://github.com/example/repo.git",
                        )

            mocked_source_url.assert_called_once_with(item_dir, "https://github.com/example/repo.git", False)
            mocked_local_source.assert_not_called()
            self.assertIn("source.mdをURLから作成した", messages)


if __name__ == "__main__":
    unittest.main()
