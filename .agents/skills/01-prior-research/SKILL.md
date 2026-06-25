---
name: prior-research
description: 先行研究の置き場作成、metadata.yaml、idea_notes.md、paper.pdf/source.mdの整理、paper.md/source.mdへのingest、先行研究からの未解決点整理を担当する。
---

# 目的

先行研究の論文PDFと、公開repositoryの要約Markdownを、Idea Discovery Workspaceで読める形に取得・整理する。

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
├── figures/
├── metadata.yaml
├── idea_notes.md
├── source.md
└── source/  # 任意。人間がローカルsourceを手動配置する場合だけ使う
```

# 言語方針

- 説明と`idea_notes.md`は日本語で書く。
- 論文タイトル、著者名、DOI、URL、repository名、ライセンス名、API名は原表記を残す。

# 文章表現の方針

- `idea_notes.md`は論文の表現を写す場所ではなく、研究アイデア探索に使うための読解メモとして書く。
- 論文由来の英語専門語をそのまま並べない。初出では必ず短い日本語説明を添える。
- データセット名、モデル名、正式な評価指標名、API名は原表記を残してよいが、概念語はできるだけ日本語で噛み砕く。
- 「著者らはXを示した」で止めず、「このworkspaceの仮説やgapにどう関係するか」まで平易に書く。
- 1文に専門語を複数詰め込まない。専門家が読んでも、頭の中で翻訳し直さなくてよい文章にする。

言い換え例:

```text
replicate ceiling -> 同じ条件を繰り返したときに、測定値がどこまで一致するかという上限
generic response -> 多くの薬剤や条件で共通して出る反応
conservative collapse -> モデルが安全側に倒れて、変化量を小さく予測してしまう現象
signature reversal -> 疾患で増減した遺伝子変化を、薬剤で逆向きに戻せるかを見る考え方
applicability domain -> その予測を信じてよい条件の範囲
zero-shot context -> 学習時に見ていない条件への予測
```

# 基本ルール

- paywallを回避しない。
- private repositoryを勝手に取得しない。
- login、token、API key、認証が必要な場合は人間に確認する。
- ライセンスが不明なコードを無条件に再利用可能と扱わない。
- `research_state/logbook.md`は使わない。記録は`metadata.yaml`と`idea_notes.md`に残す。
- helper scriptは補助であり、skillがワークフローを管理する。
- 依存ライブラリが未導入の場合、勝手に別ライブラリ・内製実装・簡易変換へfallbackしない。失敗理由を記録し、人間に依存導入または手動作成を確認する。
- helper scriptは必ず`uv run python ...`で実行する。`python ...`や`python3 ...`の直呼びは、`.venv`外のPythonを使って依存不足を起こすため使わない。
- `pymupdf4llm`や`gitingest`が見つからない場合は、まずworkspace rootで`uv sync`を実行する。

# 曖昧な呼び出しへの対応

ユーザーが`$prior-research`、`01-prior-research`、`prior-research`のようにskill名だけを指定し、具体的なpaper_id、URL、PDF/source.md、依頼内容を書いていない場合:

- skillの中身やディレクトリ構造を説明しない。
- 「skillを確認しました」「以後この形式に従います」のような確認報告だけで終わらない。
- 次に何をしたいかを短く聞く。
- 候補を出す場合も、次の選択肢だけを簡潔に示す。

返答例:

```text
prior-researchで何をしますか？

- 新しい先行研究を追加する
- PDFを取得し、source.mdを作成する
- paper.md/source.mdに変換する
- 既存の先行研究を読んで仮説に反映する
```

# 先行研究アイテム作成

人間が「先行研究を追加して」と依頼したら:

1. `prior_research/<paper_id>/`を作る。
2. `metadata.yaml`を作る。
3. `idea_notes.md`を作る。
4. 作成ログを`idea_notes.md`に残す。

helper scriptを使う場合:

```bash
uv run python .agents/skills/01-prior-research/scripts/init_prior_research_item.py <paper_id>
```

# metadata.yaml

最低限、以下を維持する。

```yaml
title: ""
authors: []
year: ""
doi: ""
pmid: ""
pmcid: ""
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

# PDF/source.mdの取得・配置

- 人間が合法的に取得したPDFは`paper.pdf`として配置する。
- `metadata.yaml`の`pdf_url`が公開・合法アクセス可能なPDFを指す場合だけ、`paper.pdf`として取得してよい。
- 雑誌HPのPDFが見つからない、HTML応答、HTTP 403/challenge、有料公開などで保存できず、PMCIDまたはPMC Free Full Textが確認できる場合は、PMCの公開PDFを取得候補にする。
- PMCIDは`metadata.yaml`の`pmcid`、`paper_url`、`pdf_url`から拾う。PMCIDが直接ない場合は、公開情報である`pmid`、PubMed URL、DOIをNCBI PMC ID Converterに問い合わせてPMCIDを確認してよい。
- `pdf_url`が空、HTTP失敗、HTML応答、landing page応答などで`paper.pdf`を保存できない場合は、Semantic Scholar Academic Graph APIの`openAccessPdf`を確認してよい。
- Semantic Scholar経由で使ってよいのは、`openAccessPdf.url`が示す公開OA候補と、そこから明確に導けるarXiv/PMCのPDFだけに限定する。paywall回避や認証回避には使わない。
- Semantic Scholar API keyは任意の環境変数`SEMANTIC_SCHOLAR_API_KEY`だけを使う。API keyを`metadata.yaml`、`idea_notes.md`、ログへ書かない。
- `paper.md`は必ず`paper.pdf`から変換して作る。`paper.pdf`を保存できない場合、PMC XML、HTML、abstract、publisher本文、API本文から`paper.md`だけを作らない。
- すべてのPDF取得候補に失敗した場合は、ユーザーに聞かれる前に、手動で確認すべきURLと`paper.pdf`の保存先を`idea_notes.md`と最終応答に明記する。
- 公開repositoryのsource code本体はworkspaceへclone保存しない。
- `code_url`がある場合は、`gitingest` Python APIへURLを直接渡し、`source.md`だけを作成する。
- source ingestのファイルサイズ上限は、wrapper側の一時コピーではなく、`gitingest.ingest(..., max_file_size=100 * 1024)`で指定する。
- `source/`は、人間がローカルsourceを手動配置した場合の再Markdown化用入力としてだけ使う。
- 取得元、取得日時、ライセンス注意、アクセス制約を`metadata.yaml`または`idea_notes.md`に書く。
- paywall、login、token、private repository、HTML応答、ライセンス不明などがあれば、保存せず人間に確認する。

helper scriptを使う場合:

```bash
uv run python .agents/skills/01-prior-research/scripts/download_prior_research.py prior_research/<paper_id>
```

このscriptは`metadata.yaml`の`pdf_url`と`code_url`を読み、公開PDFを取得し、`code_url`はcloneせず`gitingest` Python APIで`source.md`へ直接変換する。取得だけに止めたい場合だけ`--no-ingest`を付ける。ただしsource code本体は保存しないため、`--no-ingest`時は`code_url`から`source.md`も作成しない。
`paper.pdf`を保存できない場合は、PMC Free Full Textの公開PDFを先に確認し、それでも取得できない場合にSemantic Scholar `openAccessPdf`を確認する。成功した場合だけ`metadata.yaml`の`pdf_url`、`pmcid`、`access_note`を更新する。取得できない理由は`idea_notes.md`に記録し、`paper.md`は作成しない。未取得のまま残る場合は、手動PDF取得候補URLと保存先を必ず出す。

複数の先行研究をまとめて取得した後、未取得PDFが1件でもある場合は、最終応答に次の表を含める。

```text
paper_id | 手動確認URL | 保存先
```

# ingest

人間が「Markdown化して」と依頼したら:

1. `paper.pdf`があれば`paper.md`へ変換する。
2. PDF変換は`pymupdf4llm`だけを使う。未導入なら`paper.md`を生成せず、別方式のfallbackを追加しない。
3. PDF変換時は`pymupdf4llm.to_markdown(..., write_images=True, image_path="figures", image_format="png", dpi=200)`を使い、論文中の画像を`figures/`へ保存し、`paper.md`内に画像pathを残す。
4. `code_url`があれば、source code本体を保存せず、`gitingest` Python APIで`source.md`へ直接変換する。
5. `code_url`がなく、`source/`が手動配置されている場合だけ、ローカル`source/`から`source.md`へ変換する。
6. source変換は`gitingest` Python packageだけを使う。未導入なら`source.md`を生成せず、内製の軽量fallbackを追加しない。
7. Codexは、依存不足を理由にscriptへ新しい代替変換実装を追加しない。必要なら導入コマンド候補と手動作成の選択肢を人間に提示する。
8. source ingestは軽量に保ち、`gitingest.ingest(..., max_file_size=100 * 1024)`で1ファイル100KB以下を対象にする。
9. `gitingest`の100KB制約、変換失敗、未導入dependencyを`idea_notes.md`または`source.md`冒頭に記録する。
10. `metadata.yaml`の`ingested_at`を更新する。

helper scriptを使う場合:

```bash
uv run python .agents/skills/01-prior-research/scripts/ingest_prior_research.py prior_research/<paper_id>
```

このscriptは、既にある`paper.pdf`を再Markdown化したい場合、または`metadata.yaml`の`code_url`/手動配置した`source/`から`source.md`を再作成したい場合に使う。通常は`download_prior_research.py`が取得後に自動で呼び出す。

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
