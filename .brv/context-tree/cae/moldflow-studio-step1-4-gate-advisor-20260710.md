# Moldflow CAE Studio STEP1-4 + Gate Advisor (2026-07-10 Fable5)

## 要点
- ChatGPT改造(7/8-7/9: solver-landscape/learned-params/readiness)を含む未追跡アプリ一式をSTEP1でベースラインcommit
- STEP2: import cgi(Py3.13削除)→自前_parse_multipart(512MB上限)。テスト7件
- STEP3: /api/maturity(26h鮮度判定付き)+/api/golden-error-trend+UIパネル。maturity_latest.jsonが7/8 05:31から更新停止を発見(要調査)
- STEP4: Gate Advisor=固定3インレット7組合せの決定論スコア(最大流動長/L/t限界PP150・ABS130・PC100/ウェルド推定/バランスCV)。**充填不成立候補は常に下位**(テストが順位欠陥を暴いた)。平板近似・実測未校正=L3級
- API再起動bat: kill-by-port-8776方式v2(孤児2匹実在した)

## 参照
- 引継ぎ: docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP1〜4_20260710.md
- テスト: data/workspace/tests/test_moldflow_studio_api_multipart.py(10) / test_moldflow_gate_advisor.py(12)
- commit: 3f0b65d/4509bd1/0c2e19e/8fba84e/61cb3a1/1629917
- bd起票要: moldflow-studio-step1-4記録 / maturity日次更新停止調査 / gate-advisor Tier2(OpenFOAM実検証)
