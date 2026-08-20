# Mecha Motion Lab L30 — セッション引き継ぎ (2026-07-19 夜 / Claude Fable 5 Cowork)

前提の必読: `trouble_history.md` [T019][T066][T067] / PROMISES [P025][P025-R1] /
技術詳細: `docs/handover/MECHA_L30_DIVEHACK_ARMFIX_HANDOVER_20260719.md`(本セッション作成・FMEA/ロールバック手順含む)

## このセッションで確定した事実

1. **L30ダッシュボードの「learned」表示は実学習の証明ではない**(T066: 旧ml_supervisorはモック)。
   実チェーン = `motion_learning_supervisor.py` + u1〜u7キュー(u7は稼働中)。
2. **7/1のTelegram用歩行動画は関節ゲートが正しくHOLD判定済み**
   (`diagnostics/v50_current_best_walk_telegram_20260701_0528/v50_joint_attachment_gate_report.json`:
   verdict=HOLD_JOINT_DETACHMENT, 腕6関節FAIL/脚6関節PASS)。ユーザーも目視で肩分離を確認。
3. **腕分離の根本原因**: アーマチュアがメッシュから常時1.1〜1.4m変位しており、
   腕メッシュはどの駆動系にも接続されていない「置物」だった。
4. walk_cycle01 は dive_hack(前傾ダイブ+這いで travel を稼ぐ)でエスカレーション。

## 実施済み変更(全て.bakあり / 詳細とFMEAは技術引き継ぎMD参照)

| ファイル | 変更 | バックアップ |
|---|---|---|
| `projects/AtsugiMechaCity/rl_integration/stage_a/train_v50_walk_tracking.py` | 報酬ハードゲート(upright>0.85)・転倒カット0.75・ペナルティ-10 | `.bak_divehack_20260719` |
| `projects/AtsugiMechaCity/rl_integration/autonomy/playbook.yaml` | v4: dive_hack→フレッシュ自動再学習(安全弁不変) | `.bak_20260719` |
| `projects/AtsugiMechaCity/v50_final_walk_preview.py` | 腕をメッシュ駆動FK化+Xスナップ+マーカー/ソケットのメッシュ由来化 | `.bak_armfix_20260719` |

検証済み: py_compile全OK / playbook判定テスト(yaml+miniパーサ)PASS /
bpyスタブ幾何テスト(スナップ・ピボット・FK連続性=ギャップ成長ゼロ)PASS。
**未検証: Windows実機でのBlenderレンダー+関節ゲート実判定**(fail-closedなので不合格時は配信自動ブロック)。

## 現在進行中の状態(2026-07-19 21:15時点)

- **19:06起動の旧コードcycle1がGPU学習中**(プロセスは私の修正前に起動→旧報酬のまま。
  dive_hack再発見込み。supervisorも旧playbook v3をメモリに保持→escalateで終了する)
- **修正版の次ランは装填済み**: スキル依頼 `req_walk_v2_1784462105`(status: retargeted,
  ref: `C:\v50_work\refs\walk.json` = 100STYLE実モーキャップ)が u5 の配車待ち。
  現行ランが終わり次第、自動で修正版コード+playbook v4+実参照(Stage B)で学習開始。
- **明朝6:00にスケジュールタスク** `mecha-walk-training-morning-check` が結果を自動チェックし報告
  (読み取りのみ。タスク定義: `C:\Users\yasu\Claude\Scheduled\mecha-walk-training-morning-check\SKILL.md`)

## 次セッションのTODO(優先順)

1. 朝チェック結果の確認: 修正版ランのメトリクス(vx/travel/fell/min_upright)を
   旧cycle01(vx=0.082, travel=1.513, fell=true)と比較。dive_hack解消の判定。
2. 次回プロモーション時の関節ゲートreportで腕6関節PASSを確認。
   肘が逆曲がりの場合は `v50_final_walk_preview.py` の `ELBOW_SIGN` を -1.0→+1.0。
3. bd起票(サンドボックスにbd CLIなし・未起票):
   - playbook v4 dive_hack自動再学習の効果測定
   - preview腕FKの実機ゲート検証
   - ゲートとpreviewの腕クラスタ定義の単一ソース化
   - 19:06ランを起動した再起動主体の特定(escalations 12:07/13:08/18:11と頻回再起動の出所)
4. トラブル履歴への追記判断(dive_hack対策と腕FK化の恒久記録)。

## 制約メモ(このセッションで実証)

- サンドボックスから GPU学習/Blender実行/Windowsプロセス操作/api.telegram.org は不可。
  D:配下のファイル読み書きと、スキル依頼キュー経由の自動学習発火は可能(今回実証)。
- git はマウント経由で信用しない(T055)→ バックアップは.bak方式を継続。
