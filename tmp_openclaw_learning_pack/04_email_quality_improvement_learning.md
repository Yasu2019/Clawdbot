# 04. Email / 品質問題 / 改善活動 学習仕様

## 4.1 Emailは学習対象にすべきか
はい。品質実務では、以下がメールに強く表れる。
- 相手が本当に欲しい回答
- 単なる事実列挙では足りない点
- 暫定対策→恒久対策の変遷
- 社内と社外の認識差
- 返信不足で揉める論点

## 4.2 追加コレクション
- `email_thread_memory`
- `email_fact_memory`
- `email_judgement_memory`
- `quality_issue_memory`
- `improvement_activity_memory`
- `lesson_memory`

## 4.3 品質問題点の学習対象
- 不具合票
- 再発防止票
- 是正処置報告
- 監査不適合
- 改善の機会
- 会議議事録
- 口頭情報の文字起こし

### quality_issue_memory 推奨項目
- issue_id
- title
- lot_no
- part_number
- process
- defect_name
- symptom
- containment_action
- suspected_root_cause
- permanent_action
- due_date
- owner
- verification_result
- status

## 4.4 改善活動の学習対象
- 改善提案書
- 工程改善活動
- ポカヨケ導入
- 検査強化
- 監視方法変更
- DR / PFMEA 反映結果

### improvement_activity_memory 推奨項目
- activity_id
- source_org
- title
- target_process
- trigger_issue
- before_state
- after_state
- change_type
- expected_effect
- measured_effect
- side_effect
- rollout_scope
- horizontal_deployment
- result_status

## 4.5 一般化教訓の抽出
過去勤務先のメールや改善活動から、社名・顧客名・型番を落として一般化する。

例:
- 悪い保存: `FoxconnのA顧客向けX部品は...`
- 良い保存: `高温工程後の表面外観不良では、更新履歴の有無だけでなく相関の見解提示が求められやすい`

これを `lesson_memory` に保存する。

## 4.6 Email返信支援の判断観点
- 相手の主要求を満たしているか
- 相関有無の見解が明示されているか
- 根拠が書かれているか
- 断定しすぎていないか
- 添付参照と本文が一致しているか
- 控えめで丁寧か
- 未回答論点が残っていないか
