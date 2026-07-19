# Gmail Token Rejection RCA - INC-146

Date: 2026-07-11 JST
Beads: `Clawdbot_Docker_20260125-w3cg`

## Result

Gmail indexing failed on repeated HTTP 401 responses even though the locally stored access-token expiry was still in the future. The fixed path refreshes once and replays the request, while transient transport failures use bounded retries only for idempotent methods.

## Evidence

- `data/workspace/token.json` existed and contained access and refresh tokens; no values were displayed.
- Stored expiry: 2026-07-11 20:03 JST.
- Gmail rejected the token before 19:50 JST.
- Previous `gmail_request()` raised immediately on 401.
- A separate `RemoteDisconnected` had no retry path.

## 5 Why

1. Messages were not indexed because Gmail fetch calls failed.
2. Fetch calls failed because Gmail returned 401 and one connection was closed remotely.
3. The request wrapper raised immediately for both conditions.
4. Refresh was only checked against locally stored expiry during session creation.
5. Early provider invalidation and transient transport failure were missing from the test matrix.

## Fault tree

`Gmail fetch failure` = `authentication branch` OR `transport branch`.

- Authentication branch: provider rejects token AND no refresh replay exists.
- Transport branch: connection closes or service throttles AND no bounded retry exists.
- Repetition amplifier: per-message loop catches the exception and continues with the same rejected session.

## Countermeasures

- Refresh and replay once after 401; fail after a second 401.
- Retry connection errors, timeouts, 429, 500, 502, 503, and 504 at most three attempts.
- Apply generic retries only to GET, HEAD, and OPTIONS.
- Keep credentials and response bodies out of warning logs.
- Maintain focused regression tests for upper bounds and non-idempotent behavior.

## Web knowledge decision

No global web search was used. The failure mechanism was established directly from local source code, secret-safe token metadata, HTTP 401 behavior, and a successful read-only Gmail profile request after the fix. External search would not have changed the countermeasure.

## Verification

- `py_compile`: PASS.
- Focused unit tests: 4/4 PASS in 0.003 seconds.
- Live read-only Gmail profile request: PASS (`ok=True`).
