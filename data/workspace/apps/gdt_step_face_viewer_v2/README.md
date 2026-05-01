# GD&T 3D HTML Viewer ノウハウ移管パッケージ

本ZIPは、本日の NZGLG7-01 GD&T HTML v6 と、これまでの STEP/PDF/HTML 可視化トラブルから得た知見を、ミニPC上の OpenClaw / Codex / ローカルLLM（Qwen, Gemma系）へ引き渡すためのものです。

## Codexに判断してほしいこと

1. 既存アプリへ融合すべきか
2. 別Portalカードとして試験導入すべきか
3. ノウハウだけ protocol registry / failure memory に追加すべきか
4. face_map / gdt_overlay / evidence_report の分離設計を既存アプリに追加すべきか

## 重要原則

- STEP由来メッシュだけでは STEP面ベース と呼ばない。
- step_face_exact と呼ぶには face_id / axis_id / provenance / 4視点検証が必要。
- 図面記号は datum / section / detail を分類する。
- 直角度は φ 記号の有無を確認する。
- 面の輪郭度は外/内シェルで表現する方が誤解が少ない。
- 3D描画中の項目だけ左カードをハイライトする。
- 進捗表示を入れて、フリーズに見えないUIにする。
- 未確認項目は candidate / unverified と表示する。

## 文字コード

全テキストは UTF-8 with BOM です。
