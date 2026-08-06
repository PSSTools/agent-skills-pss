# Scheduling semantics

*Domain: activity. LRM Clause 6.*

The formal meaning of "sequential", "parallel", and "concurrent". Read this when an activity
or a set of flow objects isn't producing the ordering you expected, or when you need to reason
about whether two things can overlap.

## When you are writing this

- You need to know whether two actions *may* overlap, or *must*.
- The user asked for something to happen "at the same time" and you need to know what PSS can
  guarantee.
- You are choosing between a sequential block, a `parallel` block, and a flow object.
- You are reasoning about what the target environment must provide.

## Decide

The whole model reduces to one relation: **scheduling dependency**. `b` has a scheduling
dependency on `a` if `b`'s start must wait for `a`'s end.

| You need | The relation |
|---|---|
| b definitely after a | a scheduling dependency: sequential block, or a `buffer` from a to b |
| a and b definitely start together | **synchronized**: identical scheduling dependencies — `parallel`, or a `stream` between them |
| a and b may or may not overlap; order unspecified | **concurrent**: no dependency either way — `schedule` |
| a and b definitely overlap | **PSS cannot express this.** Concurrency permits overlap; it does not require it |

That last row is the one that catches people. `parallel` guarantees a common *start*, not
overlapping execution — PSS makes no assumptions about duration, so nothing forces two actions
to be alive at the same moment. If your intent depends on overlap, model it with a resource
claim, a `stream`, or target-side synchronization (`../platform/02-sync-and-communication.md`).

## Canonical form

```pss
activity {
    do a;                                  // \ sequential: b depends on a
    do b;                                  // /

    parallel { do c; do d; }               // c and d synchronized: same dependencies

    schedule { do e; do f; }               // concurrent: no dependency either way;
                                           // the tool may still order them if the
                                           // model rules require it
}
```

## Rules

### Preliminary definitions (§6.3.1)

- An **action execution** of an atomic action is the execution of its `exec body` with all
  reachable attributes assigned. A compound action's execution is the execution of the atomic
  actions it contains, directly or indirectly.
- **Start-time** is when the exec body is entered; **end-time** is when it exits; the difference
  is the **duration**.
- The **start-time is under the PSS implementation's control**. The **end-time is not** — it
  depends on the target implementation.
- A **scheduling dependency** means one execution necessarily starts after another ends. The
  implementation must guarantee this **regardless of actual durations**.
- Scheduling dependencies form a **partial order** over action executions. The solver
  determines it; the scheduler obeys it.
- **No dependency between two executions means neither waits for the other** — they *may* (or
  may not) overlap.
- Executions are **synchronized** if they have *exactly the same* scheduling dependencies. No
  delay is introduced beyond a minimal constant.
- Two sets are **independent** if there is no dependency between any two executions across the
  sets (there may be dependencies within each).
- Within a set, the **initial** executions are those with no dependency on another member; the
  **final** ones are those no other member depends on.

### Sequential (§6.3.2)

`a` and `b` are sequential if `b` depends on `a`. Two *sets* S₁, S₂ are sequential if **every
initial execution in S₂ depends on every final execution in S₁**. For N sets, this chains
pairwise.

### Parallel (§6.3.3)

S₁..Sₙ are parallel if **both**:

1. all initial executions in all sets are **synchronized** (identical dependency sets), and
2. the sets are **independent** of each other.

### Concurrent (§6.3.4)

S₁..Sₙ are concurrent if they are **independent** — condition 2 alone, without the
synchronized start.

### Assumptions about the execution environment (§6.2)

These are what a target platform must provide, and they bound what PSS can promise:

- **Starting and ending** (§6.2.1) — target-mapped behavior can be invoked at arbitrary points
  unless model rules prevent it, and completion can be known. **No assumption is made about
  duration**, or about the mechanism by which completion is detected.
- **Concurrency** (§6.2.2) — actions can be invoked concurrently, subject to model rules. PSS
  makes **no assumption about the threading framework**: native concurrent tasks (simulation),
  real threads (multicore), or cooperative time-sharing (an RTOS) are all equally valid.
- **Synchronized invocation** (§6.2.3) — invocations can logically start at the same time. Real
  "sync-time" overhead is at worst proportional to the *number* of synchronized actions and
  **constant with respect to everything else** in the scenario.

### Test realization (§6.4)

- Exec blocks are mapped to one or more **executors** (hardware threads) during execution.
- **Each executor is a single non-preemptible thread.** Executors implement **cooperative**
  multithreading among exec blocks running simultaneously on the same executor — which is why
  `yield` exists (§20.7.14) and why a blocking call in one exec body can stall others assigned
  to the same executor.

### Correctness of a run (§6.1)

Every observed action execution either corresponds to an explicit activity traversal or was
**implicitly introduced** to establish a correct flow. A legal run requires consistent
resolution of inputs, outputs and resource references; satisfaction of scheduling constraints;
and attribute assignments satisfying all constraints.

## Gotchas

**Reading `parallel` as "these overlap".** It guarantees a synchronized *start*. A one-cycle
action and a million-cycle action started in parallel do not meaningfully overlap.
*Tier 4.*

**Reading `schedule` as "these run at the same time".** It means "no ordering is imposed by
this statement" — the tool may still serialize them, and *will* if flow objects or resources
require it.
*Tier 4.*

**Assuming sequential composition of sets is per-branch.** Sequencing two *sets* means every
initial member of the second waits for every final member of the first — not a pairwise
zip of branches.
*Tier 4.*

**Assuming a common start survives an intervening dependency.** Synchronization requires
*identical* dependency sets. Give one `parallel` branch an extra input and its producer becomes
a dependency the other branch does not have — the branches are then no longer synchronized, and
the `parallel` may become unsatisfiable.
*Tier 3.*

**Assuming the target preempts.** Executors are **non-preemptible** and cooperative. A target
exec that blocks without yielding stalls every other exec on that executor, no matter what the
scheduling graph says.
*Tier 4* — a real hang, with the model provably correct.

**Reasoning about durations.** PSS makes no assumptions about them. Any intent expressed as "a
finishes before b starts" must be a scheduling dependency, never a timing assumption.
*Tier 4.*

## See also

- `01-activities.md` — the statements that create these relations.
- `../structural/04-flow-objects.md` — dependencies created by data rather than structure.
- `../constraints/02-scheduling-constraints.md` — stating dependencies as constraints.
- `../platform/01-executors.md` — what an executor is and how actions are assigned to them.
- `../platform/02-sync-and-communication.md` — `yield`, blocking calls, target-time
  synchronization.
