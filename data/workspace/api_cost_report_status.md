# API Cost Report

- Generated: 2026-06-03T20:27:06+09:00
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
| OpenAI | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | 4200 / 5000 Tokens/Min resets 1 minute (ok) |
| Anthropic / Claude | False | unknown | not set | unknown | unknown | not set | unknown | not_configured | 188000 / 200000 Tokens/Day resets 6 hours (ok) |
| Google Gemini | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | 5 / 50 RPM resets 15 minutes (warning) |
| Kimi / Moonshot | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | unknown |
| OpenRouter | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | unknown |
| OpenCode GO | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | 5 / 100 Requests/Day resets 2 days (critical) |
| ByteRover | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | unknown |
| Pexels | True | free | not set | 0.0000 | 0.0000 | not set | unknown | free_no_monetary_cost | unknown |
| Pixabay | True | free | not set | 0.0000 | 0.0000 | not set | unknown | free_no_monetary_cost | unknown |
| Unsplash | True | free | not set | 0.0000 | 0.0000 | not set | unknown | free_no_monetary_cost | unknown |
| Telegram Bot | True | free | not set | 0.0000 | 0.0000 | not set | unknown | free_no_monetary_cost | unknown |
| Turso | True | unknown | not set | unknown | unknown | not set | unknown | billing_amount_unknown | unknown |

## Local Evidence

- `D:\Clawdbot_Docker_20260125\data\workspace\iatf_opencodego_video_pdca_policy_status.json`: JPY=0.0, USD=0
- `D:\Clawdbot_Docker_20260125\data\workspace\api_quota_status.json`: JPY=0, USD=0
