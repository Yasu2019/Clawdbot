# Quality Incident Report: CP-018 Book Pages Missing

Date: 2026-06-20

## Incident
The CP-018 robot publishing topic was added to `content_publishing_catalog.json`, but Kindle Unlimited, note, and BOOTH book pages were not created. The user correctly reported that the book pages could not be found.

## Impact
- The growth dashboard could show the publishing idea, but the user had no concrete book/page draft to open.
- The publishing workflow stopped at proposal level instead of becoming usable content.

## 5 Whys
1. Why were pages missing?  
   Because only the catalog item was added.
2. Why was only the catalog item added?  
   Because the task was interpreted as registering a publishing idea, not creating platform-specific pages.
3. Why was that interpretation insufficient?  
   Existing CP items use `cp-*_book_draft.html` and `.md` assets, so CP-018 should have followed the same pattern.
4. Why was the existing pattern not enforced?  
   There was no validation that every publishing catalog item with Kindle/note/BOOTH platforms has concrete page assets.
5. Why did this reach the user?  
   The final verification checked JSON validity and Telegram notification, but did not check that page assets existed for all listed sales channels.

## RCA
Root cause: asset completeness validation was missing for publishing catalog entries.

Contributing factors:
- The content catalog renderer accepts asset links but does not require them.
- Existing book draft naming convention was discovered after the user reported the gap.

## Web Knowledge Check
Global web knowledge collection was not needed for this root cause. The failure was local workflow completeness, not an unknown publishing-platform requirement.

## Countermeasures
- Added `cp-018_book_draft.html` and `cp-018_book_draft.md`.
- Added platform-specific drafts:
  - `publishing/cp018_robot_training/kindle_unlimited_page.md`
  - `publishing/cp018_robot_training/note_page.md`
  - `publishing/cp018_robot_training/booth_page.md`
  - `publishing/cp018_robot_training/README.md`
- Updated CP-018 `asset_paths` so the dashboard can link to these pages.
- Added validation that all non-external CP-018 assets exist.

## Recurrence Rule
When adding a publishing catalog item with `kindle`, `note_paid`, `note_free`, or `booth`, also create at least one concrete draft page and validate that every catalog asset path exists.

## Verification
- CP-018 asset existence validation: PASS.
- HTML structure validation for `cp-018_book_draft.html`: PASS.
- `localhost:8088` route check timed out, indicating a dashboard server availability issue separate from the missing page files.

