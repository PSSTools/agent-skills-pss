# Pools and binding

*Domain: structural. LRM Clause 12, §11.9–11.11.*

A pool is where objects live. **Flow object exchange is always mediated by a pool**: one action
outputs into a pool, another inputs from that same pool. A resource claim always comes from a
pool. An object reference with no reachable pool can never be bound, so the action can never be
scheduled.

This is the most common cause of "the tool says there is no legal scenario" with nothing
obviously wrong in the model.

## When you are writing this

- You just gave an action an `input`, `output`, `lock`, or `share`. **Every one of those needs
  a pool.**
- The user said "each DMA has its own four channels" (pool per instance) or "the cores are
  shared across the system" (one pool higher up).
- You need state to be per-instance or global.
- Two actions that should exchange an object aren't connecting.

## Decide

| The requirement | Write |
|---|---|
| objects flow freely between all actions under a component | `pool T p;` in that component + `bind p *;` |
| each instance has its own set | declare the pool **in the instantiated component**, so each instance gets one |
| all instances share one set | declare the pool in a **common ancestor** and bind down the sub-tree |
| N resource instances | `pool [N] T p;` — the size **is** the count |
| a state variable | `pool state_t v;` — a state pool holds exactly one object at a time |
| this specific field of this specific action uses this specific pool | **explicit** bind: `bind p comp_path.action_t.field;` |
| everything of this type under here uses this pool | **default** bind: `bind p *;` |
| different elements of an object-reference array go to different pools | explicit bind per element (default binding cannot do this) |

**Pool placement is a scope decision, and it is the whole game.** A pool declared in `dma_c`
gives *each* `dma_c` instance its own; a pool declared in `pss_top` and bound downward is
shared by everything. Getting this wrong produces models that are legal and either
over-serialized (shared when it should be per-instance) or that never contend
(per-instance when it should be shared).

## Canonical form

```pss
component dma_c {
    pool     data_buff_s  buff_p;      // one per dma_c instance
    pool [4] channel_s    chan_p;      // four channels per dma_c instance
    pool     config_s     cfg_var;     // a state variable, per instance

    bind buff_p  *;                    // default: everything under dma_c
    bind chan_p  *;
    bind cfg_var *;

    action xfer {
        input  data_buff_s in_d;
        output data_buff_s out_d;
        lock   channel_s   ch;
    }
}

component pss_top {
    dma_c dma[2];
    pool [1] cpu_core_s core_p;        // ONE core, shared by both dma instances
    bind core_p *;
}
```

Explicit binding, when the wildcard is too broad:

```pss
component sys_c {
    dma_c    dma;
    pool data_buff_s in_p, out_p;
    bind in_p  dma.xfer.in_d;          // this field of this action
    bind out_p dma.xfer.out_d;
}
```

## Rules

- Syntax: `pool [ [expression] ] type_identifier identifier;` The size expression **applies
  only to resource pools**; it defaults to 1 (§12.1).
- Pool capacity by object kind (§12.1b):
  - **state** — exactly one object at any time;
  - **resource** — up to the declared size, unique objects, throughout the scenario;
  - **buffer / stream** — unrestricted.
- Binding is relative to the component sub-tree of the component in which the `bind` appears
  (§12.3).
- Two forms:
  - **explicit** — pool ↔ a specific object-reference field of a specific action type under a
    component instance;
  - **default** — pool ↔ a component sub-tree, by object type, using `*`.
- **Explicit binding always takes precedence over default binding** (§12.3c).
- Conflicting explicit bindings for the same field are **illegal** (§12.3d).
- If several default bindings apply, the one in the **top-most** component instance wins —
  default binding resolves top-down (§12.3e).
- Applying multiple default bindings to the same field *from the same component* is **illegal**
  (§12.3f).
- **The object type and the pool type must match exactly** (§12.3g). Binding a derived-type
  object to a base-type pool, or vice versa, is illegal. This is a hard rule and it surprises
  people who expect the usual substitutability.
- Wildcards may name a whole array without a range; in a multidimensional array you may range
  only some dimensions (§12.3b).
- Resource pools: `instance_id` runs `0 .. size-1`; the same `instance_id` **in the same pool**
  is the same object. Different pools with equal `instance_id` are different objects (§12.4).
- State pools: before any action outputs to the pool it contains the **initial** object
  (`initial == true`). The initial object is overwritten by the first output. Only actions
  scheduled before any writer can input it (§12.5).
- Explicit and hierarchical *object* binding inside activities (`bind a.out b.in;`) is a
  separate mechanism — see §11.9–11.11 and the Gotchas below.

## Gotchas

**Forgetting the `bind` entirely.**
```pss
component c { pool buf_s p; action a { input buf_s i; } }   // pool exists, nothing bound
```
*Tier 3* — "no legal scenario" / unbindable input, with no mention of the missing `bind`.
Declaring a pool does **not** bind it. Add `bind p *;`.

**Binding a derived type to a base-type pool.**
```pss
buffer base_b {}
buffer deriv_b : base_b {}
component c { pool base_b p; bind p *; action a { input deriv_b d; } }   // WRONG
```
*Tier 2–3.* Exact type match only. Declare a pool of the derived type.

**Pool in the wrong scope — the shared/per-instance mistake.**
```pss
component dma_c  { pool [1] cpu_core_s core_p; bind core_p *; }   // one core PER dma
component pss_top { dma_c dma[4]; }                               // ...so four cores exist
```
*Tier 4* — legal, and it silently removes all contention the user asked you to model. Put the
pool where the *thing* actually is.

**Sizing a resource pool by how many claims you make.** The pool size is how many exist, not
how many are used. `pool [4]` with an action locking `chans[4]` means one such action can be in
flight at a time — which may be exactly right, or may be why nothing overlaps.
*Tier 4.*

**Expecting default binding to spread an object-reference array across pools.** It applies
uniformly to all elements. Use explicit binds. (§9.3.4c)
*Tier 3.*

**Two default binds for the same type from one component.** Illegal (§12.3f) — and a natural
mistake when adding a second pool of the same type. Use explicit binds to disambiguate.
*Tier 2.*

**State input without a bind.** A `state` reference *must* be statically bound (§9.3.3e). It is
easy to add the pool and forget the directive.
*Tier 3.*

## See also

- `04-flow-objects.md` — what the pool holds, and the scheduling rules that come with each kind.
- `05-resource-objects.md` — `instance_id`, and why pool size is the resource count.
- `../activity/02-action-inferencing.md` — inference searches the *bound* pool; an unbound pool
  is invisible to it.
- `02-components.md` — pools are component members; scope is everything.
- `../../playbooks/01-model-a-flow.md`, `../../playbooks/02-model-a-resource.md`.
