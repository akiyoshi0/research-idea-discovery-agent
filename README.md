# Idea Discovery Workspace

このワークスペースは、研究者の初期的な関心を、具体的な`discovery_state/research_plan.md`へ落とし込むためのローカル環境です。

構成は意図的に小さく保ちます。

```text
Codex
+ Markdown
+ 4 focused skills
+ 5 discovery_state files
+ prior_research/
+ data/
+ probes/
```

独自Web UI、データベース、ベクトルDB、複雑なmulti-agent基盤、自律的なテーマ決定機構、大規模実験パイプラインは作りません。

## 4つのskill

```text
.agents/skills/
├── 00-idea-discovery/
├── 01-prior-research/
├── 02-data-probe/
└── 03-research-plan/
```

- `00-idea-discovery`: 分野整理、gap抽出、仮説生成、仮説再考。
- `01-prior-research`: 先行研究の追加、PDFとsource.md整理、Markdown化、idea notes作成。
- `02-data-probe`: 公開データ確認、軽いprobe、data/README.mdとprobe.md更新。
- `03-research-plan`: 仮説の批判・順位づけ、人間の選択確認、research_plan.md作成。

## 使い方の流れ

最初に`discovery_brief.md`を書く。その後は直線ではなく、`00`〜`02`を何度も往復して仮説を育てる。

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
  ↓ 候補が十分育ったら
03 research-plan
```

最終的な仮説は人間が選ぶ。Codexが勝手に最終テーマを決めない。

## 最初の依頼例

```text
AGENTS.mdとdiscovery_brief.mdを読んでください。
00-idea-discovery skillのmap-fieldとして動作し、
discovery_state/field_map.mdを更新してください。
まだ仮説の確定やresearch_plan.mdの作成はしないでください。
```

## 先行研究ワークフロー

先行研究を追加するとき:

```text
01-prior-research skillで、先行研究 paper_a の置き場を作り、
metadata.yamlとidea_notes.mdを初期化してください。
```

PDFやcode_urlをMarkdown化するとき:

```text
01-prior-research skillで、prior_research/paper_a のPDFとcode_urlをMarkdown化してください。
失敗やスキップがあればidea_notes.mdに記録してください。
```

## data-probeワークフロー

```text
02-data-probe skillで、HYP-001の実行可能性を軽く確認するprobeを作ってください。
本格解析はせず、probe.mdとdata/README.mdに結果を記録してください。
```

## 研究計画化

```text
03-research-plan skillで、hypothesis_bank.mdの候補をcritique-rankしてください。
人間が選んだ仮説だけをresearch_plan.mdにしてください。
```

## Helper Scripts

scriptsはCodexの補助とスモークテスト用です。主なユーザーインターフェースではありません。

必要な場合だけ、手動で以下を実行できます。

```bash
uv run python scripts/init_idea_discovery_workspace.py
uv run python .agents/skills/01-prior-research/scripts/init_prior_research_item.py paper_a
uv run python .agents/skills/01-prior-research/scripts/download_prior_research.py prior_research/paper_a
uv run python .agents/skills/01-prior-research/scripts/ingest_prior_research.py prior_research/paper_a  # 再Markdown化だけを行う場合
uv run python .agents/skills/02-data-probe/scripts/init_probe.py probe_001_short_name
```

`download_prior_research.py`は、PDF取得と`code_url`からの`source.md`直接作成を行い、`paper.md`/`source.md`へのMarkdown化まで一括で実行します。取得だけに止めたい場合は`--no-ingest`を付けます。ただしsource code本体は保存しないため、`--no-ingest`時は`code_url`から`source.md`も作成しません。

## 初回セットアップ

PDFやcode_urlをMarkdown化する場合は、最初に`uv`で依存環境を同期してください。

```bash
uv sync
```

`.agents/skills/01-prior-research/scripts/ingest_prior_research.py`は、Markdown化に以下を使います。

- `pymupdf4llm`: `paper.pdf`から`paper.md`への変換
- `gitingest`: `code_url`または手動配置した`source/`から`source.md`への変換

PDF変換時は`pymupdf4llm`の画像保存オプションを使い、論文中の画像を`prior_research/<paper_id>/figures/`へ保存し、`paper.md`内に画像pathを残します。
`paper.md`は必ず`paper.pdf`から変換して作ります。PDFを保存できない場合は、PMC XML、HTML、abstract、publisher本文、API本文から`paper.md`だけを作りません。
公開repositoryのsource code本体はworkspaceへclone保存しません。`metadata.yaml`の`code_url`を`gitingest` Python APIへ直接渡し、`max_file_size=100 * 1024`で1ファイル100KB以下だけを対象にして`source.md`を作ります。`source/`は、人間がローカルsourceを手動配置した場合だけ使います。

未導入の場合は勝手に別ライブラリや内製の簡易変換へfallbackせず、スキップ理由を`idea_notes.md`に記録します。これらがなくても、Markdownファイルを手動で用意すればワークスペースは利用できます。

helper scriptを手動実行する場合は、同じ環境で実行します。
`python ...`や`python3 ...`で直接実行せず、必ず`uv run python ...`を使ってください。

```bash
uv run python .agents/skills/01-prior-research/scripts/download_prior_research.py prior_research/<paper_id>
```

## Safety

- paywallを回避しない。
- private repositoryを明示的な許可なしに取得しない。
- private data、clinical data、個人情報、機密情報を人間の承認なしに外部サービスへ送らない。
- 研究計画が固まる前に、`probes/`を本格解析へ膨らませない。
