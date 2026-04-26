# 既存防止策との融合ガイド

## 原則
既存ファイルは削除・上書きしません。末尾に「AI Surgical Guardrails Complete v1」セクションとして追記します。

## 追記先
- CLAUDE.md がある場合: CLAUDE.md の末尾
- GEMINI.md がある場合: GEMINI.md の末尾
- AGENTS.md がある場合: AGENTS.md の末尾
- .cursorrules がある場合: .cursorrules の末尾
- OpenClaw SOUL.md: openclaw/OPENCLAW_SOUL_APPEND.md の内容を追記
- OpenClaw PROMISES.md: openclaw/OPENCLAW_PROMISES_APPEND.md の内容を追記

## 推奨導入順
1. GitHubバックアップが正常に動くか確認
2. AGENTS.md / GEMINI.md / CLAUDE.md を配置または追記
3. Rails保護ルールを確認
4. VSCode設定を確認
5. pre-commit hookを導入
6. Antigravityへ ANTIGRAVITY_RULES.md を読み込ませる

## 注意
.env, master.key, credentials は絶対にZIPやGitHubへ含めないでください。
