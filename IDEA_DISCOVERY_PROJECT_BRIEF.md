# IDEA_DISCOVERY_PROJECT_BRIEF.md

# Idea Discovery Workspace

## 0. 最重要方針

このプロジェクトの本質は、**徹底的なシンプルさ**である。

作りたいものは、巨大なAI co-scientistではない。
作りたいものは、研究者がまだ研究計画書を持っていない段階で、Codexが文献・先行研究コード・公開データ・軽いデータ確認を使いながら、未解決問題、仮説、研究計画書を整理する **Idea Discovery Workspace** である。

最終形はこれだけでよい。

```text
Codex
+ Markdown
+ 1 core skill
+ 5 discovery_state files
+ prior_research/
+ data/
+ probes/
```

複雑なmulti-agent基盤、Web UI、DB、ベクトルDB、大規模自律パイプラインは作らない。

---

## 1. プロジェクトの目的

生命科学、バイオインフォマティクス、機械学習研究において、研究者が以下を行うためのローカルワークスペースを作る。

```text
研究分野を整理する
未解決問題を見つける
先行研究とそのコードを読む
公開DB・公開データを軽く確認する
仮説候補を作る
仮説を批判・順位づけする
最終的に research_plan.md を作る
```

この `research_plan.md` は、次段階の Research Co-Pilot Workspace に渡す。

---

## 2. 作らないもの

MVPでは作らない。

```text
- 独自Web UI
- データベース
- ベクトルDB
- 複数エージェント基盤
- 自動で研究テーマを決定する仕組み
- 本格的な実験実行環境
- 論文執筆環境
- 大規模解析パイプライン
- 自動投稿
```

---

## 3. 最終ディレクトリ構成

```text
idea-discovery-workspace/
├── AGENTS.md
├── IDEA_DISCOVERY_PROJECT_BRIEF.md
├── discovery_brief.md
├── prior_research/
│   └── paper_a/
│       ├── paper.pdf
│       ├── paper.md
│       ├── source/
│       ├── source.md
│       ├── metadata.yaml
│       └── idea_notes.md
├── data/
│   ├── README.md
│   ├── raw/
│   └── processed/
├── probes/
│   └── probe_001_short_name/
│       ├── probe.md
│       ├── script.py
│       ├── run.sh
│       └── outputs/
├── discovery_state/
│   ├── field_map.md
│   ├── gap_table.md
│   ├── hypothesis_bank.md
│   ├── decision_log.md
│   └── research_plan.md
├── scripts/
│   ├── init_idea_discovery_workspace.py
│   ├── init_prior_research_item.py
│   ├── ingest_prior_research.py
│   └── init_probe.py
└── .agents/
    └── skills/
        └── 00-idea-discovery/
            └── SKILL.md
```

---

## 4. 基本思想

Idea Discoveryは、LLMに自由に夢想させるものではない。

正しい流れは以下。

```text
文献を見る
↓
先行研究コードを見る
↓
公開DB・公開データを見る
↓
軽いコードで中身を確認する
↓
未解決問題を整理する
↓
仮説を作る
↓
仮説を批判する
↓
人間が選ぶ
↓
research_plan.md にする
```

このプロジェクトの強みは、**仮説生成に軽いデータ確認を入れること**である。

---

## 5. `discovery_brief.md`

人間が最初に書く入力ファイル。

テンプレート：

```markdown
# Discovery Brief

## Research area

## Personal interest

## Available data

## Available experimental system

## Available computational resources

## Skills and constraints

## Themes to avoid

## Desired output

## Notes
```

このファイルは最重要入力である。
Idea Discoveryでは、面白いアイデアよりも、**その研究者が実行できるアイデア**が重要である。

---

## 6. `prior_research/`

論文とそのソースコードを論文単位で保管する。

```text
prior_research/
└── paper_a/
    ├── paper.pdf
    ├── paper.md
    ├── source/
    ├── source.md
    ├── metadata.yaml
    └── idea_notes.md
```

### `paper.pdf`

論文PDF。
有料論文は人間が合法的に取得して配置する。

### `paper.md`

`paper.pdf` を `pymupdf4llm` でMarkdown化したもの。
Codexは基本的にこちらを読む。

### `source/`

先行研究のソースコード。

### `source.md`

`source/` を `gitingest` でLLM向けテキスト化したもの。
Codexはまずこちらを読む。

### `metadata.yaml`

テンプレート：

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

### `idea_notes.md`

Idea Discovery用メモ。

テンプレート：

```markdown
# Idea Notes

## What this paper did

## What remains unsolved

## Weaknesses / limitations

## Reusable data or code

## Possible follow-up ideas

## Connection to our interests

## Candidate hypotheses
```

---

## 7. `data/`

公開DBやscience-skills、Web検索、手動取得で得たデータを置く。

```text
data/
├── README.md
├── raw/
└── processed/
```

### `data/README.md`

Dataset Card Liteとして使う。

テンプレート：

```markdown
# Data README

## Data source

## Date accessed

## Version

## What it contains

## How it was obtained

## Usage restrictions

## Local path

## Notes
```

注意：

```text
- 巨大データを無理に保存しない
- 必要なら取得元と取得条件だけ記録する
- 臨床データや個人情報を外部送信しない
- データ取得は仮説生成補助のために限定する
```

---

## 8. `probes/`

仮説生成を補助するための軽いコード確認置き場。

`probes/` は本格実験ではない。

```text
probes/
└── probe_001_short_name/
    ├── probe.md
    ├── script.py
    ├── run.sh
    └── outputs/
```

### `probe.md`

テンプレート：

```markdown
# Probe

## Question

## Related hypothesis

## Data source

## Method

## Result

## Interpretation

## Supports hypothesis?

High / Medium / Low

## Weakens hypothesis?

High / Medium / Low

## Next action
```

### `script.py`

軽い確認コード。
大規模解析パイプラインを書いてはいけない。

### `run.sh`

再実行コマンド。

### `outputs/`

軽い表、ログ、図を置く。

---

## 9. `probes/` のルール

`probes/` の目的：

```text
- データが存在するか確認する
- 仮説が現実的か確認する
- 明らかに弱い仮説を落とす
- 簡単な傾向を見る
- research_plan.md に進める価値があるか判断する
```

`probes/` でやらないこと：

```text
- 最終結論を出す
- 論文用の本解析をする
- 複雑な機械学習パイプラインを作る
- 大量の前処理を作り込む
- 研究計画なしに深掘りしすぎる
```

---

## 10. `discovery_state/`

Idea Discoveryの状態をMarkdownで管理する。

```text
discovery_state/
├── field_map.md
├── gap_table.md
├── hypothesis_bank.md
├── decision_log.md
└── research_plan.md
```

---

## 11. `field_map.md`

分野の地図。

テンプレート：

```markdown
# Field Map

## Research area

## Major themes

## Key papers

## Key datasets

## Key methods

## Known open problems

## Recently active topics

## Stagnant or underexplored areas

## Notes
```

---

## 12. `gap_table.md`

未解決問題の表。

テンプレート：

```markdown
# Gap Table

| Gap ID | Unsolved problem | Evidence | Why unsolved | Importance | Feasibility | Notes |
|---|---|---|---|---|---|---|
```

評価は3段階でよい。

```text
High / Medium / Low
```

---

## 13. `hypothesis_bank.md`

仮説候補の一覧。

テンプレート：

```markdown
# Hypothesis Bank

| Hypothesis ID | Hypothesis | Related gap | Evidence | Data probe | Test method | Expected result | Failure condition | Feasibility | Fit | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
```

必ず入れる列：

```text
- 検証方法
- 予想結果
- 失敗条件
- Data probe
- Feasibility
- Fit
```

仮説は、面白いだけでは不十分である。
検証可能で、人間が実行できるものでなければならない。

---

## 14. `decision_log.md`

なぜその仮説を選び、なぜ他を捨てたかを書く。

テンプレート：

```markdown
# Decision Log

## Decision YYYY-MM-DD

### Selected hypothesis

### Rejected hypotheses

### Reason

### Human judgment

### Required next work

### Output research_plan
```

---

## 15. `research_plan.md`

最終成果物。
Research Co-Pilot Workspaceに渡すファイル。

テンプレート：

```markdown
# Research Plan

## Title

## Background

## Research gap

## Hypothesis

## Rationale

## Available data

## Proposed analysis / experiment

## Evaluation metrics

## Success criteria

## Risks and limitations

## Prior research

## Expected figures

## Manuscript outline

## Next step for Research Co-Pilot Workspace
```

---

## 16. core skillは1つだけ

skillは1つだけにする。

```text
.agents/skills/
└── 00-idea-discovery/
    └── SKILL.md
```

この1つのskillの中に、6つのモードを持たせる。

```text
mode: map-field
mode: find-gaps
mode: generate-hypotheses
mode: data-probe
mode: critique-rank
mode: write-research-plan
```

新しいskillを増やしてはいけない。

---

## 17. `00-idea-discovery` skill

### 目的

研究者の関心、文献、先行研究コード、公開DB、軽いデータ確認をもとに、未解決問題、仮説、研究計画書を作る。

### 入力

```text
- discovery_brief.md
- prior_research/*/paper.md
- prior_research/*/source.md
- prior_research/*/idea_notes.md
- data/README.md
- probes/*/probe.md
- discovery_state/*
```

### 出力

```text
- discovery_state/field_map.md
- discovery_state/gap_table.md
- discovery_state/hypothesis_bank.md
- discovery_state/decision_log.md
- discovery_state/research_plan.md
- probes/*
```

---

## 18. mode: `map-field`

やること：

```text
- discovery_brief.md を読む
- prior_research/ を確認する
- Web検索や文献検索で分野の全体像を整理する
- field_map.md を更新する
```

やってはいけないこと：

```text
- 仮説を確定しない
- 研究計画書を書かない
```

---

## 19. mode: `find-gaps`

やること：

```text
- field_map.md を読む
- prior_research/*/idea_notes.md を読む
- 未解決問題を抽出する
- gap_table.md に表として整理する
```

やってはいけないこと：

```text
- ギャップを1つに早く絞りすぎない
- 根拠のないギャップを書かない
```

---

## 20. mode: `generate-hypotheses`

やること：

```text
- gap_table.md を読む
- 複数の仮説候補を作る
- 検証方法、予想結果、失敗条件を書く
- hypothesis_bank.md を更新する
```

やってはいけないこと：

```text
- 面白いだけの仮説を残さない
- 検証方法がない仮説を残さない
```

---

## 21. mode: `data-probe`

やること：

```text
- 仮説候補に対して必要な公開DB・公開データを確認する
- science-skillsを必要に応じて使う
- data/ に取得情報を記録する
- probes/ に軽い確認コードを残す
- hypothesis_bank.md の Data probe 列を更新する
```

使ってよいもの：

```text
- Web検索
- PubMed
- Semantic Scholar
- OpenAlex
- NCBI
- UniProt
- Reactome
- STRING
- ClinVar
- gnomAD
- GTEx
- ChEMBL
- PubChem
- google-deepmind/science-skills
```

やってはいけないこと：

```text
- 大規模解析を始めない
- 論文用の本解析をしない
- 未承認で外部APIへ機密データを送らない
- データプローブ結果だけで結論を出さない
```

---

## 22. mode: `critique-rank`

やること：

```text
- hypothesis_bank.md を読む
- 各仮説を批判する
- 新規性、重要性、実行可能性、検証可能性、根拠、Fitを評価する
- 人間が選べるように候補を整理する
- decision_log.md を更新する
```

評価軸：

```text
Novelty
Importance
Feasibility
Testability
Evidence
Fit
Data-probe support
```

評価は3段階だけ。

```text
High / Medium / Low
```

やってはいけないこと：

```text
- 0-100点の複雑な採点をしない
- AIだけで最終テーマを決めない
- 人間の制約を無視しない
```

---

## 23. mode: `write-research-plan`

やること：

```text
- 人間が選んだ仮説をもとにする
- field_map.md、gap_table.md、hypothesis_bank.md、decision_log.mdを読む
- research_plan.md を書く
- Research Co-Pilot Workspaceへ渡せる形式にする
```

やってはいけないこと：

```text
- 未選択の仮説を勝手に採用しない
- 根拠のない研究計画を書かない
- 実行不可能な計画を書かない
```

---

## 24. science-skills の扱い

DeepMind science-skillsは、本体ではなく外部道具箱として使う。

MVPでは丸ごと同梱しない。
導入案内だけ置く。

```text
.agents/skills/external/google-deepmind-science-skills/
├── README.md
├── INSTALL.md
└── USAGE_POLICY.md
```

使用ルール：

```text
- 使うのは data-probe モードだけ
- 公開DB確認はOK
- API keyが必要なら人間に確認
- 臨床データや個人情報を外部送信しない
- 使ったDBと取得日を data/README.md に記録する
```

---

## 25. prior_research ingest

`prior_research/` のPDFとコードはMarkdown化する。

```text
paper.pdf -> paper.md
source/   -> source.md
```

実装は `scripts/ingest_prior_research.py` に置く。

使用ツール：

```text
pymupdf4llm
gitingest
```

やってはいけないこと：

```text
- paywallを回避しない
- 違法にPDFを取得しない
- private repositoryを勝手に取得しない
- ライセンス不明のコードを無条件に使わない
```

---

## 26. scripts

最小スクリプトだけ作る。

```text
scripts/
├── init_idea_discovery_workspace.py
├── init_prior_research_item.py
├── ingest_prior_research.py
└── init_probe.py
```

### `init_idea_discovery_workspace.py`

ワークスペース全体を初期化する。

生成対象：

```text
AGENTS.md
discovery_brief.md
prior_research/.gitkeep
data/README.md
data/raw/.gitkeep
data/processed/.gitkeep
probes/.gitkeep
discovery_state/field_map.md
discovery_state/gap_table.md
discovery_state/hypothesis_bank.md
discovery_state/decision_log.md
discovery_state/research_plan.md
.agents/skills/00-idea-discovery/SKILL.md
README.md
```

### `init_prior_research_item.py`

先行研究1件分を作る。

```bash
python scripts/init_prior_research_item.py paper_a
```

生成：

```text
prior_research/paper_a/
├── metadata.yaml
├── idea_notes.md
└── source/
```

### `ingest_prior_research.py`

PDFとコードをMarkdown化する。

```bash
python scripts/ingest_prior_research.py prior_research/paper_a
```

生成：

```text
paper.md
source.md
```

### `init_probe.py`

データプローブ用フォルダを作る。

```bash
python scripts/init_probe.py probe_001_gene_expression_check
```

生成：

```text
probes/probe_001_gene_expression_check/
├── probe.md
├── script.py
├── run.sh
└── outputs/
```

---

## 27. AGENTS.md テンプレート

```md
# AGENTS.md

## Role

You are an idea discovery co-pilot for life science, bioinformatics, and machine learning research.

You are not a fully autonomous scientist.
You help the human researcher discover research gaps, generate hypotheses, lightly probe data, critique ideas, and write a research_plan.md.

## Core Principles

- Keep the system extremely simple.
- Use Codex as the only UI.
- Do not create a custom Web UI.
- Do not introduce a database.
- Use Markdown as the shared memory.
- Use only one core skill: 00-idea-discovery.
- Do not create many agents.
- Do not decide the final research theme without human input.
- Prefer hypotheses that are testable and feasible.
- Use data-probe only as light reality check.
- Do not treat probes as final experiments.
- Do not send private, clinical, or sensitive data to external services without human approval.

## Start-of-task Routine

Before starting, read:

1. discovery_brief.md
2. discovery_state/field_map.md
3. discovery_state/gap_table.md
4. discovery_state/hypothesis_bank.md
5. discovery_state/decision_log.md
6. discovery_state/research_plan.md

When prior research is needed, read:

1. prior_research/*/metadata.yaml
2. prior_research/*/idea_notes.md
3. prior_research/*/paper.md
4. prior_research/*/source.md

When data probe is needed, read:

1. data/README.md
2. probes/*/probe.md

## Modes

The 00-idea-discovery skill has six modes:

- map-field
- find-gaps
- generate-hypotheses
- data-probe
- critique-rank
- write-research-plan

## Output Style

Always explain:

1. What you inspected
2. What you updated
3. Why it matters
4. Which file the human should inspect next
5. What decision the human needs to make
```

---

## 28. `SKILL.md` テンプレート

```md
---
name: idea-discovery
summary: Discover research gaps, generate hypotheses, run light data probes, critique ideas, and write a research_plan.md.
description: Use this skill when the user wants to explore research ideas before starting an implementation or experiment project.
---

# Purpose

Help the human researcher discover feasible, testable research ideas.

# Modes

- map-field
- find-gaps
- generate-hypotheses
- data-probe
- critique-rank
- write-research-plan

# Inputs

- discovery_brief.md
- prior_research/
- data/
- probes/
- discovery_state/

# Outputs

- discovery_state/field_map.md
- discovery_state/gap_table.md
- discovery_state/hypothesis_bank.md
- discovery_state/decision_log.md
- discovery_state/research_plan.md
- probes/

# Core rules

- Keep the workflow simple.
- Do not create extra skills.
- Do not create a database.
- Do not run large analyses.
- Use data-probe only as a light reality check.
- Do not decide the final research theme without human input.
- Always preserve why an idea was selected or rejected.

# Failure behavior

If evidence is insufficient, write that explicitly.
If data cannot be accessed, record that in data/README.md or probe.md.
If human judgment is required, stop and ask.
```

---

## 29. Codexへの実装依頼文

Codexには以下をそのまま渡す。

```text
この IDEA_DISCOVERY_PROJECT_BRIEF.md を読み、この設計に従ってMVPを実装してください。

最重要方針：
このプロジェクトの価値は、徹底的なシンプルさと、軽いデータ確認による仮説生成の補助です。
複雑なUI、DB、multi-agent基盤、大規模解析パイプラインは作らないでください。

作成するもの：

1. ディレクトリテンプレート
2. AGENTS.md
3. discovery_brief.md テンプレート
4. prior_research/ テンプレート
5. data/ テンプレート
6. probes/ テンプレート
7. discovery_state/ の5ファイル
8. .agents/skills/00-idea-discovery/SKILL.md
9. scripts/init_idea_discovery_workspace.py
10. scripts/init_prior_research_item.py
11. scripts/ingest_prior_research.py
12. scripts/init_probe.py
13. README.md

重要：
- skillは1つだけにしてください。
- discovery_stateは5ファイルだけにしてください。
- data-probeは本格解析ではなく、軽い確認だけにしてください。
- probes/の結果だけで結論を出さないでください。
- 最終成果は discovery_state/research_plan.md です。
- その research_plan.md は次の Research Co-Pilot Workspace に渡す前提です。
```

---

## 30. 最終定義

Idea Discovery Workspace は、研究者の関心と制約を入力し、文献・先行研究コード・公開DB・軽いデータプローブを使って、未解決問題、仮説、研究計画書を作るためのシンプルな研究アイデア探索環境である。

このプロジェクトの本質は、AIに研究テーマを勝手に決めさせることではない。

本質は、研究者がアイデアを見つける過程を、Codexが文献・データ・軽い確認コードで支え、最終的に実行可能な `research_plan.md` に落とすことである。
