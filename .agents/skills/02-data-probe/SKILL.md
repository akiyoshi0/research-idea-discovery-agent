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

# 基本ルール

- data-probeは軽い現実確認であり、論文用の本解析ではない。
- 大規模前処理、複雑なML pipeline、最終評価実験を作らない。
- private data、clinical data、個人情報、機密情報を外部サービスへ送らない。
- API key、login、tokenが必要な場合は人間に確認する。
- probe結果だけで最終結論を出さない。

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
python .agents/skills/02-data-probe/scripts/init_probe.py <probe_id>
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
