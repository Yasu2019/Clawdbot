# INC-MOLD-STOP-9995-20261103: a stop criterion was read as a physical result

Observed 2026-11-03 08:15 JST. Source: run summaries and solver code.

Failure: runs without the trapped-air model stopped at 99.95 % fill and reported the remaining 0.05 % as unfilled volume. That remainder has the same size as the defect being studied. 54 of 68 such runs ended this way. Reports based on those volumes were retracted, including one claim of mesh convergence: three levels agreed to 0.2 % because they all stopped at the same threshold.

Cause (verified in code): the threshold had been tightened only for runs with trapped air. The comment on that line named the size of the remainder.

Detection: adding a resisting effect appeared to reduce the unfilled volume. That contradiction was followed up instead of explained away.

Fix: a run with a hold stage ends only when full or when the hold ends. Regression test added and passing. Effect on the real model is pending reruns.

Still open: the same constant in another solver; showing the stop reason in result tables.

Lessons: report the stop reason with every end-state number. Agreement between levels proves nothing until you know the quantity is not set by the stopping rule.
