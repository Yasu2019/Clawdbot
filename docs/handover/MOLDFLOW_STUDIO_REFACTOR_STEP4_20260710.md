# Moldflow CAE Studio STEP4: Gate Advisor MVP (2026-07-10)

> 作成: Fable5。前段: STEP1-3 (`MOLDFLOW_STUDIO_REFACTOR_STEP1〜3_20260710.md`)
> ユーザー要望「適切なゲート位置を判定してほしい」への回答実装

## 実装内容

### 判定エンジン `scripts/moldflow_gate_advisor.py` (新規・純Python・LLM不使用)

- 固定3インレット(inlet1=x0/inlet2=L2/inlet3=L)の**7組合せを決定論スコアリング**
- メトリクス: 最大流動長(中面グリッド距離) / L/t比 vs 材料別限界(PP150/ABS130/PC100・保守目安) / ウェルドライン位置・本数(隣接ゲート中点) / 充填バランスCV
- スコア重み: 充填余裕45% + ウェルド25% + バランス15% + 流動長15%
- **順位規則: 充填不成立(short_shot_risk)候補は常に成立候補より下位。不成立同士は限界に近い順**(テストが暴いた設計欠陥の修正: ウェルド数が充填可否より優先されていた)
- CLI単体実行可: `python scripts/moldflow_gate_advisor.py --length 100 --width 10 --height 2 --material pp_generic`

### API/UI

- `POST /api/gate-advice` {bbox_mm, thickness_mm?, material_id?} → 7候補ランキング+assumptions
- UI「Gate Advisor」パネル(ensure*Panelパターン): ランキング表(FILL OK/SHORT SHOT RISKタグ・全メトリクス開示)+Applyボタンでゲートチェックボックスへ反映

## 検証

- `tests/test_moldflow_gate_advisor.py` **12件PASS**(解析解: 中央1点maxL=50.99/端点100.50/3点26.93、ウェルド位置x=50、560mm板でのL/t逆転、全不成立時のmargin順位、決定論性)
- 既存テスト含め22件PASS / py_compile / node --check PASS

## 制約(UIのassumptionsにも表示)

- **平板bbox近似・障害物なし**。Moldflow本家BGA相当ではない一次スクリーニング(精度L3級)
- L/t限界は一般的目安で**実測未校正** — L6(実測相関)達成時に校正すること
- 最終判断は人間。スコアは判断材料の開示が目的

## 発効条件

`scripts\restart_moldflow_studio_api.bat` をダブルクリック(API再起動)+ブラウザリロード

## 次の拡張候補(未実装・bd起票要)

- Tier2: 上位候補をexport-job経由でOpenFOAM実検証(既存DOE基盤流用)
- STEP実形状の外形ポリゴン利用(bbox→実形状距離場)
