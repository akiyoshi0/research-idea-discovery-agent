---
name: research-plan
description: 育った仮説を批判・順位づけし、人間が選んだ仮説だけをresearch_plan.mdとして研究計画にまとめる。critique-rankとwrite-research-planを担当する。
---

# 目的

`00`〜`02`で育てた仮説を、人間が選べる形に整理し、最終的に`discovery_state/research_plan.md`へ落とし込む。

このskillは最終段階を担当する。新しい仮説探索が必要になった場合は`00-idea-discovery`へ戻す。

# 担当するmode

- `critique-rank`
- `write-research-plan`

# 入力

- `discovery_brief.md`
- `discovery_state/field_map.md`
- `discovery_state/gap_table.md`
- `discovery_state/hypothesis_bank.md`
- `discovery_state/decision_log.md`
- `prior_research/*/idea_notes.md`
- `probes/*/probe.md`

# 出力

- `discovery_state/decision_log.md`
- `discovery_state/research_plan.md`
- 必要に応じた`hypothesis_bank.md`の`Selected`更新

# 言語方針

- 説明、`decision_log.md`、`research_plan.md`は日本語で書く。
- データセット名、モデル名、評価指標、file path、Hypothesis IDは原表記を残してよい。

# 基本ルール

- AIだけで最終テーマを決めない。
- 人間が選んだ仮説だけを`research_plan.md`にする。
- 根拠、実行可能性、評価指標、失敗条件、リスクを書く。
- 実行不可能な計画を書かない。
- 未選択の仮説を勝手に採用しない。
- `research_plan.md`は、会話履歴の要約ではなく、単体で読める研究計画書として書く。
- `research_plan.md`には、Codex、人間、ユーザー、あなた、私、我々の議論、これまでの議論、先ほどの指摘、今回のやりとり、などの会話・共同作業のメタ記述を書かない。
- 会話中に決まった内容は、会話の経緯としてではなく、研究上の背景、設計根拠、比較検討、採択理由として書き換える。
- `decision_log.md`には意思決定の経緯を書いてよいが、`research_plan.md`には経緯ではなく結論と研究上の理由を書く。

# 曖昧な呼び出しへの対応

ユーザーが`$research-plan`、`03-research-plan`、`research-plan`のようにskill名だけを指定し、評価したい仮説や選択済みHypothesis IDや依頼内容を書いていない場合:

- skillの中身や`research_plan.md`の章立てを説明しない。
- 「skillを確認しました」「以後この形式に従います」のような確認報告だけで終わらない。
- 次に何をしたいかを短く聞く。
- 候補を出す場合も、次の選択肢だけを簡潔に示す。

返答例:

```text
research-planで何をしますか？

- 仮説を批判・順位づけする
- 選択済み仮説からresearch_plan.mdを書く
- research_plan.mdを会話メタ記述なしで修正する
```

# mode: `critique-rank`

やること:

1. `hypothesis_bank.md`を読む。
2. `prior_research/*/idea_notes.md`と`probes/*/probe.md`を確認する。
3. 各仮説を以下の軸で評価する。

```text
Novelty
Importance
Feasibility
Testability
Evidence
Fit
Data-probe support
```

4. 評価は`High / Medium / Low`に限定する。
5. 採択候補、保留候補、棄却候補を整理する。
6. `decision_log.md`に理由を書く。
7. 人間に最終選択を求める。

やらないこと:

- 0〜100点の複雑な採点をしない。
- AIだけで`Selected`を確定しない。
- 人間の制約を無視しない。

# mode: `write-research-plan`

やること:

1. 人間が選んだHypothesis IDを確認する。
2. `field_map.md`、`gap_table.md`、`hypothesis_bank.md`、`decision_log.md`を読む。
3. `research_plan.md`を書く。
4. 次のResearch Co-Pilot Workspaceへ渡せる粒度にする。

書き方:

- 文体は「本研究は」「本計画では」「提案手法は」のように、研究計画そのものを主語にする。
- 「これまでの議論では」「ユーザーは」「Codexは」「あなたと私の議論では」のような会話参照を使わない。
- 代替案を扱う場合は、「当初の議論」ではなく「候補設計A/Bの比較」として書く。
- 設計変更を扱う場合は、「指摘を受けて修正した」ではなく、「計算効率、表現能力、評価可能性の観点から採択/不採択を判断する」と書く。
- 背景、仮説、根拠、評価、リスクだけを読めば研究計画が理解できるようにする。
- `research_plan.md`を書いた後、禁止表現が混入していないか必ず確認し、見つけたら研究文書として書き換える。

禁止表現の例:

```text
これまでの議論では
前回/先ほど/今回のやりとり
ユーザーの指摘
あなたと私
Codex
エージェント
私たちは議論した
```

変換例:

```text
NG: これまでの議論では、VQGAN tokenizerを使う案を中心にしていた。
OK: 4K画像をtoken gridへ変換する手段として、VQGAN tokenizerとstride-16 CNN encoderを比較対象に置く。

NG: ユーザーの指摘により、CNN encoderでも同じ役割を実現できると分かった。
OK: token grid化という機能要件は、pretrained VQGAN tokenizerだけでなくstride-16 CNN encoderでも満たせるため、両者を計算量、事前学習表現、病理意味表現との接続性で比較する。
```

`research_plan.md`には最低限以下を書く。

```markdown
# 研究計画

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
```

# 戻り条件

以下の場合は、無理に`research_plan.md`を書かずに戻す。

- 仮説の根拠が弱い。
- 先行研究確認が不足している。
- data-probeが必要だが未実施。
- 人間が最終仮説を選んでいない。

戻し先:

- 仮説再考が必要なら`00-idea-discovery`
- 文献・コード確認が必要なら`01-prior-research`
- 軽いデータ確認が必要なら`02-data-probe`

# 失敗時の動作

計画化できない理由を`decision_log.md`に書き、人間に判断を求める。
