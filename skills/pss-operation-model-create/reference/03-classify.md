# Stages 5–6 — classify, and state the completion contract

Stage 5 decides which operations need the rest of the procedure. Stage 6 decides whether they are
safe to poll.

---

## Stage 5 — three kinds of operation

| Kind | Definition | Splits into two API levels? |
|---|---|---|
| **Configuration** | Straight-line accesses. Complete when the last store retires. No device state machine is entered | **No.** Already platform-neutral; ships unchanged everywhere |
| **End-to-end** | Has a completion event the device raises asynchronously. The caller's view is submit → running → complete | **Yes.** Everything below is about these |
| **Environment entry point** | Called *into* the model by the environment, not by the system: an interrupt notification, an observation callback | **No — gated entirely.** Exists only where the blocking layer does |

Two tests settle the ambiguous cases:

1. **Does the device signal completion?** If the honest answer is "it's done when the writes are
   done", it is configuration. An operation whose completion condition is "nothing" is configuration
   by construction.
2. **Does the system initiate it?** If not, it is an environment entry point — and it does not
   belong in the device's API at all. It belongs at the seam.

Most models are mostly configuration. That is normal and it is good news: configuration operations
need no guard, no notification scheme, and no gating.

---

## Stage 6 — the completion contract

For each **end-to-end** operation, answer three questions in writing.

### 6a. What is the completion condition?

Which device-observable state changes, and how does it decode? Name the register and the bits.

Several operations often share one condition — everything acting on one channel completes off that
channel's status register. When they do, they share one decode function (`probe_<subject>`) and one
wait, both named for the **subject**, not the operation.

If two operations on the same subject need genuinely *different* decodes, that is a signal they act
on different subjects.

### 6b. Is the completion condition destructive?

**This is the question that decides whether the split is safe**, because the check runs an unbounded
number of times. It is usually an RTL fact and it is frequently under-documented.

| Condition | Consequence |
|---|---|
| **Non-destructive** — a level bit, a status word that survives being read | Easiest case. The check is idempotent, the guard is optional, a caller may poll as often and as late as it likes |
| **Read-to-clear** — reading the status consumes it | The common hardware case. Safe only if the value is captured by the same read that observes it, and only if **one caller at a time** polls the subject. **The guard below is mandatory** |
| **Consuming** — the check dequeues the result | The check *is* the completion. `check_<op>()` must return the payload, not just a status, and the operation cannot be polled speculatively at all |

**How to find out.** In order of reliability: the RTL's clear conditions for those bits; the register
spec's access-class column (a marker like `RC`, `ROC`, `RWC`, or a legend note that "a C indicates
bits are cleared after a read" — easy to skim past, and decisive); the spec prose. If you only have
a spec and it is silent, assume destructive.

A register can be mixed: one status bit read-to-clear and its neighbour a plain level bit. Record it
per bit, because it changes what a *second* read returns and therefore what a repeated check may
conclude.

### 6c. What does a caller have to promise?

Usually "one operation at a time on this subject", sometimes more. Write it down as the operation's
contract — it is the thing the guard detects violations of, and it is what a firmware author needs
that a simulation caller never had to think about.

---

## The in-progress guard

**Applies when the completion condition is read-to-clear or consuming.** Skip it otherwise.

Two mistakes become possible the moment `check_<op>()` is public, and neither is visible from the
device side — a stale read and a live one look identical:

1. Polling a subject on which nothing was started.
2. Polling *past* a completion that was already consumed. The second call does not re-report done;
   it reads a subject whose status has been taken, and answers **PENDING forever**.

The blocking layer was quietly protecting you from both: it contained the destructive read inside a
loop that exits holding the value. Publishing `check_<op>()` moves that hazard to a caller with no
such containment.

### Shape

There is no mutable component attribute in PSS, so there is nowhere to latch "already reported". A
depth-1 channel **is** the latch:

```
    inflight : channel_c<bit,1>       // present on every profile

start_<op>():   if (!inflight.try_put(1)) report("already in progress"); return;
                ... program, arm ...

check_<op>():   if (!inflight.try_get(tok)) report("check without start"); return PENDING;
                status = probe_<subject>();
                if (status == PENDING) inflight.try_put(tok);   // restore
                return status;                                  // else leave taken

wait_<subject>(): loop { status = probe(); if terminal break; wait_related_event(); }
                inflight.try_get(tok);                          // release once, at the end
```

- **`try_*` only.** Neither call ever blocks, which is what lets the guard exist where there is no
  scheduler at all.
- **Take-and-restore, not peek**, because a channel offers no peek. Safe under the
  one-operation-per-subject rule the model already requires.
- **Claim before the first register write**, so a rejected double-start has not corrupted the
  configuration of the operation already running.
- **The wait releases once at the end**, not per iteration: during a blocking wait, start and wait
  are inside one function, so there is no window for misuse.
- **It is a detector, not a lock.** The caller still owes you the rule; this catches the case where
  it has already been broken.

### Reporting a violation

A guard violation is a **programming** error, not a device error, and they must not be confusable.

- **Do not return ERROR** — that makes a caller bug indistinguishable from a device fault.
- **Return PENDING** after reporting. There is no honest answer available; the state needed was
  consumed by whoever broke the rule.
- **Report at the loudest level available**, with distinctive text a runtime can match, and bind the
  model's message sink to a fatal in environments that have one.

---

## The status type

Append `PENDING` to the operation's existing outcome enum rather than introducing a second one:

```
enum <dev>_status_e { <DEV>_DONE, <DEV>_ERROR, <DEV>_PENDING }
```

- **Append**, so existing numeric values are preserved — they cross into generated code.
- **One enum, not two**, so `check_<op>()` and `<op>()` share a return type with no conversion
  between the layers.
- **Document that the blocking forms never return PENDING.** They return only on a terminal state,
  so an existing caller still has exactly two outcomes to handle.

**Decode ERROR before DONE** when the terminal states are not mutually exclusive. An aborted
operation can retire with both set; reporting ERROR is the conservative reading, where the reverse
ordering hides it.

→ Next: `04-api-levels.md`
