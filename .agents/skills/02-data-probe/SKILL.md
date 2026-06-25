---
name: data-probe
description: 仮説の実行可能性を確認するために、公開データ・公開DBを軽く確認し、probes/、data/README.md、hypothesis_bank.mdを更新する。
---

# 目的

仮説が現実的に検証できるかを、公開データと軽いコード確認で見極める。

このskillは本格解析を行わない。仮説を育てるための現実確認だけを担当し、結果は`00-idea-discovery`の`revise-hypotheses`へ戻す。

# 入力

- `discovery_brief.md`
- `discovery_state/hypothesis_bank.md`
- `data/README.md`
- `probes/*/probe.md`
- 必要に応じて公開DB・公開データ

# 出力

```text
data/README.md
probes/<probe_id>/
├── probe.md
├── script.py
├── run.sh
└── outputs/
discovery_state/hypothesis_bank.md
```

# 言語方針

- 説明、`probe.md`、`data/README.md`、`hypothesis_bank.md`更新は日本語で書く。
- DB名、dataset ID、gene symbol、compound ID、metric名、API名、file pathは原表記を残す。

# 文章表現の方針

- `probe.md`と`hypothesis_bank.md`更新は、実験ログではなく、人間が仮説を続けるか判断するための作業メモとして書く。
- 論文由来の英語専門語やmetric名をそのまま並べない。初出では必ず短い日本語説明を添える。
- DB名、dataset ID、gene symbol、compound ID、正式なmetric名は原表記を残してよいが、概念語はできるだけ日本語で噛み砕く。
- 「有意」「改善」「安定」などの曖昧な語だけで終わらせず、何と比べて、どの程度、なぜ次の判断に関係するかを書く。
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

- data-probeは軽い現実確認であり、論文用の本解析ではない。
- 大規模前処理、複雑なML pipeline、最終評価実験を作らない。
- private data、clinical data、個人情報、機密情報を外部サービスへ送らない。
- API key、login、tokenが必要な場合は人間に確認する。
- probe結果だけで最終結論を出さない。

# 曖昧な呼び出しへの対応

ユーザーが`$data-probe`、`02-data-probe`、`data-probe`のようにskill名だけを指定し、対象仮説、確認したい問い、データソースを書いていない場合:

- skillの中身やファイル構造を説明しない。
- 「skillを確認しました」「以後この形式に従います」のような確認報告だけで終わらない。
- 次に何を確認したいかを短く聞く。
- 候補を出す場合も、次の選択肢だけを簡潔に示す。

返答例:

```text
data-probeで何を確認しますか？

- 特定仮説に必要な公開データの有無
- データ形式やサイズ
- 利用制限
- 小さな再現用probeの作成
```

# 使ってよい対象

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
- LINCS L1000 / Connectivity Map
- GEO
- CELLxGENE
- その他の公開データベース

# プローブ作成

人間または`00-idea-discovery`からprobeが必要だと示されたら:

1. 対象仮説と確認したい問いを明確にする。
2. `probes/<probe_id>/`を作る。
3. `probe.md`に問い、関連仮説、データソース、方法を書く。
4. 必要なら小さな`script.py`を書く。
5. `run.sh`で再実行方法を残す。
6. `outputs/`に小さな表、ログ、図だけを置く。

helper scriptを使う場合:

```bash
uv run python .agents/skills/02-data-probe/scripts/init_probe.py <probe_id>
```

# data/README.md更新

使ったデータについて、最低限以下を記録する。

- データソース
- アクセス日
- version
- 含まれる内容
- 取得方法
- 利用制限
- ローカルパス
- 注意点

# hypothesis_bank.md更新

probe後は、対象仮説の以下を更新する。

- `Data probe`
- `状態`
- `実行可能性`
- `更新履歴`

状態の例:

- `Active`
- `Needs prior research`
- `Needs data probe`
- `Revised`
- `Rejected`

# 00への戻し方

probe結果を受けて、`00-idea-discovery`の`revise-hypotheses`で再考できるように、次を明記する。

- 仮説を支持する点
- 仮説を弱める点
- データが足りない点
- 次に必要な先行研究
- 次に必要な追加probe

# 失敗時の動作

データが見つからない、アクセスできない、利用制限がある、APIが使えない場合は、`probe.md`と`data/README.md`に理由を書く。
