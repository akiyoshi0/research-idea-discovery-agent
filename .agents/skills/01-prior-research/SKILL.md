---
name: prior-research
description: 先行研究の置き場作成、metadata.yaml、idea_notes.md、paper.pdf/sourceの整理、paper.md/source.mdへのingest、先行研究からの未解決点整理を担当する。
---

# 目的

先行研究の論文PDFとsource codeを、Idea Discovery Workspaceで読める形に取得・整理する。

このskillは、研究アイデア探索のための文献・コード入力を整える担当である。仮説生成そのものは`00-idea-discovery`、軽いデータ確認は`02-data-probe`、最終研究計画は`03-research-plan`へ渡す。

# 入力

- 人間が指定した`paper_id`
- `doi`
- `paper_url`
- `pdf_url`
- `code_url`
- ローカルに配置された`paper.pdf`
- ローカルに配置された`source/`

# 出力

```text
prior_research/<paper_id>/
├── paper.pdf
├── paper.md
├── metadata.yaml
├── idea_notes.md
├── source/
└── source.md
```

# 言語方針

- 説明と`idea_notes.md`は日本語で書く。
- 論文タイトル、著者名、DOI、URL、repository名、ライセンス名、API名は原表記を残す。

# 基本ルール

- paywallを回避しない。
- private repositoryを勝手に取得しない。
- login、token、API key、認証が必要な場合は人間に確認する。
- ライセンスが不明なコードを無条件に再利用可能と扱わない。
- `research_state/logbook.md`は使わない。記録は`metadata.yaml`と`idea_notes.md`に残す。
- helper scriptは補助であり、skillがワークフローを管理する。

# 先行研究アイテム作成

人間が「先行研究を追加して」と依頼したら:

1. `prior_research/<paper_id>/`を作る。
2. `metadata.yaml`を作る。
3. `idea_notes.md`を作る。
4. `source/`を作る。
5. 作成ログを`idea_notes.md`に残す。

helper scriptを使う場合:

```bash
python .agents/skills/01-prior-research/scripts/init_prior_research_item.py <paper_id>
```

# metadata.yaml

最低限、以下を維持する。

```yaml
title: ""
authors: []
year: ""
doi: ""
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
```

# idea_notes.md

最低限、以下を整理する。

```markdown
# アイデアメモ

## この論文が行ったこと

## 未解決の点

## 弱点・限界

## 再利用できるデータ・コード

## 発展アイデア

## こちらの関心との関係

## 仮説候補

## 取得・変換ログ
```

# PDF/sourceの取得・配置

- 人間が合法的に取得したPDFは`paper.pdf`として配置する。
- `metadata.yaml`の`pdf_url`が公開・合法アクセス可能なPDFを指す場合だけ、`paper.pdf`として取得してよい。
- 公開repositoryのsource codeは`source/`へ取得・配置する。
- 取得元、取得日時、ライセンス注意、アクセス制約を`metadata.yaml`または`idea_notes.md`に書く。
- paywall、login、token、private repository、HTML応答、ライセンス不明などがあれば、保存せず人間に確認する。

helper scriptを使う場合:

```bash
python .agents/skills/01-prior-research/scripts/download_prior_research.py prior_research/<paper_id>
```

このscriptは`metadata.yaml`の`pdf_url`と`code_url`を読み、公開PDFと公開Git repositoryだけを取得する。取得できない理由は`idea_notes.md`に記録する。
`paper_url`または`pdf_url`にPMCIDが含まれ、PDF取得がHTML応答・challenge等で保存できない場合は、NCBI E-utilitiesのPMC XMLから`paper.md`を作成してよい。

# ingest

人間が「Markdown化して」と依頼したら:

1. `paper.pdf`があれば`paper.md`へ変換する。
2. `source/`があれば`source.md`へ変換する。
3. source ingestは軽量に保ち、1ファイル100KB以下を対象にする。
4. skipped file、変換失敗、未導入dependencyを`idea_notes.md`に記録する。
5. `metadata.yaml`の`ingested_at`を更新する。

helper scriptを使う場合:

```bash
python .agents/skills/01-prior-research/scripts/ingest_prior_research.py prior_research/<paper_id>
```

# 00への戻し方

先行研究を読んだ後は、`00-idea-discovery`の`revise-hypotheses`に戻れるように、次を明記する。

- 既存仮説を支持する点
- 既存仮説を弱める点
- 既存研究で既に解かれている可能性
- 新しく追加すべきgap
- 新しく追加すべき仮説候補

# 失敗時の動作

取得・変換できない場合は、理由を`idea_notes.md`に書く。
paywall、private repository、認証、ライセンス不明の場合は停止して人間に確認する。
