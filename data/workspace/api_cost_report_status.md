# API Cost Report

- Generated: 2026-06-12T17:28:20+09:00
- USD/JPY used for optional USD conversion: 155.0
- Rule: unknown billing must stay unknown; this report does not invent yen cost.
- Known variable spend: 0.0000 JPY
- Known fixed monthly fees: 0.0000 JPY
- Total known monthly cost: 0.0000 JPY
- Unknown configured billing providers: 7
- History DB: `D:\Clawdbot_Docker_20260125\data\workspace\api_cost_report_history.jsonl`
- SQLite DB: `D:\Clawdbot_Docker_20260125\data\workspace\api_cost_report.sqlite`

| Provider | Configured | Billing mode | Fixed monthly JPY | Known variable JPY | Total known JPY | Limit JPY | JPY Remaining | Billing status | Usage quota remaining |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| OpenAI | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | None / 上限未設定 JPY resets API利用不可 (warning) |
| Anthropic / Claude | False | unknown | not set | unknown | unknown | not set | unknown | not_configured | unknown |
| Google Gemini | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | None / 上限未設定 JPY resets API利用不可 (warning) |
| Kimi / Moonshot | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | None / - - resets HTTP Error 401: Unauthorized (critical) |
| OpenRouter | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | None / No Limit USD resets API連動(正確) (ok) |
| OpenCode GO | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | None / 上限未設定 JPY resets API利用不可 (warning) |
| ByteRover | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | unknown |
| Pexels | True | free | not set | 0.0000 | 0.0000 | not set | unknown | free_no_monetary_cost | unknown |
| Pixabay | True | free | not set | 0.0000 | 0.0000 | not set | unknown | free_no_monetary_cost | unknown |
| Unsplash | True | free | not set | 0.0000 | 0.0000 | not set | unknown | free_no_monetary_cost | unknown |
| Telegram Bot | True | free | not set | 0.0000 | 0.0000 | not set | unknown | free_no_monetary_cost | unknown |
| Turso | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | unknown |

## Local Evidence

- `D:\Clawdbot_Docker_20260125\data\workspace\iatf_opencodego_video_pdca_policy_status.json`: JPY=0.0, USD=0
- `D:\Clawdbot_Docker_20260125\data\workspace\api_quota_status.json`: JPY=0, USD=0
