---
name: idea-discovery
description: 研究者の関心と制約から分野を整理し、未解決問題、仮説候補、仮説の再考ループを管理する。map-field、find-gaps、generate-hypotheses、revise-hypothesesを担当する。
---

# 目的

研究者が実行可能で検証可能な研究テーマを見つけるために、分野の地図、未解決問題、仮説候補、仮説の更新履歴を管理する。

このskillは探索の司令塔である。先行研究の取得・変換は`01-prior-research`、軽いデータ確認は`02-data-probe`、最終的な批判・研究計画化は`03-research-plan`に渡す。

# 担当するmode

- `map-field`
- `find-gaps`
- `generate-hypotheses`
- `revise-hypotheses`

# 入力

- `discovery_brief.md`
- `discovery_state/field_map.md`
- `discovery_state/gap_table.md`
- `discovery_state/hypothesis_bank.md`
- `prior_research/*/metadata.yaml`
- `prior_research/*/idea_notes.md`
- `prior_research/*/paper.md`
- `prior_research/*/source.md`
- `probes/*/probe.md`

# 出力

- `discovery_state/field_map.md`
- `discovery_state/gap_table.md`
- `discovery_state/hypothesis_bank.md`
- 必要に応じた`discovery_state/decision_log.md`への途中判断ログ

# 言語方針

- 人間が明示的に別言語を指定しない限り、説明とMarkdown更新は日本語で書く。
- データセット名、モデル名、評価指標、遺伝子名、化合物ID、ファイルパス、コマンド、Hypothesis IDは英語や原表記を残してよい。
- 英語論文や英語READMEを読む場合も、長い逐語訳ではなく日本語要約を書く。

# 文章表現の方針

- `field_map.md`、`gap_table.md`、`hypothesis_bank.md`は論文メモではなく、人間が次の判断をするための作業メモとして書く。
- 論文由来の英語専門語をそのまま並べない。初出では必ず短い日本語説明を添える。
- データセット名、モデル名、正式な指標名は原表記を残してよいが、概念語はできるだけ日本語で噛み砕く。
- 「示唆される」「未整理である」を多用せず、「何が分かっていないか」「なぜ困るか」「何を確認すればよいか」を直接書く。
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

- AIだけで最終テーマを決めない。
- 面白いだけの仮説を残さず、検証方法、予想結果、失敗条件を書く。
- 人間の利用可能データ、実験系、計算資源、スキル、避けたいテーマを常に反映する。
- 仮説は一度出して終わりにせず、先行研究やdata-probe結果を受けて更新する。
- 本格解析や論文用実験は行わない。必要なら`02-data-probe`へ軽い確認として渡す。

# 曖昧な呼び出しへの対応

ユーザーが`$idea-discovery`、`00-idea-discovery`、`idea-discovery`のようにskill名だけを指定し、具体的なmodeや対象ファイルや依頼内容を書いていない場合:

- skillの中身やファイル構造を説明しない。
- 「skillを確認しました」「以後この形式に従います」のような確認報告だけで終わらない。
- 次に何をしたいかを短く聞く。
- 候補を出す場合も、次の選択肢だけを簡潔に示す。

返答例:

```text
idea-discoveryで何をしますか？

- 分野を整理する
- gapを探す
- 仮説候補を作る
- 既存仮説を見直す
```

# 開始時に読むもの

1. `discovery_brief.md`
2. `discovery_state/field_map.md`
3. `discovery_state/gap_table.md`
4. `discovery_state/hypothesis_bank.md`
5. 必要に応じて`prior_research/*/idea_notes.md`
6. 必要に応じて`probes/*/probe.md`

# 仮説状態

`hypothesis_bank.md`では、各仮説に状態を持たせる。

```text
Active
Needs prior research
Needs data probe
Revised
Rejected
Selected
```

状態の意味:

- `Active`: 現在の有力候補。
- `Needs prior research`: 先行研究確認が必要。`01-prior-research`へ渡す。
- `Needs data probe`: 軽いデータ確認が必要。`02-data-probe`へ渡す。
- `Revised`: 文献やprobe結果を受けて修正済み。
- `Rejected`: 根拠、実行可能性、新規性、fitのいずれかが弱く棄却。
- `Selected`: 人間が最終候補として選択。

# mode: `map-field`

やること:

- `discovery_brief.md`を読む。
- 分野の主要テーマ、重要論文、重要データセット、重要手法、既知の未解決問題を整理する。
- `discovery_state/field_map.md`を更新する。
- 足りない先行研究があれば、`01-prior-research`へ渡す候補を明記する。

やらないこと:

- 仮説を確定しない。
- `research_plan.md`を書かない。

# mode: `find-gaps`

やること:

- `field_map.md`と利用可能な`prior_research/*/idea_notes.md`を読む。
- 根拠つきで未解決問題を抽出する。
- `discovery_state/gap_table.md`を更新する。
- 重要度と実行可能性を`High / Medium / Low`で整理する。

やらないこと:

- 根拠のないgapを書かない。
- 早すぎる段階でgapを1つに絞らない。

# mode: `generate-hypotheses`

やること:

- `gap_table.md`を読む。
- 複数の仮説候補を作る。
- 各仮説について、状態、関連gap、根拠、必要な先行研究、Data probe、検証方法、予想結果、失敗条件、実行可能性、Fitを書く。
- `discovery_state/hypothesis_bank.md`を更新する。

やらないこと:

- 検証方法がない仮説を残さない。
- 人間の制約に合わない仮説を有力候補にしない。

# mode: `revise-hypotheses`

やること:

- `hypothesis_bank.md`、`prior_research/*/idea_notes.md`、`probes/*/probe.md`を読む。
- 新しい文献情報やprobe結果を受けて仮説を修正、統合、棄却、追加する。
- 状態を更新する。
- 更新理由を`hypothesis_bank.md`の更新履歴または`decision_log.md`に残す。
- 次に必要な作業があれば、`01-prior-research`または`02-data-probe`へ渡す形で明記する。

やらないこと:

- 一度出した仮説を無批判に維持しない。
- probe結果だけで最終結論を出さない。
- 人間の選択なしに`Selected`へ変更しない。

# 他skillへの渡し方

- 先行研究の追加、PDF/source ingest、論文・コード読解が必要なら`01-prior-research`を使う。
- 公開データ確認や軽いコード確認が必要なら`02-data-probe`を使う。
- 候補が十分に育ち、人間が選べる段階になったら`03-research-plan`を使う。

# 失敗時の動作

根拠が足りない場合は「根拠不足」と明記する。
人間の判断が必要な場合は、勝手に進めず質問する。
