# Stage 7 — the two API levels

Every end-to-end operation becomes five functions. Four of them are unconditional; one is gated.

| Role | Signature | Present | What it does |
|---|---|---|---|
| `start_<op>` | `void start_<op>(args)` | always | Claim the guard, program, arm. Returns with the device running. **All device knowledge lives here** |
| `probe_<subject>` | `status_e probe_<subject>()` | always | One read of the completion condition, decoded. No guard, no loop. Internal |
| `check_<op>` | `status_e check_<op>()` | always | Guard + `probe`. **The public non-blocking API** |
| `wait_<subject>` | `status_e wait_<subject>()` | gated | The loop, then release the guard. Calls `wait_related_event()` |
| `<op>` | `status_e <op>(args)` | gated | `start_<op>(args); return wait_<subject>();` — nothing else |

`probe` and `wait` are named for the **subject** because several operations usually share one
completion condition. `probe` is separate from `check` for one reason: exactly one caller needs the
decode without the guard (the abort, below). If your device has no such caller, inline it.

## The rule that keeps the layers honest

> **The blocking wrapper adds only the loop.**

Mechanical test: if `<op>()`'s body contains **any** register access, address arithmetic, or
device-specific decision, the split is wrong and that content belongs in `start_<op>()`. A correct
`<op>()` is two lines.

This is not style. It is the entire basis for the claim that one regression covers both levels: a
simulation exercises the non-blocking core *because the core is the body of what the simulation
runs*. Every line that leaks into the wrapper is a line the polling consumer executes and the
regression does not.

Same rule for `wait_<subject>()`: it may contain the loop, the wake and the guard release, and no
device access except through `probe`.

## The two waits

```
wait_<subject>()          the loop + the guard release           (one per subject)
    while (probe() == PENDING) wait_related_event();

wait_related_event()      the one platform-dependent line        (stage 8)
```

Keeping them separate is deliberate: `wait_related_event()` is then the **only** thing an integrator
reimplements, and it is greppable. Everything else in the model is portable by construction.

`wait_related_event()` never reports completion. It returns "something may have changed"; every
decision comes from the probe. That is what makes the design edge-free — nothing is edge-triggered,
so nothing can be missed, and a spurious wake costs one extra read.

## Gating

One flag, one package, one constant:

```
package <dev>_cfg_pkg { static const bool <DEV>_HAS_BLOCKING = true; }
```

Selecting a level is a **build** decision, not a source decision: two mutually exclusive files
declare the same package and the build selects one.

| Element | Gated? |
|---|---|
| `wait_<subject>`, `<op>`, the end-to-end actions | **yes** |
| `notify_<event>` | **yes** |
| `start_<op>`, `probe`, `check_<op>`, all configuration operations | no |
| the `inflight` guard channel | **no** — `try_*` never blocks |
| the `wake` channel *member* | **no** — it is the `get()`, not the declaration, that needs a scheduler |

One flag per device is right when every event has the same delivery story, which is the usual case.
Split it only when two events differ *on the same target* — a routed completion interrupt plus a
handshake whose peer may not exist. One flag then forces an all-or-nothing choice, and the usual
damage is the unavailable event dragging the available one down with it.

**Assert the flag in the scenario layer, not in the device tree.** A device tree that asserts it
cannot be built at the non-blocking level at all; put the assertion where the mistake can actually
be made.

## What exists at each level

| | Non-blocking | Blocking |
|---|---|---|
| Configuration operations | all | all |
| `start_<op>`, `probe`, `check_<op>` | all | all (used by the layer above) |
| `wait_<subject>`, `<op>` | — | all |
| Scenario actions | **none** | all |
| `notify_<event>` | — | yes |
| Event routing required for progress | no | **yes** |

**The non-blocking level has a driver API, not a scenario layer** — no actions. An action's body
runs to completion before the action retires, so a scenario layer there would need either a spin
inside a body (never legal) or each operation split into an arm-action and a wait-action. Do not do
the latter: concurrency in a scenario is **parallel composition of whole operations**, not one
operation sliced in half. Slicing changes how every scenario is expressed to solve a problem that is
not a scenario problem.

That last table row is a real behavioural difference worth stating in the source: at the blocking
level, a test that routes no event raises no notification, so nothing wakes and the first end-to-end
operation blocks forever. That is intended — a hang is more honest than a green test whose
completion path was never real — but it makes "check the routing before you look at the device" the
first debugging step.

---

## Four shapes that do not fit

Each is a real device behaviour, not an edge case to smooth over.

### 1. An abort — an operation with no completion of its own

An abort (`stop`, `cancel`, `flush`) terminates a transaction that is *already running*, so the
subject already holds the guard token.

- **`start_<abort>()` claims nothing.** Claiming would report the one case the model explicitly
  permits as a violation.
- **`<abort>()` cannot call `wait_<subject>()`**, because that ends by *releasing* a token — it
  would take the aborted operation's. Give the abort its own loop over `probe`, without the release.
  This is the one caller that needs a guard-free probe. The duplication is five lines and it is the
  honest shape; a "do not release" flag would hide the one place two operations legitimately share a
  subject.
- **At the non-blocking level there is no `check_<abort>()`** — the abort holds no token, so it has
  nothing to poll with. A caller aborts, then keeps polling *the operation it aborted*.

Whichever of the two reads a destructive terminal status first consumes it, and which one that is
may not be determined by the model. Say so at the call site: the loser answers PENDING forever.

### 2. Completion supplied by another operation

Auto-restart, streaming, "runs until stopped": the completion event exists but nothing *this*
operation does causes it. Something else must clear the mode or abort the subject.

Blocking, this is a call that never returns, so it must never be the only thing a scenario waits on.
Non-blocking, it is a loop that never exits — the same defect with a *less* visible symptom.
Document it on `start_<op>()`, where both levels' readers will see it.

### 3. Blocking on something that is not an event surface

A hardware-handshake or pin-level model typically waits on an imported blocking foreign call, not on
a wake. There is no status register to probe, so there is no non-blocking half to hoist and the
decomposition does not apply.

Such a model has **no non-blocking form**, and it usually belongs to the peer's operation model
rather than this device's. Do not bring it under the same flag; if a build must exclude it, exclude
the component.

### 4. Intermediate progress events

A device that raises an event per chunk as well as per completion makes most wakes spurious. That is
free — the loop is wake-and-recheck.

But note the cost on the polling side: every probe that returns PENDING still **acknowledges**
whatever intermediate sources happen to be set, if those bits are destructive. Nothing is lost only
because the polling caller is the sole consumer of them — the one-caller-per-subject rule again, now
visible to firmware. State it in `check_<op>()`'s contract.

→ Next: `05-notification.md`
