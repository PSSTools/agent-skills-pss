# Resource objects: `lock` and `share`

*Domain: structural. LRM §9.4.*

A resource models something the environment has a **limited number of**, which actions occupy
for their duration. Unlike a flow object, nothing is exchanged: the point is exclusion.

## When you are writing this

- The user said "there are four DMA channels", "only one CPU core", "eight interrupt slots".
- The user said "these can't run at the same time" and the reason is contention, not data.
- The user described arbitration, priority, or "which engine does this run on".
- You want the tool to *choose* which instance an action uses, and to guarantee it doesn't
  double-book.

## Decide

| The requirement | Write |
|---|---|
| "this action needs exclusive use of one" | `lock resource_t r;` |
| "this action needs one, but others may use it too — just not exclusively" | `share resource_t r;` |
| "this action needs two distinct ones" | `lock resource_t r[2];` |
| "there are N of them" | pool size: `pool [N] resource_t p;` |
| "which one it got matters to the code" | read `r.instance_id` in `exec body` |
| "the thing carries data from one action to another" | not a resource — flow object |
| "which processing element runs this action" | not a resource — an *executor* claim, see `../platform/01-executors.md` |

**`lock` vs `share`:**

- `lock` — no other action may use that instance, in any mode, while this one runs.
- `share` — guarantees only that no other action has it *locked* while this one runs. Any
  number of sharers may overlap.

So `share` is the right claim for "I need a core, and I don't mind who else is on it, but
nobody may take it exclusively". If the action genuinely needs the resource to itself, `lock`.

## Canonical form

```pss
resource DMA_channel_s { rand bit[4] priority; }
resource CPU_core_s    { }

component dma_c {
    pool [4] DMA_channel_s chan_p;    // exactly four channels exist
    bind chan_p *;

    action xfer {
        lock DMA_channel_s ch;                       // exclusive, one channel
        constraint ch.priority > 2;                  // constrain the chosen instance
        exec body {
            poke(comp.ch_base(ch.instance_id), 1);   // which one did we get?
        }
    }

    action two_chan_xfer {
        lock  DMA_channel_s chans[2];                // two *distinct* channels
        share CPU_core_s    core;                    // non-exclusive
    }
}
```

## Rules

- Resources have a built-in non-negative integer `instance_id`, ranging `0 .. pool_size-1`
  (§9.4.1a). It is the resource's index in its pool.
- **There is exactly one resource object per `instance_id` per pool** (§9.4.1b). Two actions
  referencing the same type with the same `instance_id` are necessarily referencing the *same
  object* and agree on all its properties. This is what makes `instance_id` usable as an
  identity in `exec body`.
- Reference fields are declared in actions with `lock` or `share` (§9.4.2). Instance fields of
  resource type — as plain data — may only be declared under higher-level resource types.
- No two actions may be assigned the same resource instance if they **overlap in execution time
  and at least one is locking** it (§9.4.2). This is a strict scheduling dependency.
- Resource types may inherit from previously defined `struct`s or resources.
- Arrays of resource references:
  - the array is **entirely `lock` or entirely `share`** — not per element;
  - **all elements, across all dimensions, bind to the same pool**;
  - the pool must be **at least as large as the array**, since the claims are distinct.
- Resources live in pools and are claimed from them; the pool's size *is* the resource count
  (Clause 12). See `06-pools-and-binding.md`.

## Gotchas

**Pool smaller than the array claim.**
```pss
pool [2] DMA_channel_s chan_p;
action a { lock DMA_channel_s chans[4]; }   // WRONG: can never be satisfied
```
*Tier 3* — reported as an unsatisfiable scenario, not as a size error.

**Expecting `share` to mean "at most N sharers".** It does not count. `share` only excludes
concurrent `lock`. If you need bounded concurrency, size the pool and use `lock`.
*Tier 4.*

**Using `instance_id` as a value the user chose.** It is assigned by the solver. Constrain it
if you need a specific one (`constraint ch.instance_id == 0;`), but do not assume a mapping to
anything physical unless you established it.
*Tier 4.*

**Reading resource fields in a solve context and expecting the target to agree.** Fine — the
resource is solved. The reverse (writing them from `exec body`) is not.
*Tier 2.*

**Modeling a resource as a flow object.** A `buffer DMA_channel_s` produced by one action and
consumed by another gives you a data dependency chain, not mutual exclusion: transfers become
sequential in a way that has nothing to do with contention.
*Tier 4* — the model works, and every scenario it produces is wrong-shaped.

**Modeling exclusion with a sequential activity instead.** `{ do xfer; do xfer; }` serializes
two transfers whether or not they contend. A resource claim lets the tool run them in parallel
when the pool allows it.
*Tier 4.*

**Two actions claiming the same `instance_id` and disagreeing about its fields.** Impossible by
rule — but if you *wanted* them to be different objects, you have a modeling error, not a
constraint conflict. *Tier 3.*

## See also

- `06-pools-and-binding.md` — pool size is the resource count; binding decides who can claim.
- `04-flow-objects.md` — the other relationship kind, and how to tell them apart.
- `../platform/01-executors.md` — executors are the built-in "which engine runs this" mechanism
  and are usually a better answer than a hand-rolled resource.
- `../constraints/03-randomization.md` §resource objects — how instances get chosen.
- `../../playbooks/02-model-a-resource.md` — task-first.
