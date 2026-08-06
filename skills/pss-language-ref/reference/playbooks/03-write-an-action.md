# Playbook: write an action

*"An operation that programs the descriptor and starts the transfer."*

## Steps

**1. Atomic or compound?** Atomic if you will implement it (`exec body`); compound if it is made
of other actions (`activity`). **Never both** (§9.2.1a).

**2. Put it in the right component.** Non-abstract actions live in a component scope, and that
component decides which pools it can reach and which sub-actions it may traverse.

**3. Declare what it needs and produces — before its attributes.**

```pss
action xfer {
    input  desc_s   d;      // what it consumes
    output result_s r;      // what it produces
    lock   chan_s   ch;     // what it occupies
}
```

This is where ordering and exclusion come from. Doing it first stops you from hard-coding order
in an activity later.

**4. Declare attributes, distinguishing solved from derived.**

```pss
    rand bit[16] size;      // the solver chooses
    bit[32]      addr;      // computed in post_solve
```

**5. Constrain — the rules, not the values you want.**

```pss
    constraint size in [4..4096];
    constraint size % 4 == 0;
    constraint soft size == 64;      // a preference, not a rule
```

**6. Realize it.**

```pss
    exec post_solve { addr = alloc_addr(size); }   // solve platform
    exec body       { poke(addr, size); }          // target platform
```

Check the platform of every function you call. See `../lang/procedural/01-exec-blocks.md`.

## Full shape

```pss
component dma_c {
    action xfer {
        input  desc_s d;
        output res_s  r;
        lock   chan_s ch;

        rand bit[16] size;
        bit[32]      addr;

        constraint size in [4..4096] && size % 4 == 0;
        constraint size <= d.len;

        exec post_solve { addr = alloc_addr(size); }
        exec body {
            poke(comp.ch_base(ch.instance_id), addr);
            message(LOW, "xfer %d bytes to 0x%x", size, addr);
        }
    }
}
```

## Checks before you call it done

- [ ] Atomic **or** compound, not both.
- [ ] Every `input`/`output`/`lock`/`share` has a bound pool.
- [ ] Fields the solver chooses are `rand`; fields computed from them are **not** `rand` and are
      set in `post_solve`.
- [ ] Nothing in `exec body` feeds a constraint or a coverage sample (§13.4.13).
- [ ] `comp` is read, never written.
- [ ] Every function called from `body` has a target definition; every one called from a solve
      exec has a solve definition.
- [ ] Ordering relative to other actions comes from flow objects, not from a caller's activity
      block.
- [ ] If it derives from another action, does its `exec body` need `super;`?

## Common failures

| Symptom | Cause |
|---|---|
| tool rejects a call in `exec body` | a `solve function`, directly or transitively |
| a field is always its default | declared `rand` inside a struct field that isn't itself `rand`, or written in `pre_solve` |
| a constraint "has no effect" | it references a field assigned in `exec body` |
| the base implementation stopped running | a derived `exec body` without `super;` |
| the action can never be scheduled | an object reference with no reachable pool |

## See also

- `../lang/structural/03-actions.md` — the rules.
- `../lang/procedural/01-exec-blocks.md` — exec kinds and platforms.
- `../lang/constraints/01-algebraic-constraints.md` — hard vs soft.
- `01-model-a-flow.md`, `02-model-a-resource.md` — step 3 in detail.
