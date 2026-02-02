# Protocol: Customer Response Data Context & Structure

This document defines the context, structure, and processing requirements for the "Customer Response Progress" data mounted into the Clawdbot environment.

## 1. Nature of Data

The folders listed below contain **"Progress and Records of Responses to Customer Requests"**.
They serve as the primary source of truth for tracking ongoing inquiries, deadlines, and historical responses.

## 2. Target Folders (Archives: Oct 2025 - Jan 2026)

Clawdbot must treat the following folders as "Progress Archives" and scan them chronologically.

**Base Path (Internal):**
`/home/node/clawd/Obsidian Vault/Becky/管理/管理パート生成済フォルダ`

**Monthly Archives:**

1. **October 2025**: `20260129_1213_管理_P-Custom__2025-10_2025-10-01_2025-10-31`
2. **November 2025**: `20260129_1220_管理_P-Custom__2025-11_2025-11-01_2025-11-30`
3. **December 2025**: `20260129_1233_管理_P-Custom__2025-12_2025-12-01_2025-12-31`
4. **January 2026**: `20260129_1249_管理_P-Custom__2026-01_2026-01-01_2026-01-24`

## 3. Processing Requirements for Clawdbot

### A. Name Aggregation (名寄せ)

- **Goal**: Identify unique customers across multiple files and months.
- **Method**: Extract customer names (e.g., "日本メクトロン", "ミヤタ") from the Markdown files within these folders.
- **Output**: A unified list of active customers with links to their respective inquiry files.

### B. Task Extraction (タスク抽出)

- **Goal**: Identify actionable items that are still open or require follow-up.
- **Method**: Scan for keywords and sections indicating status, such as:
  - 「回答待ち」 (Waiting for answer)
  - 「期限」 (Deadline)
  - 「未完了」 (Incomplete)
- **Action**: Sync these items to Clawdbot's internal TODOLIST or Task Management system.

### C. History Management (履歴管理)

- **Goal**: Ensure consistency in responses and avoid duplication.
- **Method**: Refer to past response content in these archives when drafting new replies.
- **Check**: Verify if a similar request was received previously and maintain consistency with prior answers.
