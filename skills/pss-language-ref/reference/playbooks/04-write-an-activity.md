# Playbook: write an activity

*"A test that configures, then runs four transfers, two of them at once."*

## The governing rule

**An activity specifies a partial order, not a program.** Every ordering you write removes
scenarios. Write the least you can and still be correct.

## Steps

**1. Ask what the ordering constraint actually is.** For each pair of steps the user mentioned:

| The real reason | Express it as |
|---|---|
| "b needs what a produced" | a flow object — **not** an activity block |
| "they contend for the same thing" | a resource claim — **not** an activity block |
| "the test is defined to do it in this order" | a sequential block |
| "no order; they all must happen" | `schedule { }` |
| "they must start together" | `parallel { }` |

Most "then" in a requirement is the first row. Do that step before writing any activity syntax.

**2. Write the skeleton with the weakest form that works.**

```pss
activity {
    do configure;
    schedule { do xfer; do xfer; }
}
```

**3. Add repetition.**

```pss
repeat (4)         { do xfer; }              // four, no handles
repeat (i : 4)     { do xfer with { id == i; }; }
replicate (i : n) R[]: { do xfer; }          // n copies you can name: R[0], R[1], …
foreach (e : sizes [i]) { do xfer with { size == e; }; }
```

`repeat` when the copies are interchangeable; `replicate` when you need to refer to them.

**4. Add choice.**

```pss
select {
    (mode == FAST) [3]: do fast_xfer;        // guard + weight
                   [1]: do slow_xfer;
}
if (use_dma) { do dma_xfer; } else { do cpu_copy; }
```

**5. Name what you need to reference.**

```pss
activity {
    L: parallel {
        a: do xfer;
        b: do xfer;
    } join_branch(a)
}
constraint parallel { L.a, L.b };
```

Only **labelled** statements create a naming scope. Unlabelled blocks do not.

**6. Decide whether inference is welcome.** An unbound `input` anywhere in this activity will
pull in producers. If the activity's structure must be exactly what you wrote, wrap it in
`atomic { }`.

## Checks before you call it done

- [ ] Is every sequential block there for a stated reason, or is it hiding a missing flow object?
- [ ] `parallel` only where a **common start** is genuinely required?
- [ ] Do you know which extra actions inference will add? (`../lang/activity/02-action-inferencing.md`)
- [ ] Labels unique within their containing named sub-activity, and not colliding with action
      handle names?
- [ ] Labels inside `replicate` use a label array?
- [ ] No action handle traversed twice in the same scope?
- [ ] No whole-array traversal carrying an inline constraint or initializer?
- [ ] Any `join_none`/`join_first` — do you understand that the following statement does **not**
      wait?

## Common failures

| Symptom | Cause |
|---|---|
| the scenario is far more rigid than asked for | sequential blocks where flow objects belonged |
| "no legal scenario" from a `parallel` | one branch acquired an extra dependency, so the branches can't be synchronized |
| extra actions in the test | inference — expected; `atomic { }` if unwanted |
| label conflict | an unlabelled `if`/block isn't a scope; two `L2:` under different branches collide |
| `replicate` produced one traversal, not N | the handle was declared **outside** the replicate scope |
| statements ran before a `parallel` finished | `join_none` / `join_first` |
| two activities behaved unexpectedly | multiple activities in one action combine as `schedule`, not as a sequence |

## See also

- `../lang/activity/01-activities.md` — every statement, in full.
- `../lang/activity/03-scheduling-semantics.md` — what sequential/parallel/concurrent mean.
- `../lang/constraints/02-scheduling-constraints.md` — ordering across compound-action boundaries.
- `../../examples/activity_shapes.pss`.
