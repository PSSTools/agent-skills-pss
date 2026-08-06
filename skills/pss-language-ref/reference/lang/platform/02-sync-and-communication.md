# Synchronization and communication at target time

*Domain: platform. LRM §20.8 (blocking calls and concurrent execution), §21.9 (`sync_pkg`).*

Everything else in PSS coordinates actions at **solve** time. This page is about coordination
at **target** time — code that is already running, that needs to wait for something.

## When you are writing this

- One action must wait for an interrupt, a completion flag, or data from another action.
- Two actions run in `parallel` and must actually rendezvous at runtime.
- A polling loop in `exec body` is starving other execs on the same executor.
- The user said "wait until", "signal", "hand off".

## Decide

| The requirement | Use |
|---|---|
| "wait until data arrives from another action" | `channel_c<T>` — `get()` blocks |
| "hand data to another action at runtime" | `channel_c<T>.put()` |
| "check without blocking" | `try_get()` / `try_put()` |
| "poll a register until it changes" | a `while` loop with **`yield;`** in the body |
| "these must start together" | not this page — `parallel` in the activity |
| "b must run after a" | not this page — a flow object or a sequential block |

**Do not use this page to express scenario ordering.** Solve-time ordering (`parallel`,
`schedule`, flow objects) is stronger, checkable, and portable. Target-time synchronization is
for what genuinely cannot be decided before the test runs.

**Every polling loop needs a `yield`.** Executors are non-preemptible; a spin loop without one
stalls every other exec assigned to that executor, and the model will look correct while the
test hangs.

## Canonical form

```pss
import sync_pkg::*;

component dma_c {
    ref reg_c<bit>  done;
    channel_c<int>  irq;                    // DEPTH defaults to 1

    action DoDma {
        exec body {
            // ... set up the transfer ...
            irq.get();                      // blocks; other execs on this executor run on
        }
    }

    action DoPoll {
        exec body {
            while (comp.done.read_val() == 0) {
                yield;                      // let the blocked DoDma (and others) proceed
            }
        }
    }

    action DmaXferAndPoll {
        activity {
            parallel { do DoDma; do DoPoll; }
        }
    }
}
```

## Rules

### Blocking calls and concurrency (§20.8)

- A tool is expected to enable **concurrent execution of multiple exec blocks assigned to the
  same executor** via cooperative or preemptive multitasking (§21.7.2).
- **`yield;`** (§20.7.14) explicitly yields control to other concurrently executing exec blocks
  on the same executor. It is legal in target execs and target functions only, and is a no-op
  if nothing else is runnable.
- **When target exec code blocks on a channel operation (`get`, `put`), other concurrently
  executing exec blocks assigned to the same executor shall continue to be evaluated.**
- **The order in which blocking exec blocks are awakened and evaluated is non-deterministic.**

### Channels (§21.9.1)

```pss
component channel_c<type T, int DEPTH = 1> {
    target function T    get();
    target function void put(T t);
    target function bool try_get(output T t);
    target function bool try_put(T t);
}
```

- A channel is a **component**, and **all its functions are `target` functions** — callable only
  from `body`/`run_start`/`run_end` and functions reached from them.
- Holds up to `DEPTH` items in **FIFO** order; the first `get` returns the first `put`.
- **`DEPTH`, if specified, shall be positive.**
- **Channels may hold only**: numeric types, `bool`, **enums that have a base type**, packed
  structs, and arrays thereof.
- **Data is copied in and out by value.**
- Implementations must provide mutual exclusion and synchronization **across executors,
  independent of the languages implementing them**.

| Function | Behaviour |
|---|---|
| `get()` | **blocks** until an element is available; returns the oldest. Thread-safe: an element goes to exactly one of several simultaneous callers. **The order in which waiters are served is non-deterministic.** |
| `put(t)` | **blocks** until space is available, then inserts. Thread-safe; no data lost. **Insertion order among simultaneous callers is non-deterministic.** |
| `try_get(out t)` | returns `true` and the oldest element if any exists, else `false`. If N callers race and there are ≥ N elements, all N get `true` |
| `try_put(t)` | inserts and returns `true` if there is space, else `false`. No data lost or corrupted under contention |

## Gotchas

**A polling loop with no `yield`.**
```pss
exec body { while (comp.done.read_val() == 0) { } }        // WRONG: starves the executor
exec body { while (comp.done.read_val() == 0) { yield; } } // RIGHT
```
*Tier 4* — the model is provably correct and the test hangs. This is the single most damaging
mistake in target-side PSS.

**Calling a channel function from a solve exec.** All channel functions are `target`.
*Tier 2.*

**Putting a non-packable type in a channel.**
```pss
channel_c<string> c;              // WRONG
channel_c<my_packed_s> c;         // RIGHT
enum e_e { A, B }                 // no base type -> not allowed either
```
*Tier 2.*

**`DEPTH` of 0.** Must be positive.
*Tier 1–2.*

**Expecting `get()` to return to waiters in order.** Non-deterministic, both for wake-up order
and for which caller receives an element.
*Tier 4* — reproducible on one tool, different on another.

**Expecting channel data to alias.** Copied by value; mutating the sender's struct afterwards
changes nothing on the receiving side.
*Tier 4.*

**Using a channel to express scenario ordering.** The solver knows nothing about it, so it will
happily schedule the `get()` before anything can `put()` — a deadlock the model cannot see. Use
a flow object for ordering, and a channel only for genuinely runtime handoff.
*Tier 4* — the worst kind: a legal model that deadlocks.

**Blocking in `run_start`/`run_end`.** Legal, but these run once at bring-up/teardown, where
the thing you are waiting for may not exist yet.
*Tier 4.*

**Channel between actions on different executors, with no executor declared.** Fine — the
implementation must work across executors — but if you never declared executors you cannot
reason about which agent is stalled.
*Tier 4.*

## See also

- `01-executors.md` — what an executor is, and why sharing one matters here.
- `../activity/03-scheduling-semantics.md` — non-preemptible cooperative execution.
- `../procedural/03-procedural-statements.md` — the `yield` statement.
- `../structural/04-flow-objects.md` — the solve-time alternative, which you should prefer.
- `04-registers.md` — `read_val()` in a polling loop.
