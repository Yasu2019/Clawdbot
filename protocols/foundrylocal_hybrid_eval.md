# Foundry Local 併用評価プロトコル（再生成版）

## 概要
- Ollama を **主系**（日常運用の生成系）として維持する
- Foundry（Foundry Local / Foundry 側の実行）を **比較系**（評価・差分観測）として併用する
- Foundry を外しても、即座に Ollama 単独へ戻せる（rollback 可能）構成を崩さない

## 目的
- 主系（Ollama）の品質・安全性・コストの基準を維持しつつ、比較系（Foundry）の有効性を定量/定性で検証する
- 「全面移行」ではなく「併用での観測」に限定し、運用停止リスクを最小化する

## 原則（安全ガード）
- 自動送信・自動削除・破壊的更新は行わない（read-only / 観測のみを優先）
- 評価結果（推論・スコア）を raw/fact データに混在させない
- 併用は feature flag / 明示スイッチで切替可能にする
- 1モデル必須の設計にしない（Foundry は比較系として任意）

## 実施フロー（最小）
1. **同一入力**（プロンプト/コンテキスト）を Ollama と Foundry に投入
2. 出力を並列に保存（モデル名・バージョン・日時・温度等のメタ情報つき）
3. 差分観測（正確性/関連性/安全性/編集工数/レイテンシ/リトライ回数）
4. 「採用判断」：ADOPT / ADOPT_PARTIAL / HOLD / ROLLBACK を短く記録

## 評価観点（例）
- correctness / relevance（要件適合、幻覚、ノイズ）
- human revision effort（人手の修正量）
- latency / retry waste（速度、無駄な再試行）
- safety regression（危険な出力や逸脱の増加）

## ロールバック
- Foundry を無効化（比較系の呼び出し停止）しても、Ollama 主系が単独で完結すること
- 併用導入で主系の依存関係を増やさない（設定・ルーティング・DB など）

## 実行ツール（任意）
- `scripts/hybrid_eval/hybrid_eval.py`（read-only / 観測のみ）
- Foundry を止めたい場合は `--foundry-cmd` を外すだけで即 rollback

## 完全版プロトコル（参考）
- `protocols/foundrylocal_complete_protocol_20260416/INDEX.md`（段階導入・判断基準・テンプレ一式）

## 由来（ZIP 収録文の要約）
- 「Ollama を主系、Foundry を比較系として併用する評価プロトコル」
- 「Foundry を外せば即 Ollama に戻せる構成を維持」
