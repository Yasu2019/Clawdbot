---
tags: [portal, cetol, visual-inspection, fact-bar, truth-gate, T082]
incident: INC-189
trouble_id: T082
bd_key: app-page-fact-bar-cetol-viai-20260827
updated: 2026-08-28
---

# INC-189 / T082: アプリ画面を最新FACTに揃える / CETOL inline JS 沈黙

## Summary

- **NG trial**: CETOL ページが「cetol_reports.json を読み込んでいます」のまま。JSON は 200 / 260KB。golden PASS も STALE も見えない。
- **OK trial**: 重複 `else` 削除後、30件セレクタ + FACT `golden PASS 2026-08-26 max_err=0.512%` / `reports 2026-07-15 30件 STALE`。Moldflow / VIAI / FEM / OpenRadioss も同じFACT様式。
- **Impact**: 古いCpkカードや読込中画面を現行・商用相当と誤読するリスク。北極星の公差トラックが見えない。

## QC工程表

| Step | 管理ポイント | 合格基準 |
|---|---|---|
| 1. HTTP | index + JSON | 8088/18010 が 200。OpenRadioss コンテナは止めない |
| 2. Parse | 巨大inline script | 抽出して `node --check` が通る。`typeof fmt !== "undefined"` |
| 3. FACT | live JSON | 日付 + trial_id / golden / STALE / SKIP を同一バーに出す |
| 4. Truth Gate | 文言 | 商用Cetol / Moldflow / AOI / せん断完了 と書かない |
| 5. Portal | カード文 | 各アプリFACTと一致 |
| 6. Browser | innerText | HTTP 200 ではなくバー文字列で合格 |

## FMEA

| Failure mode | 影響 | S | O | D | RPN | 対策 |
|---|---|---:|---:|---:|---:|---|
| inline SyntaxError | FACT/レポート全滅 | 8 | 6 | 4 | 192 | node --check + 独立IIFE |
| STALEを現行扱い | 誤った公差判断 | 9 | 5 | 3 | 135 | 生成時刻とSTALEをバーに出す |
| golden PASS=商用Cetol | Truth Gate違反 | 9 | 4 | 4 | 144 | 1D stack と明記し同等否定 |
| VIAIを8088で探す | 接続エラー | 6 | 4 | 2 | 48 | :18010 /api/health |
| 8/3 fill 63.6%を現行 | P026違反 | 8 | 3 | 3 | 72 | fill_complete=1 の 8/23 99.55% のみ現行 |

## FTA / 5 Why

- **TOP**: CETOL画面がデータ無しに見える
- **Why1**: fetch then() が走らない
- **Why2**: メインscriptがパース失敗 (`fmt` undefined)
- **Why3**: snap_fit 閉じの後に軸受アニメが重複
- **Why4**: その直後の `else if bolt_joint` が文法エラー
- **Why5**: FACTローダが同一巨大script末尾で、構文エラーの影響を隔離していない

## Fishbone (4M1E)

- Method: 巨大inlineにFACTを足すと一点故障
- Machine: portal_server :8088 vs VIAI :18010 の取り違え
- Material: cetol_reports.json はSTALE、goldenは別系統
- Man: HTTP 200を画面合格と誤認
- Environment: F: 6.4% で tri-track SKIP_STORAGE（ループ生存≠進化）

## Logical Tree

- 画面が古い/空
  - JSONが無い -> パス確認
  - JSONはある -> script死 / FACT未配線
  - JSONは新しいが文言が商用 -> Truth Gate

## Countermeasures

1. 巨大script編集後は必ず `node --check`
2. FACTバーは live JSON + 日付 + 非商用注記
3. Portalカードを同じFACTに同期
4. reports再生成は K10 `cetol_app_report_builder.py`（未実施、STALEのまま明示）

## Forbidden

- MeshNow/HTTP 200/Cpkカードだけで SUCCESS
- 商用Cetol 6 Sigma / Moldflow / 量産MSA / せん断完了 の主張
- OpenRadioss 計算コンテナをFACT更新のために止める
- `fill_complete=0` の旧充填を現行成功として出す

## Links

- Canonical: `docs/knowledge/app_page_fact_bar_cetol_viai_20260827.md`
- `docs/INCIDENT_LOG.md` INC-189
- `data/workspace/memory/trouble_history.md` T082
- `data/workspace/memory/success_cases.md` S033
- bd key: `app-page-fact-bar-cetol-viai-20260827`
