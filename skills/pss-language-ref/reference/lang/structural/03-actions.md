# Actions

*Domain: structural. LRM §9.2.*

Actions are the unit of behavior — the thing the tool schedules. Everything a PSS model
*does* is an action.

## When you are writing this

- The user described an operation: "program the descriptor", "start a transfer", "reset the
  block", "wait for the interrupt".
- The user described a test made of several operations — that is a *compound* action.
- You need somewhere to attach an `exec body`.
- You need somewhere to declare what a step consumes and produces.

## Decide

| The behavior… | Write |
|---|---|
| is a single step you will implement | **atomic action** — has `exec body`, no `activity` |
| is composed of other steps | **compound action** — has `activity`, no `exec body` |
| is a family of related steps sharing fields/constraints | `abstract action` base + derived actions |
| is "the same operation, implemented differently per component subtype" | `override action` in each subtype |
| is a step whose ordering matters relative to another | give it flow-object `input`/`output` — don't hard-code order |
| needs something exclusive while it runs | give it a `lock`/`share` resource claim |

**Atomic and compound are mutually exclusive.** An action shall not have both an `activity`
and an `exec body` (§9.2.1a). If you find yourself wanting both, you want a compound action
that traverses a new atomic one.

**Abstract vs override** — both express "several variants of one idea", differently:

| | `abstract action` | `override action` |
|---|---|---|
| Chosen by | whoever writes `do derived_t;` | the component the action is associated with |
| Declared | may be outside a component (e.g. in a package) | only in a component that derives from one declaring the same name |
| Traversable directly | no | yes (the base is; the tool substitutes) |

## Canonical form

```pss
component dma_c {

    // atomic: implemented, not decomposed
    action xfer {
        input  desc_s  desc;          // what it needs
        output result_s res;          // what it produces
        lock   channel_s ch;          // what it occupies while running

        rand bit[16] size;            // solvable attributes
        bit[32]      addr;            // derived, not solved

        constraint size in [4..4096];
        constraint size % 4 == 0;

        exec post_solve { addr = alloc(size); }
        exec body       { poke(addr, size); }
    }

    // compound: composes, does not implement
    action test {
        xfer x1, x2;                  // action handles — declared, then traversed
        activity {
            do configure;
            schedule { x1; x2; }
        }
    }
}
```

Two ways to traverse: `do <type>;` creates an anonymous instance; declaring a handle
(`xfer x1;`) and writing `x1;` lets you refer to it — in constraints, in `join_branch`, from a
sibling. Declare a handle whenever anything else needs to name it.

## Rules

- An action shall have **either** `activity` items **or** `body` exec items, never both
  (§9.2.1a).
- Non-abstract actions may only be declared **in a component scope**. Abstract actions may be
  declared outside one, e.g. in a package (§9.2.3.3).
- `abstract` actions shall not be instantiated directly. An abstract action may derive from
  another abstract action, but **not from a non-abstract action** (§9.2.1c). Extending an
  abstract action leaves it abstract (§9.2.1d).
- An action may be declared `override` in a component **only if a same-named action exists in a
  base component**. If a component declares an `override` action, every subtype declaring that
  name must also declare it `override` (§9.2.2a,b).
- Template actions shall not be overridden (§9.2.2c).
- An overriding action implicitly inherits from the action it overrides — so constraints on
  base fields apply and may be tightened at the traversal site.
- A compound action may only instantiate actions defined in its own component or that
  component's instance sub-tree (§9.1.5.1).
- Action body items: `activity`, constraints, field declarations, `symbol`, covergroups, exec
  blocks, scheduling constraints, `compile if`, annotations, `override`.
- Actions have no `rand` on their object references — you constrain the *object's* fields, and
  the tool chooses the binding.

## Gotchas

**Both `activity` and `exec body`.**
```pss
action bad { activity { do sub; } exec body { poke(0,0); } }   // WRONG
```
*Tier 2.* Split it: keep the activity, move the body into a new atomic action traversed from it.

**Ordering hard-coded when it should be data.**
```pss
// WRONG-ish: correct today, unreusable tomorrow
action test { activity { do configure; do xfer; } }
// RIGHT: the reason for the order is stated
action configure { output cfg_s c; }
action xfer      { input  cfg_s c; }
```
*Tier 4.* Legal either way; the first silently prevents the tool from interleaving anything
else, and breaks when someone reuses `xfer` elsewhere.

**Declaring an action outside a component.**
```pss
package p { action a { } }             // WRONG unless `abstract`
package p { abstract action a { } }    // RIGHT
```
*Tier 1–2.*

**Expecting `do abstract_t;` to work.** Abstract actions are base types only.
*Tier 2.*

**Traversing a base action and assuming which subtype ran.** `do TrafficGen::SendTraffic;`
resolves to `PCIe::SendTraffic` or `USB::SendTraffic` depending on the component the solver
picks. If you need a specific one, name it: `do PCIe::SendTraffic;`.
*Tier 4* — the model is legal and the test is not the one you meant. Constrain `comp` if you
need to pin it down.

**Computing an attribute in `exec body` and constraining it.** Values produced on the target
platform are invisible to the solve (§13.4.13). Anything a constraint or coverage sample reads
must be produced by `pre_solve`/`post_solve` or by the solver itself.
*Tier 2–4* depending on tool depth.

**Assuming an anonymous `do` can be referenced.** `do xfer;` twice creates two unrelated
instances you cannot name. Declare handles if you need to relate them.
*Tier 1* if you try to name it.

## See also

- `../activity/01-activities.md` — how compound actions actually compose.
- `04-flow-objects.md`, `05-resource-objects.md` — the object references above.
- `02-components.md` — where actions live, and the `comp` handle.
- `07-inheritance-extension-overrides.md` — `abstract`, `override`, `extend` in full.
- `../procedural/01-exec-blocks.md` — `exec body` and its siblings.
- `../../playbooks/03-write-an-action.md` — task-first.
