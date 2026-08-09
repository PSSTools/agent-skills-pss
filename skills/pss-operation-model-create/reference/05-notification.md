# Stage 8 — design a notification scheme per event

For every event surface from stage 2, the question is not *does an event exist* but **can it be
delivered to a thread blocked inside this model, and how**.

This is where operation models go wrong, and the failures are the least diagnosable in the whole
design: a blocking operation that never returns, in a model that elaborates, generates and lints
clean.

---

## The scheme

Nine fields. Fill in all of them, per event, in writing.

| # | Field | Why it decides something |
|---|---|---|
| 1 | **Event** — the device transition being signalled | "Chunk transferred" and "transfer complete" are different events even on one pin |
| 2 | **Physical origin** — pin, status bit, bus response | Fixes what the environment has to observe |
| 3 | **Delivery path** — how it reaches a blocked caller | The whole question. Environment calls in? Interrupt controller and ISR? Nothing? |
| 4 | **Model-side object** — what `wait_related_event()` blocks on | See below |
| 5 | **Routing** — which subjects a notification wakes | Getting this wrong destroys state |
| 6 | **Enablement precondition** — device config required before the event is ever raised | Creates a hard dependency from the blocking API onto a *configuration* operation |
| 7 | **Lost-wakeup analysis** | Decides channel-versus-flag |
| 8 | **Gap** — is field 3 established, or assumed? | An unestablished path is a stop-and-ask, never a fallback |
| 9 | **Failure signature** | So the eventual hang is diagnosable |

---

## Field 3 is the gate

**If you cannot establish the delivery path, stop and ask.** Do not fill in the rest of the scheme
around a guess.

What is missing is specific and askable:

- which agent or core observes the line;
- whether a controller sits between, and whether this device's line is routed to it;
- whether the environment has a monitor on that signal at all;
- whether the **enablement** (field 6) was found — an event that is never *raised* looks exactly
  like one that is never *delivered*.

Two substitutions you must never make on your own initiative:

- **A poll loop inside the model.** A spin consumes zero simulation time: it hangs the simulator
  rather than waiting in it. It is not a legal `wait_related_event()` at any level, and reaching for
  it converts an unanswered question into a defect that only appears at run time.
- **A timed backoff** — a clock wait, a yield, an RTOS delay. This is a legitimate scheme, but
  **only when the user asks for it**, because it silently changes the model's platform requirements.
  When chosen, it is a contracted (Tier B) dependency like any other: named, in the requirements
  list, with its cost stated.

Stopping is cheap. The **non-blocking API is unaffected** and completes in full; only the blocking
wrapper for that one operation waits on the answer.

If the user confirms there is genuinely no delivery mechanism on the target, the capability flag is
false and the device has no blocking API there. That is a correct, buildable outcome — but it is the
user's determination, not an inference you make from a blank field.

---

## The shape, when there is a path

### Field 4 — a depth-1 channel per subject

```
    wake : channel_c<bit,1>
```

- **A channel, not a flag.** There is no mutable component attribute to hold a flag, and
  flag-then-block has a lost-wakeup window: a notification arriving between arming and setting the
  bit is dropped and the waiter blocks forever. A channel has no such window — it *is* the
  registration. A notification that arrives before anyone waits leaves a token, and the next get
  returns immediately.
- **Depth 1 is the design, not a buffer size.** It makes the channel a coalescing binary semaphore:
  notifications arriving while a token is pending are absorbed by `try_put` failing, and a subject
  nobody is waiting on accumulates at most **one** stale token — worth one extra probe at the top of
  its next operation. That bound is what makes blind posting affordable.
- **Probe before blocking.** The loop reads the device before it ever waits, so a stale token costs
  one immediate return, not a missed completion.

### The notification entry point

`notify_<event>()` is the function the **environment** calls when it observes the device signal: a
monitor, a coroutine, an ISR. **Nothing in PSS calls it.**

- **Not an action.** The obvious alternative — a service action looping on an imported blocking
  wait — works, and it costs: the action never retires, so every scenario must compose it in
  parallel and must never wait on it. Keeping the notification outside PSS removes that from every
  test in the suite, and leaves the channel as pure runtime plumbing with no scenario semantics.
- **`try_put`, never `put`.** The caller runs on a thread outside any executor context. `put` blocks
  when the channel is full, stalling the monitor.
- **Know that it may be pruned.** No PSS code references it, so a front end that drops unreferenced
  functions will drop it, and it surfaces as an unresolved symbol at link time. Gating it adds a
  second way for it to vanish — say so at its definition.

### Field 5 — post blind

> **Never read the event in order to route the event.**

A dispatcher that reads an interrupt-source register to decide whom to wake **consumes the very
state the waiters need to decode**. Post blind to every subject and let each one probe its own
condition. `try_put` returning false is the normal case, not an error.

The asymmetry that justifies this: a missed wake is a hang; a spurious wake is one extra read.

### Field 6 — the enablement precondition

Most devices will not raise an event until software enables it — a mask register, a routing
register, an interrupt-enable bit. **This creates a hard dependency from the blocking API onto a
configuration operation**, and it is the single most common cause of "the blocking call never
returns".

Record which configuration operation programs it, and state in the source that the blocking level
depends on it having been called.

---

## The correspondence rule

The one thing this stage exists to check:

> For each subject `S`, the set of events that wake `S` must include **every** event that can change
> the answer of `check_<op>()` for any operation on `S`.

Miss one and the operation hangs after that event turns out to be the last thing that happens.
Include an extra and you pay one probe.

Write it as a table — subjects down, events across — and check it by hand. Nothing can automate it,
because no tool knows which physical events change a status register's value.

```
| Subject | Woken by | Can also be advanced by | Covered? |
|---|---|---|---|
```

If the third column has an entry the second does not, that is the bug, and you have found it at
design time instead of at 3am in a simulation that will not terminate.

---

## Failure modes

| Symptom | Cause | First thing to check |
|---|---|---|
| Blocking operation never returns | No notification: enablement (field 6) not programmed, or an event missing from the correspondence table | The routing/mask configuration, **before** the device |
| `check_<op>()` answers PENDING forever | Destructive completion already consumed — a second check after a terminal status, or an abort raced it | The guard message; whether an abort ran concurrently |
| Guard reports "check without start" | The one-operation-per-subject rule was broken | Whether the operation was started on *this* subject |
| Unresolved symbol at link | `notify_<event>` pruned, or built at the wrong level | The level first, then pruning |

→ Next: `06-structure.md`
