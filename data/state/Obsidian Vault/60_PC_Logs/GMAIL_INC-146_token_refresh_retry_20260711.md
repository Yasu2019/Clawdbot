---
tags: [gmail, oauth, incident, indexing, retry]
incident: INC-146
trouble_id: T057
bd_key: Clawdbot_Docker_20260125-w3cg
updated: 2026-07-11
---

# Gmail token refresh and bounded retry

## Summary

- NG: Gmail message fetches repeatedly returned 401 before the stored token expiry; one connection was also closed remotely.
- OK: 401 now causes one refresh and replay. Idempotent transient failures have a three-attempt ceiling.
- Impact: affected messages were skipped during the failed run; existing Gmail and indexed data were preserved.

## QC工程表

| Control point | Method | Acceptance | Result |
|---|---|---|---|
| Credential presence | Inspect key presence only | Access and refresh token present; values hidden | PASS |
| 401 recovery | Unit test two-response sequence | Refresh exactly once and second call succeeds | PASS |
| Retry ceiling | Two connection errors then success | Exactly three calls and two sleeps | PASS |
| Write safety | POST with 503 | No generic retry | PASS |
| Live health | Gmail `users/me/profile` GET | Read-only response succeeds | PASS |

## FMEA

| Failure mode | Effect | Cause | Countermeasure |
|---|---|---|---|
| Access token rejected early | Message indexing stops | Refresh tied only to stored expiry | Refresh and replay once on 401 |
| Remote connection closes | One message is skipped | No transport retry | Bounded retry for idempotent calls |
| Retry storm | API load and long hangs | Unlimited retry loop | Hard maximum of three attempts |
| Duplicate write | Unintended repeated mutation | Retry applied to all methods | Generic retries limited to GET/HEAD/OPTIONS |

## 5 Why / FTA

1. Fetch failed because Gmail rejected the access token.
2. The wrapper raised immediately on 401.
3. Refresh ran only when local expiry had elapsed.
4. Provider-side early invalidation was not modeled.
5. No regression case covered 401 refresh replay.

FTA top event: Gmail fetch failure = authentication failure OR transport failure. The fix puts a separate bounded recovery gate on each branch.

## Fishbone

- Method: expiry-only refresh rule.
- Machine/network: remote connection can close without a response.
- Software: request wrapper lacked bounded recovery state.
- Measurement: local expiry was treated as provider truth.
- Safety: retries were not classified by HTTP method idempotency.

## Countermeasures and forbidden patterns

- Refresh at most once per request after 401.
- Retry transient idempotent requests at most three attempts.
- Never print access tokens, refresh tokens, client secrets, or authorization headers.
- Never add unlimited retries.
- Never apply generic transport retries to non-idempotent methods without an idempotency design.

## Links

- `data/workspace/email_search_index.py`
- `data/workspace/tests/test_email_search_index_gmail_retry.py`
- `quality_incident_report_20260711_gmail_token_rejection.md`
- `docs/INCIDENT_LOG.md` - INC-146
- `data/workspace/memory/trouble_history.md` - T057
