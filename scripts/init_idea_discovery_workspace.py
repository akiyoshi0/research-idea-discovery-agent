#!/usr/bin/env python3
"""Initialize a minimal Idea Discovery Workspace."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


TEMPLATES = {
    "AGENTS.md": """# AGENTS.md

## Role

あなたは、生命科学・バイオインフォマティクス・機械学習研究のためのidea discovery co-pilotです。

完全自律型の科学者ではありません。研究者が研究ギャップを見つけ、仮説を作り、先行研究と公開データで軽く確認し、最終的に`research_plan.md`へまとめる過程を支援します。

## Core Principles

- 必要な依存ライブラリや外部toolが未導入の場合、勝手に別ライブラリ・内製実装・簡易fallbackを追加しない。
- 失敗理由を記録し、依存導入、手動作成、または明示的な代替案承認を人間に確認する。
- skillや既存scriptで明示されたfallbackだけを使ってよい。
- workspace内のPython helper scriptは`uv run python ...`で実行する。`python ...`や`python3 ...`で直接実行しない。
- 依存環境を整える場合は`uv sync`を使う。

## Skills

このworkspaceは4つのskillで運用する。

```text
.agents/skills/
├── 00-idea-discovery/
├── 01-prior-research/
├── 02-data-probe/
└── 03-research-plan/
```

## Operating Loop

```text
00 idea-discovery
  ↓ 必要な先行研究を特定
01 prior-research
  ↓ 文献・コードから知見を追加
00 revise-hypotheses
  ↓ 確認すべき仮説を選ぶ
02 data-probe
  ↓ 軽いデータ確認結果を追加
00 revise-hypotheses
  ↓ 足りなければまた01/02へ
03 research-plan
```

## Output Style

人間が明示的に別言語を指定しない限り、ユーザー向け説明と、このワークスペースで作成・更新するMarkdownは日本語で書く。

## 曖昧なskill呼び出し

ユーザーがskill名だけを指定し、具体的な作業対象や依頼内容がない場合は、通常の作業報告として長く説明しない。

- skillの中身を要約しない。
- 「skillを確認しました」だけで返さない。
- そのskillで何をしたいかを短く聞く。
- 選択肢を出す場合は3〜5個までにする。
""",
    "README.md": """# Idea Discovery Workspace

このワークスペースは、研究者の初期的な関心を、具体的な`discovery_state/research_plan.md`へ落とし込むためのローカル環境です。

Codex、Markdown、4つのfocused skill、先行研究、公開データメモ、軽いprobeだけを使います。独自Web UI、データベース、ベクトルDB、複雑なmulti-agent基盤、大規模実験パイプラインは追加しません。

## 4つのskill

- `00-idea-discovery`: 分野整理、gap抽出、仮説生成、仮説再考。
- `01-prior-research`: 先行研究の追加、PDFとsource.md整理、Markdown化、idea notes作成。
- `02-data-probe`: 公開データ確認、軽いprobe、data/README.mdとprobe.md更新。
- `03-research-plan`: 仮説の批判・順位づけ、人間の選択確認、research_plan.md作成。

## 初回セットアップ

PDFやcode_urlをMarkdown化する場合は、最初に`uv`で依存環境を同期してください。

```bash
uv sync
```

Python helper scriptは、`python ...`や`python3 ...`で直接実行せず、必ず`uv run python ...`で実行します。

PDF変換時は、論文中の画像を`prior_research/<paper_id>/figures/`へ保存し、`paper.md`内に画像pathを残します。
`paper.md`は必ず`paper.pdf`から変換して作ります。PDFを保存できない場合は、PMC XML、HTML、abstract、publisher本文、API本文から`paper.md`だけを作りません。
公開repositoryのsource code本体はworkspaceへclone保存しません。`metadata.yaml`の`code_url`を`gitingest` Python APIへ直接渡し、`max_file_size=100 * 1024`で1ファイル100KB以下だけを対象にして`source.md`を作ります。`source/`は、人間がローカルsourceを手動配置した場合だけ使います。
""",
    "pyproject.toml": """[project]
name = "idea-discovery-workspace"
version = "0.1.0"
description = "Local Codex and Markdown workspace for research idea discovery."
requires-python = ">=3.12"
dependencies = [
    "gitingest",
    "pymupdf4llm",
]
""",
    "discovery_brief.md": """# ディスカバリーブリーフ

## 研究領域

書くべき内容：研究したい大枠。

## 研究の方向性

書くべき内容：

- 何を明らかにしたいか:
- 重視したい観点:
- 伸ばしたい方向:
- 比較したい既存手法・立場:

## 利用可能なデータ

書くべき内容：使える公開データ、自前データ、候補データ。

## 利用可能な実験系

書くべき内容：wet実験など。in silicoだけならそう書く。

## 利用可能な計算資源

書くべき内容：GPU、CPU、クラウド可否、予算、実行時間の制約。

## スキルと制約

書くべき内容：自分ができること・できないこと。例: Python可、深層学習可、wet実験不可。

## 避けたいテーマ

書くべき内容：やりたくない方向、実行困難な方向、興味が薄い方向。

## メモ

書くべき内容：その他の自由記述。迷っている点や仮説の断片を書く。
""",
    "data/README.md": """# データREADME

## データソース

## アクセス日

## バージョン

## 含まれる内容

## 取得方法

## 利用制限

## ローカルパス

## メモ
""",
    "discovery_state/field_map.md": """# 分野マップ

## 研究領域

## 主要テーマ

## 重要論文

## 重要データセット

## 重要手法

## 既知の未解決問題

## 最近活発なトピック

## 停滞している領域・未探索領域

## メモ
""",
    "discovery_state/gap_table.md": """# ギャップ表

| Gap ID | 未解決問題 | 根拠 | 未解決である理由 | 重要度 | 実行可能性 | メモ |
|---|---|---|---|---|---|---|
""",
    "discovery_state/hypothesis_bank.md": """# 仮説バンク

状態は `Active` / `Needs prior research` / `Needs data probe` / `Revised` / `Rejected` / `Selected` のいずれかを使う。

| Hypothesis ID | 状態 | 仮説 | 関連gap | 根拠 | 必要な先行研究 | Data probe | 検証方法 | 予想結果 | 失敗条件 | 実行可能性 | Fit | 最終判断 | 更新履歴 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
""",
    "discovery_state/decision_log.md": """# 意思決定ログ

## Decision YYYY-MM-DD

### 採択した仮説

### 採択しなかった仮説

### 理由

### 人間による判断

### 次に必要な作業

### Output research_plan
""",
    "discovery_state/research_plan.md": """# 研究計画

## タイトル

## 背景

## 研究ギャップ

## 仮説

## 根拠

## 利用可能なデータ

## 提案する解析・実験

## 評価指標

## 成功条件

## リスクと限界

## 先行研究

## 想定される図表

## 論文構成案

## Research Co-Pilot Workspaceへの次ステップ
""",
    ".agents/skills/external/google-deepmind-science-skills/README.md": """# google-deepmind/science-skills

このディレクトリは外部toolboxへの案内だけを置く場所です。core skillではなく、このワークスペースにtoolbox本体を同梱しません。

外部science skillsは`data-probe` modeでのみ使います。用途は、仮説が実行可能か判断するための公開データ確認に限定します。
""",
    ".agents/skills/external/google-deepmind-science-skills/INSTALL.md": """# Install

`google-deepmind/science-skills`を自動でinstallしたり、このworkspaceへvendorしたりしないでください。

data-probeで必要になった場合は、先に人間の研究者へ確認してください。導入したversion、API要件、使用DB、アクセス日は`data/README.md`に記録します。
""",
    ".agents/skills/external/google-deepmind-science-skills/USAGE_POLICY.md": """# Usage Policy

- この外部toolboxは`data-probe` modeでのみ使う。
- 公開DB確認に限定して使う。
- API keyを使う前に人間へ確認する。
- private data、clinical data、個人情報、機密情報を外部サービスへ送らない。
- 使用DB、query、version、アクセス日は`data/README.md`に記録する。
- 結果は軽い根拠として扱い、最終結論として扱わない。
""",
}


DIRECTORIES = [
    "prior_research",
    "data/raw",
    "data/processed",
    "probes",
    "discovery_state",
    "scripts",
    ".agents/skills/00-idea-discovery",
    ".agents/skills/01-prior-research",
    ".agents/skills/02-data-probe",
    ".agents/skills/03-research-plan",
    ".agents/skills/external/google-deepmind-science-skills",
]


GITKEEP_FILES = [
    "prior_research/.gitkeep",
    "data/raw/.gitkeep",
    "data/processed/.gitkeep",
    "probes/.gitkeep",
]


SCRIPT_FILES = [
    "init_idea_discovery_workspace.py",
]


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"既存ファイルを保持: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return f"作成: {path}"


def copy_script(source: Path, destination: Path, force: bool) -> str:
    if not source.exists():
        return f"source scriptが見つからない: {source}"
    if source.resolve() == destination.resolve():
        return f"既存ファイルを保持: {destination}"
    if destination.exists() and not force:
        return f"既存ファイルを保持: {destination}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return f"コピー: {destination}"


def copy_tree_files(source_dir: Path, destination_dir: Path, force: bool) -> list[str]:
    if not source_dir.exists():
        return [f"copy元ディレクトリが見つからない: {source_dir}"]

    messages: list[str] = []
    for source in sorted(source_dir.rglob("*")):
        if not source.is_file():
            continue

        relative = source.relative_to(source_dir)
        if relative.parts and relative.parts[0] == "external":
            continue

        destination = destination_dir / relative
        if source.resolve() == destination.resolve():
            messages.append(f"既存ファイルを保持: {destination}")
            continue
        if destination.exists() and not force:
            messages.append(f"既存ファイルを保持: {destination}")
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        messages.append(f"コピー: {destination}")

    return messages


def touch_file(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return f"作成または保持: {path}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Workspace root to initialize. Defaults to the current directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing template files.",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    for directory in DIRECTORIES:
        (root / directory).mkdir(parents=True, exist_ok=True)

    source_root = Path(__file__).resolve().parent.parent
    messages = []
    for relative_path, content in TEMPLATES.items():
        messages.append(write_file(root / relative_path, content, args.force))

    source_scripts_dir = Path(__file__).resolve().parent
    for script_file in SCRIPT_FILES:
        messages.append(
            copy_script(
                source_scripts_dir / script_file,
                root / "scripts" / script_file,
                args.force,
            )
        )

    messages.extend(
        copy_tree_files(
            source_root / ".agents" / "skills",
            root / ".agents" / "skills",
            args.force,
        )
    )

    for relative_path in GITKEEP_FILES:
        messages.append(touch_file(root / relative_path))

    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
