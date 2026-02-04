# MEMORY.md - Long Term Memory

This file contains curated, long-term context that persists across sessions.
It is distinct from `memory/YYYY-MM-DD.md` (which are raw daily logs).

## 🔑 Key Principles & Decisions

- **Safety First:** Always use `check_billing.py` and `gmail_to_calendar.js` for automation.
- **Transparency:** Logs must explain "Reasoning" for AI decisions (e.g. Calendar dates).
- **Compliance:** Never access restricted IATF docs without explicit permission.

## 👤 User Context (Suzuki-san)

- **Role:** Manager / Lead
- **Preferences:**
  - Prefers direct, concise reports.
  - Value "Peace of Mind" regarding API costs (Billing Guard installed).
  - Uses Google Calendar extensively.

## 🛠️ System State

- **ClawdBot:** Running in Docker (clawdbot-gateway).
- **Billing:** Monitoring enabled (Daily check, 500 JPY threshold).
- **Calendar:** Integration active (Gmail -> Calendar).
- **Drive:** rclone configured (gdrive).

## 📝 Ongoing Projects

- **Gmail Automation:** Stable.
- **Cost Monitoring:** Stable.
- **Obsidian Vault:** Sync enabled (readonly for bot).

_(Add new long-term learnings below this line)_
