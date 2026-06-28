# 研究アイデア創出エージェント

研究者がCodexと並走しながら、研究領域の整理、先行研究の読解、仮説生成、軽いデータ確認、研究計画化まで進めるためのローカルworkspaceです。

これは完成済みのWebアプリではありません。CodexとMarkdownを使う「研究アイデア探索用の作業机」です。独自Web UI、データベース、ベクトルDB、複雑なmulti-agent基盤は使いません。

cloneして使う詳しい手順は、[Cloneして使うための説明書](docs/clone_usage_guide_ja.md)を読んでください。

## できること

- 研究の関心や制約を`discovery_brief.md`に書き、分野の全体像を整理する
- 先行研究PDFや公開repositoryをMarkdown化し、研究アイデア探索用のメモにする
- 未解決問題と仮説候補を`discovery_state/`に蓄積する
- 公開データで仮説の実行可能性を軽く確認する
- 人間が選んだ仮説だけを`research_plan.md`へまとめる

最終的な研究テーマはCodexが勝手に決めません。候補を整理し、根拠や弱点を見えるようにして、人間が判断しやすくするための仕組みです。

## 最短の始め方

```bash
git clone https://github.com/akiyoshi0/research-idea-discovery-agent.git
cd research-idea-discovery-agent
uv sync
```

次に、`discovery_brief.md`へ研究の出発点を書きます。

```markdown
## 研究領域

~~~~モデル

## 研究の方向性

- 何を明らかにしたいか:
- 重視したい観点:
- 伸ばしたい方向:
- 比較したい既存手法・立場:
```

その後、Codexに次のように依頼します。

```text
AGENTS.mdとdiscovery_brief.mdを読んでください。
00-idea-discovery skillで、まずfield_map.mdを更新してください。
まだ仮説の確定やresearch_plan.mdの作成はしないでください。
```

## 基本の流れ

このworkspaceは直線的に一度だけ実行するものではありません。`00`から`02`を何度も往復し、仮説が十分育ったら`03`で研究計画にします。

```text
00 idea-discovery
  ↓ 分野整理、gap抽出、仮説生成
01 prior-research
  ↓ 必要な論文・コードを整理
00 revise-hypotheses
  ↓ 仮説を見直す
02 data-probe
  ↓ 公開データで軽く現実確認
00 revise-hypotheses
  ↓ 十分に育った候補を人間が選ぶ
03 research-plan
```

## 4つのskill

```text
.agents/skills/
├── 00-idea-discovery/
├── 01-prior-research/
├── 02-data-probe/
└── 03-research-plan/
```

| skill | 役割 |
|---|---|
| `00-idea-discovery` | 分野整理、gap抽出、仮説生成、仮説再考 |
| `01-prior-research` | 先行研究の追加、PDF/source整理、Markdown化、idea notes作成 |
| `02-data-probe` | 公開データ確認、軽いprobe、`data/README.md`と`probe.md`更新 |
| `03-research-plan` | 仮説の批判・順位づけ、人間の選択確認、`research_plan.md`作成 |

## 主要ファイル

```text
discovery_brief.md                  # 研究の出発点
discovery_state/field_map.md        # 分野の地図
discovery_state/gap_table.md        # 未解決問題
discovery_state/hypothesis_bank.md  # 仮説候補
discovery_state/decision_log.md     # 判断の記録
discovery_state/research_plan.md    # 最終的な研究計画
prior_research/                     # 先行研究ごとのPDF・Markdown・メモ
data/README.md                      # 利用データの整理
probes/                             # 軽い確認用probe
```

## よく使う依頼文

分野を整理する:

```text
00-idea-discovery skillで、discovery_brief.mdをもとにfield_map.mdを更新してください。
```

gapと仮説を作る:

```text
00-idea-discovery skillで、field_map.mdからgap_table.mdとhypothesis_bank.mdを更新してください。
```

先行研究を追加・取得する:

```text
01-prior-research skillで、この仮説に必要な先行研究を追加し、PDF取得とMarkdown化まで行ってください。
取得できないPDFがあれば、理由、手動確認URL、paper.pdfの保存先を示してください。
```

データで軽く確認する:

```text
02-data-probe skillで、H01の実行可能性を公開データで軽く確認してください。
本格解析にはせず、probe.mdとdata/README.mdに結果を記録してください。
```

研究計画にする:

```text
03-research-plan skillで、hypothesis_bank.mdの候補を批判・順位づけしてください。
人間が選んだ仮説だけをresearch_plan.mdにしてください。
```

## 先行研究の取得とMarkdown化

通常はCodexに`01-prior-research` skillで依頼します。必要な場合だけ、手動でhelper scriptを実行できます。

```bash
uv run python .agents/skills/01-prior-research/scripts/init_prior_research_item.py paper_a
uv run python .agents/skills/01-prior-research/scripts/download_prior_research.py prior_research/paper_a
uv run python .agents/skills/01-prior-research/scripts/ingest_prior_research.py prior_research/paper_a
```

`download_prior_research.py`は、PDF取得と`code_url`からの`source.md`作成を行い、取得後に`paper.md`/`source.md`へのMarkdown化も実行します。取得だけに止めたい場合は`--no-ingest`を付けます。

PDF取得は次の順で試します。

```text
metadata.yamlのpdf_url
→ PMC OA Web Service API
→ PMC Web PDF候補
→ Semantic Scholar openAccessPdf
→ 手動確認URLと保存先を提示
```

PMC OA APIが古い`ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/...`や`oa_package/...`を返す場合は、PMC FTP Serviceの2026年4月以降の配置に合わせて`https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/...`へ変換します。OA APIのtgz packageしかない場合は、250MB以下のpackageから本文PDFだけを抽出します。

`paper.md`は必ず`paper.pdf`から作ります。PDFを保存できない場合、PMC XML、HTML、abstract、publisher本文、API本文から`paper.md`だけを作ることはしません。

公開repositoryのsource code本体はworkspaceへclone保存しません。`metadata.yaml`の`code_url`を`gitingest` Python APIへ直接渡し、1ファイル100KB以下を対象にして`source.md`を作ります。

## 依存環境

初回は必ず次を実行してください。

```bash
uv sync
```

Python helper scriptを手で動かす場合は、必ず`uv run python ...`を使います。

```bash
uv run python .agents/skills/01-prior-research/scripts/download_prior_research.py prior_research/<paper_id>
```

`python ...`や`python3 ...`で直接実行しないでください。workspaceの`.venv`ではなく別のPythonを使ってしまい、依存ライブラリが見つからない原因になります。

主な依存ライブラリ:

- `pymupdf4llm`: `paper.pdf`を`paper.md`へ変換する
- `gitingest`: 公開repositoryを`source.md`へ変換する

未導入の場合、別ライブラリや内製の簡易変換へ勝手にfallbackしません。`uv sync`で環境を整えるか、PDF/Markdownを手動で用意してください。

## 安全方針

- paywallを回避しない
- login、cookie認証、Cloudflare challenge、PMC proof-of-workを回避しない
- private repositoryを明示的な許可なしに取得しない
- private data、clinical data、個人情報、機密情報を承認なしに外部サービスへ送らない
- `probes/`は軽い現実確認に限定し、本格解析パイプラインにしない

取得できなかったPDFは、理由、手動確認URL、`paper.pdf`の保存先を`idea_notes.md`と応答に残します。
