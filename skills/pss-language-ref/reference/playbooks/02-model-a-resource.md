# Playbook: model a limited resource

*"There are four DMA channels." "Only one core." "These can't run at once."*

## Steps

**1. Confirm it is a resource, not a flow object.** A resource is *occupied*; a flow object is
*exchanged*. If the consuming action doesn't care what is inside it, it's a resource.

**2. Declare the resource type.** Fields describe the instance, not the transfer:

```pss
resource DMA_channel_s { rand bit[4] priority; }
resource CPU_core_s    { }
```

**3. Declare the pool — its size is the count.**

```pss
component dma_c {
    pool [4] DMA_channel_s chan_p;    // four channels PER dma_c instance
    bind chan_p *;
}
```

**Where you put the pool decides what contends.** A pool in `dma_c` gives each DMA its own set;
a pool in a common ancestor makes them compete. Put the pool where the *thing* actually is.

**4. Claim it from the action.**

```pss
action xfer {
    lock  DMA_channel_s ch;     // exclusive for this action's duration
    share CPU_core_s    core;   // non-exclusive; only excludes concurrent lockers
}
action two_chan { lock DMA_channel_s chans[2]; }   // two DISTINCT channels
```

**5. Use it, if the realization needs to know which one.**

```pss
exec body { poke(comp.ch_base(ch.instance_id), 1); }
```

**6. Constrain the instance only if you must.** `constraint ch.instance_id == 0;` pins it;
`constraint ch.priority > 2;` selects by property. Both narrow the scenario space — do it only
when the requirement is real.

## `lock` vs `share`

- `lock` — no other action may use that instance in **any** mode while this one runs.
- `share` — guarantees only that nobody has it **locked** concurrently. Any number of sharers
  may overlap.

`share` does **not** bound the number of concurrent users. If you need "at most N at once", size
the pool and use `lock`.

## Checks before you call it done

- [ ] Is the pool size the real count of the thing?
- [ ] Is the pool at the level where contention actually happens?
- [ ] For an array claim: is the pool at least as large as the array?
- [ ] Is `lock` vs `share` right — does the action need it *to itself*?
- [ ] Is there a `bind`?
- [ ] Did you use a sequential activity block where the resource claim would have expressed it
      better?

## Common failures

| Symptom | Cause |
|---|---|
| nothing ever runs in parallel | pool of size 1, or `lock` where `share` was right |
| everything runs in parallel; no contention modelled | pool declared per-instance when the resource is shared system-wide |
| "no legal scenario" | array claim larger than the pool |
| unrelated transfers became ordered | the "resource" was modelled as a `buffer` |
| `instance_id` isn't the physical channel you expected | it is solver-assigned; constrain it if the mapping matters |

## Consider an executor instead

If the requirement is really "which **processing agent** runs this", executors are the built-in
mechanism and they carry the code-generation implications too. A resource derived from
`executor_claim_s` gives you *both* — executor assignment and scheduling exclusion. See
`../lang/platform/01-executors.md`.

## See also

- `../lang/structural/05-resource-objects.md` — the rules.
- `../lang/structural/06-pools-and-binding.md` — sizing and placement.
- `../lang/constraints/03-randomization.md` §13.4.4 — how instances get chosen.
- `../../examples/resource_arbitration.pss`.
