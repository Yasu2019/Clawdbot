# スキル獲得パイプライン設計 (Skill Acquisition Pipeline) v1.0-draft

作成日: 2026-07-03 | bd: `Clawdbot_Docker_20260125-6li`
要求(ユーザー原文): 「介助する、工場作業、MOST基本動作、サーブリック基本動作、格闘技動作、スポーツ動作など、あとからユーザーが覚えてほしい動作をローカルLLM経由で依頼すれば、世界中のWebから適切な先生データを読み込んで機械学習する」

## 0. 全体像（依頼→登録までの9ステージ）

```
[S1 依頼] → [S2 解釈/分類] → [S3 探索] → [S4 取得] → [S5 ライセンスゲート(人間)]
 → [S6 リターゲット] → [S7 物理検証] → [S8 学習] → [S9 登録/検収]
```

**自動で回る**: S2,S3,S4,S6,S7,S8 | **人間必須**: S5(法的判断), S9(品質検収)
**思想**: QC工程表と同じ「コマンド+数値基準+NG時停止」。各ステージがJSONレポートを残し、途中停止からの再開が可能。

## 1. ステージ定義

### S1: 依頼受付
- 入力: 自然言語(例:「介助動作を覚えて」「サーブリッグの<つかむ>を覚えて」)
- 経路: Telegram/コンソール → ローカルLLM(`local_fast`=qwen3:8b, 無料)

### S2: 解釈・分類（ローカルLLM）
- 出力(JSON): `{skill_name, taxonomy, required_tier, search_queries[], expected_sources[]}`
- **taxonomy語彙(固定)**: `locomotion | posture | manipulation | care_assist | factory_work | most_basic | therblig | martial_arts | sports`
  - MOST基本動作 → `most_basic`(A:歩く/B:体の動作/G:つかむ/P:置く 等にサブタグ)
  - サーブリッグ18動素 → `therblig`(TE:手を伸ばす/G:つかむ/TL:運ぶ/P:位置決め 等)
- **required_tier判定表**: locomotion/posture→Tier1、manipulation/factory/most/therblig/care→**Tier2**、martial_arts/sports→Tier2(近似)〜Tier3(将来)
- 機体のdof_locksがrequired_tierを満たさない場合: **この時点で停止し「その機体では学べない」と報告**(無理に学習しない)

### S3: 探索（自動・無料）
- 一次: 既知データセット表(HANDOVER_TO_CODEX §3: 100STYLES/PHUMA/CMU/AMASS/Bandai/AIST++)へのマッチング
- 二次: SearXNG(`http://localhost:8081`, ローカル)で `<動作名> BVH dataset / motion capture dataset / <動作名> video` を検索
- 三次(データが無い動作): **生成経路** — MoMask(テキスト→モーション)で候補クリップ生成
- 出力: 候補リスト `{url, format(bvh|fbx|smpl|video|generated), license_claim, quality_hint}`

### S4: 取得（自動）
- データセット: DL+形式判定(BVH/FBX/SMPL-NPZ)
- **動画経路**(格闘技・スポーツ・介助はここが主力): WHAM または ROMP/TRACE(Apache-2.0, 調査済み)で動画→3Dモーション抽出
- 保存: `design/skill_library/<skill_name>/raw/` + `acquisition_report.json`

### S5: ライセンスゲート（**人間必須・自動化禁止**）
- 提示: 出典URL・ライセンス表記・用途(学習データ)を人間へ
- 判定基準: CC0/CC BY/Apache/MIT → OK | **CC BY-NC**(Bandai等) → 非商用限定の明示承認 | 学術限定(AMASS) → 用途確認 | 出所不明動画 → **原則棄却**(著作権/肖像権)
- 記録: `license_decision.json`(承認者・日付・条件)。**この記録が無いクリップは以後のステージが受け付けない**

### S6: リターゲット（自動）
- 入力スケルトン(SMPL/BVH各種) → **カノニカル29DOF**へ変換
- 実装: ボーン名マッピング表+IKベースの再解釈(Blenderヘッドレス)。Tier外DOFへの成分は破棄記録
- QC: 足接地率・関節可動域超過チェック(数値基準、robotics_gait_motion_algorithm.py の知見を流用)

### S7: 物理検証（自動・ローカルGPU）
- Genesis上でDiffMimic式トラッキング: 参照クリップを物理シミュで追従できるか
- 合格基準: 追従誤差・転倒率の閾値(Stage A実装時に校正)
- 不合格クリップは自動除外(理由をレポートに記録)

### S8: 学習（自動・ローカルGPU）
- スキル埋め込みテーブルに新規行`z_new`を追加 → 条件付きAMP+PPOで**既存スキルとのリプレイ混合ファインチューン**(破滅的忘却対策: 旧スキルのバッチを20-30%混ぜる)
- 成果: 更新チェックポイント+新スキルの評価動画

### S9: 登録・検収（人間）
- スキル登録簿(§2)に行追加、評価動画をTelegramでユーザー検収
- 検収NG → S2の分類 or S3の候補選定へ差し戻し(理由を登録簿に記録)

## 2. スキル登録簿スキーマ (`design/skill_registry.yaml`)

```yaml
schema: clawstack.skill_registry.v1
skills:
  - name: walk_basic
    taxonomy: locomotion
    tier: 1
    status: enum            # requested|acquiring|license_pending|training|trained|approved|rejected
    embedding_id: int       # 埋め込みテーブルの行番号(不変)
    reference_clips:
      - {path: ..., source_url: ..., license: ..., license_decision: path, s7_report: path}
    checkpoints: {latest: path, approved: path}
    qa: {eval_video: path, user_verdict: null|ok|ng, notes: str}
```

## 3. コスト構造（ユーザー質問への回答を設計に固定）

| ステージ | 実行主体 | APIコスト |
|---|---|---|
| S2解釈 | ローカルLLM(qwen3:8b) | **ゼロ** |
| S3-S4探索取得 | SearXNG+スクリプト | **ゼロ** |
| S6-S8学習系 | Blender/Genesis(ローカルGPU) | **ゼロ** |
| S5/S9人間ゲート | ユーザー | ゼロ(時間のみ) |
| 異常時デバッグ | Claude等(必要時のみ) | 有料(例外時のみ) |

## 4. 実装順序（Stage A〜Cとの統合）

1. Stage A(DiffMimicトラッキング)実装 = **S7の実体**を先に作る
2. S6リターゲッタ(100STYLES→カノニカル) = Stage Bの一部
3. S8条件付き学習 = Stage C
4. S1-S5の自動配線(n8nワークフロー+ローカルLLM)は**最後**(中身が動いてから蛇口を付ける)

## 5. 難易度の正直な明記

- locomotion/posture/factory定型: 実現性高い(先行事例多数)
- most_basic/therblig: グリッパー抽象化の範囲で実現可能。精密な指先作業はTier3待ち
- care_assist(介助): 対人接触の物理(2体問題)は**研究フロンティア**。当面は単体動作(支える姿勢等)の形から学習
- martial_arts/sports: 高動的・接触リッチで最難関。動画→モーキャップの品質が律速。**期待値調整: 「見た目がそれらしい動作」までは到達可能、「実戦的な動作」は長期目標**
