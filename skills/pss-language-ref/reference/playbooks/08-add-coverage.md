# Playbook: add coverage

*"Make sure we hit all the transfer sizes." "Cover a read after a write."*

## Choose the kind

| The question | Mechanism |
|---|---|
| "which **values** did we hit?" | `covergroup` — `../lang/coverage/01-data-coverage.md` |
| "which **scenarios** did we exercise?" | `cover` / `monitor` — `../lang/coverage/02-behavioral-coverage.md` |

## Steps — data coverage

**1. Decide where it lives.** In-line (`covergroup { … } cg;`) may reference the enclosing scope
and is the right default. A named type must be **parameterized** and must **not** reference its
declaring scope.

**2. Cover solved values.** Anything computed in `exec body` is invisible (§13.4.13). Sample
attributes the solver assigned.

**3. Write explicit bins.** This is the step that gets skipped, and it is what makes coverage
mean something.

```pss
covergroup xfer_cg(bit[16] len, mode_e m) {
    ln : coverpoint len {
        bins small[]  = [1..64];         // one bin per value
        bins medium   = [65..1023];      // one bin for the range
        bins large[4] = [1024..4096];    // four bins across the range
        illegal_bins  bad = [4097..];
    }
    md : coverpoint m;                   // enum: auto bins are fine
    md_x_ln : cross md, ln;
}
```

Auto bins on a wide integer give `min(2^M, auto_bin_max)` bins — **64 by default**. A `bit[32]`
coverpoint with no bins reports 100% and means nothing.

**4. Instantiate it.**

```pss
action xfer {
    rand bit[16] len;
    rand mode_e  mode;
    xfer_cg cg(.len(len), .m(mode)) with { option.at_least = 2; };
}
```

**5. Consider per-instance.** `option.per_instance = true` on a covergroup in a flow/resource
object collects **per pool**; in an action, per component instance.

## Steps — behavioral coverage

**1. Remember it only observes.** A `monitor` does not cause the scenario to be generated. If
you need it produced, that is a constraint or an activity.

**2. Pick the temporal operator.**

| Pattern | Statement |
|---|---|
| A then B, gaps allowed | `sequence { … }` (or bare `{ … }`) |
| A then B, immediately | `concat { … }` |
| B at some later point | `eventually …;` |
| all, any order, disjoint | `schedule { … }` |
| all, **simultaneously active at some instant** | `overlap { … }` |
| any one | `select { … }` |

**3. Constrain the handles, or the pattern is trivial.**

```pss
c1 : cover {
    write w;
    read  r;
    activity { concat { w; r; } }
    constraint w.addr == r.addr;
    covergroup { cpw : coverpoint w.write_mode; } cg;
}
```

## Checks before you call it done

- [ ] Explicit `bins` on every non-enum coverpoint.
- [ ] Sampled values are solve-resolved, not `exec body` results.
- [ ] A reusable covergroup type takes parameters and references nothing from its declaring
      scope.
- [ ] Crosses reference **coverpoints**, not expressions.
- [ ] `illegal_bins` used for "must never happen" *checks* — with a constraint if it must also
      never be *generated*.
- [ ] `ignore_bins` hasn't silently emptied a bin you cared about.
- [ ] `option.detect_overlap` on while developing.
- [ ] No option set twice in one scope.
- [ ] Monitors: is the pattern constrained enough to be meaningful?
- [ ] Cover statements are in components actually instantiated from the root.

## Common failures

| Symptom | Cause |
|---|---|
| 100% coverage that means nothing | auto bins on a wide integer |
| a coverpoint never samples | the value is produced on the target platform |
| a named bin is missing from the report | `ignore_bins`/`illegal_bins` removed all its values |
| a monitor never matches | the trace genuinely lacks it — a monitor cannot generate it |
| a monitor matches everything | unconstrained action handles, or `sequence` where `concat` was meant |
| coverage differs between tools | multiple first-match realizations; the choice is implementation-defined |

## See also

- `../lang/coverage/01-data-coverage.md`, `../lang/coverage/02-behavioral-coverage.md`.
- `../lang/constraints/01-algebraic-constraints.md` — producing what you want to count.
- `../../examples/coverage.pss`.
