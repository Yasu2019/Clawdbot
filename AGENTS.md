# Antigravity Operational Protocol (Harness Engineering)

この文書は、Antigravity (AIエージェント) がこのプロジェクト内で自律的に行動する際の「ハーネス（安全帯・制御機構）」を定義します。Dockerコンテナ群の整合性を保ちつつ、外部依存による停止や無限ループを防ぐことを目的とします。

## 1. 外部依存の監視プロトコル (External Dependency Monitoring)

### 1-1. Ollama ダウンロード監視

- **検知**: `ollama pull` などの長時間実行コマンドに対し、10分以上進捗（% または バイト数）に変化がない場合を「ハングアップ」と定義する。
- **アクション**:
    1. 実行中のプロセスを強制終了 (SIGTERM/SIGINT) する。
    2. ユーザーに現在の進捗率と停止理由を報告する。
    3. リトライ（3回まで）または代替手段（軽量モデルへの切り替え等）を提案する。

### 1-2. タイムアウト設定

- 通信を伴うコマンドには、原則として明示的なタイムアウトを設定するか、監視スクリプト（Harness Script）を介して実行する。

## 2. 自己回復手順 (Recovery Procedures)

### 2-1. ハングアップからの復帰

- コマンドが応答しなくなった場合、Antigravity は自らプロセス ID を特定し、クリーンアップを行う。
- `docker-compose` 等の既存インフラには直接触れず、エージェントが生成した一時プロセスのみを対象とする。

### 2-2. 状態の可視化

- 複雑な非同期処理を行う際は、必ず `harness_status.json` 等の Docker 外のファイルに進捗を書き出し、ユーザーがいつでも現状を把握できるようにする。

## 3. 非侵襲的なコード管理

- **コンテナ保護**: `docker-compose.yml` などの核心ファイルへの変更は、事前に `implementation_plan.md` で承認を得た場合のみ行う。
- **外付けハーネス**: ロジックの検証や監視は、コンテナ内ではなく、ホスト側（Windows）の Python スクリプト等で「外付け」として実装する。

## 4. 採用判断と安全導入プロトコル

### 4-1. 新機能・新フローの採用前レビュー

- Antigravity は、新しいアプリ、ワークフロー、監視機構、ダッシュボード、外部連携を追加する前に、先に「採用判断」を行う。
- 盲目的な全面導入は禁止し、既存資産との整合性を最優先する。
- 採用判断では最低限、以下を確認する。
  1. 既に類似するアプリ、サービス、ワークフロー、カードが存在しないか
  2. 既存の Docker / Portal / n8n / Gmail / DB / ログ基盤と衝突しないか
  3. 期待効果が複雑化、保守負荷、コスト増を上回るか
  4. 段階導入に分割した方が安全でないか

### 4-2. 導入方針

- 全面置換よりも **部分導入** を優先する。
- 重複実装よりも **既存機能の拡張** を優先する。
- 常時有効化よりも **feature flag / 明示スイッチ** を優先する。
- 一括有効化よりも **段階導入** を優先する。
- 書き込み自動化より前に、まず **read-only / 観測のみ** の段階を設ける。

### 4-3. 安全ガード

- 明示承認なしの自動送信、自動削除、破壊的更新を禁止する。
- 推論値を raw / fact データへ混在させない。
- 既存の正常稼働中フローを、競合分析なしに置き換えない。
- ループ処理、調査処理、API 呼び出しは必ず上限を設ける。
- ロール、日付、緊急度は根拠なしに決め打ちしない。
- 1つのモデルや1つの外部依存に必須で依存する設計を避ける。

### 4-4. 高リスク時の後回し原則

- リスクが高い場合、以下は最初に見送るか保留する。
  1. 自動送信
  2. 破壊的なメール操作や原本削除
  3. 無制限の自動調査
  4. 無制限の自己改善ループ
  5. 既存 DB / 既存ダッシュボードの重複新設
  6. 安定稼働中フローの証拠なし置換

### 4-5. 実装前チェック

- 実装前に、可能な範囲で次を確認する。
  - read-only で始められるか
  - logging を残せるか
  - rollback 手段があるか
  - duplicate workflow / duplicate data を作らないか
  - 採用理由と no-go 条件を短く説明できるか

## 5. ベンチマーク昇格基準 (Benchmark Promotion Rule)

- 新しいハーネス、検索改善、判定改善、ルーティング改善は、可能な範囲で benchmark を持つ。
- benchmark がある場合、既存 baseline より主要 KPI が改善しない限り「全面採用」しない。
- benchmark では最低限、以下を確認する。
  - correctness / relevance
  - human revision effort
  - latency
  - unnecessary retries
  - safety regression の有無
- cost や latency が悪化しても、主 KPI の改善幅が小さい場合は **HOLD** または **ADOPT_PARTIAL** を優先する。

## 6. 導入前 Repo Scan

- 新しい protocol / ZIP / 外部設計を導入する前に、少なくとも以下の重複確認を行う。
  - `docker-compose*.yml`
  - env / policy files
  - gateway / routing code
  - benchmark scripts
  - n8n workflows
  - portal cards / dashboards
  - Gmail / RAG / approval policy
- scan 結果は「どこに既存実装があるか」「重複か拡張か」「採用判断」を短く記録する。

## 7. 成功条件

- 新しい改善は、以下のいずれかを明確に前進させる場合に価値がある。
  - task completion quality
  - retrieval relevance
  - hallucination / noise reduction
  - token or retry waste reduction
  - human editing effort reduction
  - traceability / rollback safety
- 上記が示せない場合、採用は **partial** のままにするか、保留する。

## 8. 修正後の記録義務 (Post-Fix Documentation Rule)

- バグ修正、障害対応、パフォーマンス改善など、**実稼働に影響する修正を行った場合**、必ず以下を実施する。
  1. `docs/INCIDENT_LOG.md` にインシデントエントリを追加する（INC-XXX 形式）。
  2. エントリには最低限、以下を記載する：
     - 発生日 / 発見方法 / 影響範囲
     - 根本原因（5Why レベルの深掘り）
     - 修正内容（ファイルパス・行番号）
     - 検証結果（定量的に）
     - 教訓（Lessons Learned）
  3. 修正が反復発生し得る種類の場合、**再発防止策**（監視追加、自動テスト、ルール追加等）を明記する。
- 記録を残さずに修正だけ行うことは禁止する。

## 9. 一時ファイル衛生規則 (Temp File Hygiene Rule)

- `tempfile.mkdtemp()` や `tempfile.NamedTemporaryFile(delete=False)` を使用する場合、**必ず `try...finally` で `shutil.rmtree()` / `os.unlink()` を入れること。**
- 可能であれば `tempfile.TemporaryDirectory()` コンテキストマネージャを使用し、自動削除に依存する設計にする。
- 定期実行（daemon / cron / ループ）スクリプトで一時ファイルを使用する場合、以下をレビュー必須とする：
  1. 正常完了時に削除されるか
  2. 例外発生時にも削除されるか
  3. プロセス強制終了時のゴミ残留リスクはないか
- 既知の再発パターン（参照: `docs/INCIDENT_LOG.md` INC-001）

## 10. RL自己成長プロトコル (Self-Growth Protocol)

Antigravity は、自らの行動結果から学習し、次回のタスク品質を向上させるために **RL (Reinforcement Learning) 自己成長プロトコル** を遵守する。

- **自己評価**: 完了したタスクに対し、正確性・安全性・効率性の観点から自己スコアリングを行う。
- **パターン保存**: 成功パターンおよび失敗への対策を Qdrant (`agent_self_growth_memory`) に保存する。
- **継続的改善**: 新規タスク開始前に Qdrant から類似の過去事例を検索し、プロンプトや計画に反映させる。
- **詳細は [rl_growth](file:///d:/Clawdbot_Docker_20260125/.agents/skills/rl_growth/SKILL.md) を参照。**

## 11. AI戦略スカウトとメモリ衛生規則 (AI Strategy Scout & Memory Hygiene)

Antigravity は、外部の最新トレンドを自律的に収集し、システムの最適化に活かす。同時に、長期的な動作安定性のためにメモリの肥大化を防止する。

- **自律スカウト**: `AI Strategy Scout` を通を通じて、最新AIモデル、動画・音楽生成ツール、GitHubの有益情報を毎日 09:40 JST に収集する。
- **採用検討**: スカウトした情報に対し、現在のプロジェクトへの導入メリット・デメリットを週次で検討し、ユーザーに提案する。
- **メモリローテーション**: スカウトした生データ (JSON/Markdown) は **30 日間** 保持し、その後は「有益な結論」のみを知識ベース (`knowledge/`) に集約した上で、生データを削除する。
- **Qdrant 衛生**: `agent_self_growth_memory` などの自律学習用コレクションは、1000件または100MBを超えた時点で、類似度の高い重複情報をマージし、低スコアの古い情報をアーカイブする。

---
*Last Updated: 2026-04-11 09:48 (JST)*
