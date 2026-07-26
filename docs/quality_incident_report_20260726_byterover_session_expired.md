# ByteRover query timeout caused by expired session (2026-07-26)

## Impact

The required pre-work context query did not return within 69 seconds. Unity
integration work was paused while the failure was isolated. No Unity, Blender,
download, RL-training, or application process was stopped.

## Observed facts

- The Unity/Mixamo context query timed out after 69 seconds.
- `brv status` reported `Account: Session expired`.
- The timed-out query left only its own CLI process and agent child running.
- Those two exact processes were stopped. The ByteRover daemon, Telegram bridge,
  unrelated Node processes, and RL training were preserved.

## Root cause analysis

### 5 Whys

1. The context query did not finish because the ByteRover agent returned no result.
2. The agent returned no result because its account session was expired.
3. This was detected after launch because the query path did not fail fast.
4. The shell waited 69 seconds because only the outer bounded timeout contained it.
5. Work can continue because the decisions and evidence already exist in Beads,
   incident logs, success cases, and the current handoff.

### Fishbone / FTA summary

- Authentication: expired ByteRover session (confirmed).
- Process lifecycle: query child remained after the outer timeout (confirmed).
- Network/provider: not tested; authentication already explains the failure.
- Project data: local context tree remains present; no corruption observed.

## FMEA

| Failure mode | S | O | D | RPN | Countermeasure |
|---|---:|---:|---:|---:|---|
| Expired session blocks engineering | 5 | 6 | 2 | 60 | Bounded query; use local durable records as fail-safe |
| Timed-out query leaves child | 4 | 5 | 3 | 60 | Stop only PIDs matching the exact query |
| Broad Node cleanup damages services | 9 | 2 | 7 | 126 | Verify PID and command line; never kill by image name |

## Countermeasure and decision rule

IF `brv status` reports an expired/invalid session and `brv query` times out,
THEN stop only the exact query child processes and continue from Beads plus local
durable Markdown, BECAUSE unrelated work must remain intact and ByteRover is not
the authoritative runtime dependency for Unity import.

The ByteRover skill's user recovery action is to run `brv login` again. Until
then, repeated queries are suppressed.

## Verification and rollback

- Pass: the exact query and agent child are absent; unrelated services and RL
  training remain running.
- Rollback: none required; no project content or daemon was deleted.
- Scope limit: ByteRover cloud/session recovery was not performed.

## Web knowledge decision

No web search was needed. Local authentication status directly identified the
failure; internet search cannot repair a private expired session.

## Provenance

- Date: 2026-07-26 JST
- Backup commit: `e765bdedaf`
- Project: `D:\Clawdbot_Docker_20260125`
