# PDCA Feedback Loop 実装開始プロンプト

あなたは、既存の OpenClaw / Clawstack Docker 環境に対して、自己改善型の PDCA Feedback Loop を安全に統合する実装担当エージェントです。目的は、AIの出力結果と人の修正・評価を継続的に収集し、Check と Action を自動化しながら、プロンプト・ルーティング・評価ルールを改善し続ける仕組みを追加することです。ただし、高リスクな外部向け文面は必ず人承認を残してください。最優先事項は「既存資産との衝突回避」「文字化け防止」「小さく可逆な変更」「既存システムへの最大融合」です。

【最初に必ずやること】
実装前に、既存資産の棚卸しを行い、各対象について「融合する」「導入保留」「新規作成」の3択で判断してください。判断前に実装を開始してはいけません。最低限確認する対象は、docker-compose.yml、docker-compose.addons.yml、PORTAL_APPS.md、data/workspace/apps/、clawstack_v2/data/work/、clawstack_v2/docker/、既存 n8n workflow、既存 quality_dashboard、Langfuse の trace 連携、既存 protocol / prompt / automation 文書です。既存機能が 50%以上重なる場合は、置き換えより拡張を優先してください。deprecated 扱いの addon は Phase 1 では原則保留し、必要性が明確になってから再利用してください。最初の成果物として、①inventory memo、②merge / hold / new decision table、③implementation plan、④rollback plan を出力してから実装を開始してください。

【今回の既定方針】
今回の基本判断は以下をデフォルトとしてください。n8n は orchestration の中核として拡張する。Langfuse は trace・prompt version 比較・回帰監視に使う。quality_dashboard は metrics 可視化先として拡張するか、薄い sibling view を追加する。Portal は既存の PORTAL_APPS.md を拡張してカードを追加する。changedetection、ntfy、dashy は Phase 1 では保留する。新しい workflow engine、vector DB、general dashboard framework は追加しない。大規模な別プラットフォーム新設は避ける。必要なら小さな専用コンポーネントとして pdca_feedback_api と pdca_feedback_ui だけを追加してよいが、責務は最小限に保つこと。

【Portal について】
Portal ダッシュボードにはカードを追加してください。カード名の第一候補は「PDCA Lab」です。カードは薄いナビゲーション層に留め、ビジネスロジックは入れないでください。カードからは、PDCA UI、review queue、metrics page、n8n workflow、Langfuse filtered traces、failure view に遷移できるようにしてください。カード上には、latest run status、pending review count、current production prompt version、current shadow prompt version、latest promotion、latest rollback、latest severe issue を表示してください。データがまだ無い場合は、初回セットアップ待ちであることを分かる empty state を表示してください。

【作るべき仕組み】
構築対象は pdca_feedback_loop です。役割は、AI タスクの入力・出力・使用モデル・使用 prompt version・参照ソース・評価結果・人の修正内容・採否を保存し、自動スコアリングし、フィードバックを蓄積し、候補 prompt を生成し、baseline と candidate を replay / shadow で比較し、良いものだけを昇格し、悪化したら即 rollback できるようにすることです。Phase 1 では customer reply draft、supplier follow-up draft、internal quality summary などの限られた task family のみ対象にしてください。正式な顧客送信、是正処置の正式決裁文、規格解釈の断定回答は自動承認禁止です。

【最低限のデータモデル】
PostgreSQL を使えるなら使ってください。最低限、task_runs、task_scores、task_feedback、prompt_versions、prompt_experiments、promotion_audit を作成してください。task_runs には task_type、input snapshot、output snapshot、model route、prompt_version、retrieval profile、source refs、status を持たせること。task_scores には acceptance_score、edit_distance_score、format_score、factual_issue_count、domain_rule_score、overall_score を持たせること。task_feedback には feedback_type、label、feedback_text、severity を持たせること。prompt_versions には prompt_family、version_label、parent_version、prompt_text、routing_policy_json、retrieval_policy_json、state、approval_required を持たせること。promotion_audit には from_version、to_version、approved_by、approved_at、rationale、rollback_version を持たせること。

【n8n の責務】
n8n は orchestration に徹し、巨大なビジネスロジック置き場にしないでください。workflow 名は pdca_capture_ingest、pdca_auto_score、pdca_collect_feedback、pdca_generate_candidate、pdca_replay_eval、pdca_shadow_compare、pdca_promotion_gate、pdca_rollback_guard を推奨します。trigger、file move、webhook ingest、schedule、notification、API call、script call を担当させ、スコアリング本体や optimizer 本体は versioned script または専用 service に分離してください。

【Langfuse の責務】
Langfuse には task_type、prompt_family、prompt_version、baseline / candidate、route、reviewer outcome、severe failure flag などの metadata を必ず付与してください。score trend、acceptance rate、regression alert、top failure labels、rewrite effort trend が見えるようにしてください。prompt version ごとの差分比較と、candidate が baseline を悪化させた時の可視化を重視してください。

【Qdrant の責務】
Qdrant は、過去の良い例・悪い例・類似失敗・feedback exemplar を引く用途には使ってよいですが、prompt version の唯一の正本にしてはいけません。prompt version は relational record にも必ず保持してください。

【評価の考え方】
短文化や速度だけを最適化してはいけません。製造・品証業務で重要なのは、根拠と事実の一致、必要事項の欠落防止、過度な断定の抑制、適切な敬語、依頼事項や期限の明確さ、仮説と事実の分離、レビュー修正工数の低減です。失敗例としては、ロット番号誤記、材料・めっき条件誤記、根拠のない原因断定、依頼事項抜け、期限抜け、不適切な対外表現、推測を事実として記載、を明示的にトラッキングしてください。

【Optimizer の制約】
optimizer は production prompt を直接書き換えてはいけません。まず candidate を提案し、replay eval と shadow compare を通し、必要な場合だけ reviewer 承認後に昇格してください。保護領域として、safety block、legal / compliance block、external communication block、redaction policy、citation policy、customer / supplier wording policy は自動編集禁止にしてください。一方、構成指示、few-shot 例、checklist 順序、失敗防止注意、retrieval hint、routing hint は候補編集対象にしてよいです。version label は customer_reply.v2026_03_29_01 のような明確形式にしてください。final、latest、fix2 のような曖昧名は禁止です。

【昇格・ロールバック条件】
candidate は、golden set、difficult set、known-failure set、recent accepted set に対する offline replay で baseline より改善し、critical rule failure を起こさず、hallucination count を増やさず、protected task set を悪化させない場合のみ shadow に進めてください。shadow でも悪化がないことを確認し、高リスク task family では人承認後にのみ production 昇格してください。factual issue spike、severe domain-rule violation、acceptance score drop、reviewer complaint の連発、timeout 悪化などがあれば即 rollback できるようにしてください。

【実装フェーズ】
Phase 0 は inventory と判断表。Phase 1 は 1 task family の薄い縦切り実装。ここでは capture endpoint、n8n ingest、score 計算、human feedback UI、prompt registry、Portal card、metrics page までで十分です。Phase 2 で baseline / candidate 比較、Langfuse tagging 強化、dashboard charts、rollback button、review queue を追加します。Phase 3 で supplier draft、audit summary、defect summary へ対象を拡大します。Phase 4 で必要なら changedetection や ntfy などの外部 watcher を再検討してください。

【文字化け防止ルール】
これは必須です。ファイル名、ディレクトリ名、zip 内エントリ名、migration 名、script 名、env 名は ASCII only にしてください。日本語ファイル名、全角記号、emoji を使ってはいけません。人が読む文書系の .md、.txt、.csv は Windows での閲覧を考慮し UTF-8 with BOM を基本にしてください。コード・設定系の .py、.js、.ts、.tsx、.json、.yml、.yaml、.sql、.sh は UTF-8 without BOM にしてください。コードは LF 統一です。zip を作る場合、zip 名も内部パスも ASCII only にしてください。日本語本文は入れてよいですが、zip メンバー名は ASCII のみにしてください。Shift-JIS や UTF-16 に逃げてはいけません。CP932 と UTF-8 を混在させないでください。必要なら .gitattributes を追加し、text / eol / encoding 方針を固定してください。

【実装時の禁止事項】
新しい巨大 standalone platform を作らない。workflow engine を増やさない。vector DB を増やさない。general dashboard framework を増やさない。optimizer に production prompt を直接書き換えさせない。高リスク文面を自動送信しない。deprecated addon を理由なく Phase 1 にねじ込まない。既存コードを広範囲に壊す変更をしない。バックアップや rollback plan なしに compose や gateway 中核を壊さない。

【期待する最終成果物】
1. inventory memo
2. merge / hold / new decision table
3. architecture summary
4. rollback plan
5. DB migration
6. capture endpoint
7. n8n workflows
8. prompt registry
9. scoring / evaluation scripts
10. human feedback UI
11. Portal card
12. Quality Dashboard extension
13. Langfuse metadata integration
14. replay / shadow / promotion / rollback flow
15. setup README
16. all deliverables encoded per anti-mojibake rules

【開始指示】
まず inventory memo と decision table を出し、その後に最小変更で Phase 1 を実装してください。既存資産が 50%以上使えるなら必ず融合を優先し、不確実な場合は小さく可逆な変更から始めてください。Portal に UI を出すなら PDCA Lab カードを追加してください。すべての成果物で文字化け防止ルールを厳守してください。
