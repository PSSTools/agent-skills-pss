# Playbook: model a data flow

*"X produces something that Y consumes." "Configure before transfer."*

## Steps

**1. Pick the object kind.** This is a scheduling decision (§9.3):

| Producer/consumer relationship | Kind |
|---|---|
| consumer runs **after** producer completes | `buffer` |
| both run **at the same time** (one each) | `stream` |
| a mode or condition, one value at a time | `state` |

If you want one producer and several concurrent consumers, that is a `buffer`, not a `stream`.

**2. Declare the object type.** It is a struct with a kind:

```pss
buffer desc_s {
    rand bit[32] addr;
    rand bit[16] len;
    constraint len > 0;
}
```

**3. Give the actions `input` / `output` fields.**

```pss
action configure { output desc_s d; }
action transfer  { input  desc_s d; }
```

**4. Declare a pool and bind it.** Without this there is no scenario (Clause 12).

```pss
component dma_c {
    pool desc_s desc_p;
    bind desc_p *;
    action configure { output desc_s d; }
    action transfer  { input  desc_s d; }
}
```

**Pool placement is the reuse decision.** In `dma_c`, each DMA has its own; in a common ancestor,
they share. Decide deliberately.

**5. Write the activity — and write less than you think.**

```pss
action test { activity { do transfer; } }   // configure is INFERRED
```

The `input` pulls in a producer. If you want a specific one, traverse it and relate them:

```pss
action test {
    configure c; transfer t;
    activity { c; t; }
    constraint t.d.len == c.d.len;
}
```

**6. Constrain the object, not the actions.** Both the producer and every consumer contribute
constraints to the same object (§13.4.3), which is exactly what makes them agree without knowing
about each other.

## Checks before you call it done

- [ ] Is there a `pool` of this type, and a `bind`? *(the single most common omission)*
- [ ] Does the pool's placement give the sharing you intended?
- [ ] Is the kind right — does the consumer need the producer **finished**, or **running**?
- [ ] For `stream`: exactly one producer and exactly one consumer?
- [ ] For `state`: is `initial` constrained? Is `prev` guarded with `!initial`?
- [ ] Does the object type match the pool type **exactly**? (No base/derived substitution.)
- [ ] Did you add a sequential block that the flow object already implies?

## Common failures

| Symptom | Cause |
|---|---|
| "no legal scenario", nothing obviously wrong | missing `bind`, or no action outputs this type in that pool |
| the test serializes when you wanted overlap | `buffer` where the requirement was concurrent |
| the test has actions you didn't write | inference satisfying the unbound input — expected; use `atomic {}` to stop it |
| two actions get *different* objects when they should share | nothing relates them; constrain the inputs to refer to the same object |
| binding rejected | derived type bound to a base-type pool (§12.3g) |

## See also

- `../lang/structural/04-flow-objects.md` — the rules.
- `../lang/structural/06-pools-and-binding.md` — pools, binding, precedence.
- `../lang/activity/02-action-inferencing.md` — what gets added, and how to control it.
- `../../examples/flow_basic.pss` — a complete model.
