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
- `01-prior-research`: 先行研究の追加、PDF/source整理、Markdown化、idea notes作成。
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

PDFやsourceをMarkdown化するとき:

```text
01-prior-research skillで、prior_research/paper_a のPDFとsourceをMarkdown化してください。
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
python scripts/init_idea_discovery_workspace.py
python .agents/skills/01-prior-research/scripts/init_prior_research_item.py paper_a
python .agents/skills/01-prior-research/scripts/download_prior_research.py prior_research/paper_a
python .agents/skills/01-prior-research/scripts/ingest_prior_research.py prior_research/paper_a
python .agents/skills/02-data-probe/scripts/init_probe.py probe_001_short_name
```

## Optional Dependencies

`.agents/skills/01-prior-research/scripts/ingest_prior_research.py`は、導入されていれば以下を使います。

- `pymupdf4llm`: `paper.pdf`から`paper.md`への変換
- `gitingest`: `source/`から`source.md`への変換

これらがなくても、Markdownファイルを手動で用意すればワークスペースは利用できます。

## Safety

- paywallを回避しない。
- private repositoryを明示的な許可なしに取得しない。
- private data、clinical data、個人情報、機密情報を人間の承認なしに外部サービスへ送らない。
- 研究計画が固まる前に、`probes/`を本格解析へ膨らませない。
