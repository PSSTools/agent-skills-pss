# The randomization process

*Domain: constraints. LRM §13.4.*

What actually gets randomized, when, and in what order. This page answers "why did the solver
pick that?" and "why is this field still zero?".

## When you are writing this

- A field isn't taking the values you expected, and the constraints look right.
- You need to compute something from solved values — where does that code go?
- You want randomness inside procedural code.
- You are debugging a solve failure that mentions exec blocks or ordering.
- You need to know whether the target platform can randomize.

## Decide

| You need… | Use | Where it runs |
|---|---|---|
| the solver to choose a field's value | `rand` on the declaration | solve |
| to set up non-random inputs to the solve | `exec pre_solve` | solve |
| to compute derived values from solved ones | `exec post_solve` | solve |
| randomness in procedural code | `randomize v1, v2 with { … };` | solve (structs) / target (scalars only) |
| a random scalar at test runtime | `urandom()` / `urandom_range()` | target |
| to force which component runs an action | a constraint on `comp` | solve |
| to force which resource instance is used | a constraint on `instance_id` | solve |

## Canonical form

```pss
struct S1 { rand bit[8] a, b; }
struct S2 {
    rand S1 f1;          // randomized: the field is `rand`
    S1      f2;          // NOT randomized: treated as an invariant
    constraint f1.a < f2.a;
}

action A {
    rand bit[4] x;
    bit[4]      y;                       // derived, not solved

    exec pre_solve  { y = 0; }           // set non-rand inputs to the solve
    exec post_solve {                    // compute from solved values
        y = x + 1;

        S2     v1;
        bit[4] v2;
        v1.f2.a = 100;                                  // an invariant
        randomize v1, v2 with { v1.f1.a < v2; };        // v1.f1.a ends up in [0..14]
    }
}
```

## Rules

### What is random (§13.4.1)

- A struct field qualified `rand` is randomized **only if the struct-typed field itself is also
  `rand`**. `S1 f2;` (no `rand`) means `f2.a` is *not* randomized, even though `a` is declared
  `rand`.
- Action `rand` fields are randomized **at the beginning of action execution** — for compound
  actions, **before the activity runs**, and in all cases before the action's exec blocks
  (except `pre_solve`).

### Lists (§13.4.2)

Randomizing a `rand` list randomizes its **elements**, consistent with constraints. **The size
is not randomized and may not be constrained** — set it in `pre_solve` (e.g. with `push_back`).
Hierarchical constraint references may name list elements whose existence is not yet known.

### Flow objects (§13.4.3)

- On randomization, `input`/`output` fields are assigned a **reference** to a flow object. On
  entry to any exec block (except `pre_solve`) and to the activity, all `rand` attributes
  reachable through them are resolved.
- The producing action and every consuming action contribute constraints to the **same** object;
  value selection satisfies all of them.
- Binding may be explicit (in an activity) or left to the tool, including by **inferring** a
  counterpart action (Clause 14).
- Where several actions input the same buffer type, input references may be constrained to
  refer to the same object.

### Resource objects (§13.4.4)

Claim fields are assigned a reference to a resource object; the same object may be referenced by
any number of actions provided no two **concurrent** actions lock it. Value selection satisfies
constraints from **all** actions it was assigned to, in either mode.

### Component assignment (§13.4.5)

- Randomization determines the action's component: `comp` is assigned a reference satisfying any
  constraints mentioning `comp`.
- **The component assignment corresponds to the pools** its inputs, outputs and resources reside
  in. If `a` outputs an object `b` inputs, both reference fields must be bound to **the same
  pool** under their respective components.

This is why a `comp` constraint can make a scenario unsatisfiable in a way that looks like a
pool problem, and vice versa.

### Procedural randomization (§13.4.6)

`randomize v1, v2 [with { … }];`

- The **entire set of target variables is solved together**.
- Targets are treated as random **whether or not they are declared `rand`**.
- Within a struct-typed target: `rand` sub-fields are random; **non-`rand` sub-fields are
  invariants** at their current values.
- Constraints declared inside the target types apply, plus the inline constraints.
- **Platform support** (§13.4.6.1): target execs support only **built-in functions (e.g.
  `urandom()`) and scalar integer randomization**. **Struct randomization is solve-only** and may
  not be reached directly or indirectly from a target exec.
- On the solve platform, solve-time exec blocks of the involved variables' types are **evaluated
  as part of the randomization**.
- **Random stability** (§13.4.2 / §13.4.6.2) is tool-defined; do not build reproducibility
  assumptions on top of it beyond what your tool documents.

### Value selection order (§13.4.7, §13.4.8)

- Values for sub-action fields are conceptually assigned **in the order encountered in the
  activity**.
- On entry to an activity, action handles are **uninitialized** and all attributes reachable
  through them are **unresolved**. A handle traversed again in a nested scope is **reset to
  uninitialized**.
- An action handle may be traversed **only once** in a given activity scope and its nested
  scopes.

### Relationship lookahead (§13.4.9–13.4.11)

When choosing a value, the tool accounts for **both** the explicit constraints on the field and
the **implied** constraints from fields traversed later in the activity — including those
introduced by **inferred actions, binding, and scheduling**. Lookahead also extends to
sub-actions and to dynamic constraints.

Practical consequence: an early traversal's value can be restricted by something much later in
the activity, with no local explanation.

### `pre_solve` / `post_solve` (§13.4.12)

- **`pre_solve`** sets non-random attributes the solver will read. It may read non-random fields
  and their non-random children. It **cannot access handle-type fields** (`input`/`output`,
  `lock`/`share`, action handles) or their children — those are null before randomization
  completes. Reading a plain-data `rand` field yields its **initial** value, and **anything
  written to a scalar `rand` field is overwritten by the solve**.
- **`post_solve`** runs after the solver has resolved `rand` fields, and sets non-random
  attributes from them.
- Evaluation order:
  1. **within a compound action, top-down** — the containing action's block runs before any
     sub-action is traversed;
  2. **between actions, per their scheduling** — if `a1` is scheduled before `a2`, `a1`'s
     blocks run first;
  3. **flow objects follow the flow** — an object's block runs after its producing action's and
     before its consumers';
  4. **resource objects run before every action referencing them**, in either mode;
  5. **within an aggregate, top-down** — container before contained.
- **Everything else is unspecified**: any order among sibling random struct attributes, and any
  order among actions scheduled in parallel that exchange no flow objects.

### Body blocks and external data (§13.4.13)

- `exec body` (and functions it calls) may assign attribute fields. The impact is evaluated
  **after the entire body block completes**.
- If the new values conflict with other values and constraints, **it shall be illegal**.
  **Backtracking is not performed.**

## Gotchas

**`rand` on a struct field that isn't itself reached by `rand`.**
```pss
struct S2 { S1 f2; }     // f2.a is NOT randomized, despite `rand bit[8] a` in S1
struct S2 { rand S1 f2; }// now it is
```
*Tier 4* — the field silently stays at its default.

**Constraining a `rand list`'s size.** Not permitted; set it in `pre_solve`.
*Tier 2.*

**Accessing an input/output or action handle in `pre_solve`.**
```pss
exec pre_solve { x = in_obj.size; }   // WRONG: handles are null here
```
*Tier 2–3.*

**Writing a `rand` scalar in `pre_solve` and expecting it to stick.** The solve overwrites it.
Use a constraint, or make the field non-`rand` and set it there.
*Tier 4.*

**Assigning a constrained field in `exec body`.** Evaluated after the body completes, with **no
backtracking** — a conflict is an error, not a re-solve.
*Tier 3.*

**Expecting a `body`-computed value to reach a constraint or coverage.** It can only be checked
against constraints, never feed them (§13.4.13).
*Tier 4.*

**Struct `randomize` in a target exec.** Solve-platform only. Target execs get scalar integers
and built-ins.
*Tier 2.*

**Relying on sibling ordering of solve execs.** Explicitly unspecified for sibling struct
attributes and for parallel actions with no flow between them.
*Tier 4* — reproducible on one tool, different on another.

**Traversing the same action handle twice in one scope.** Not allowed; and where it *is* legal
(a nested scope) the handle is **reset**, so values from the first traversal are gone.
*Tier 1–2 / Tier 4* respectively.

**Blaming the wrong constraint after lookahead.** A value restricted by a constraint far later
in the activity — possibly on an inferred action — is normal behaviour, not a bug.
*Tier 4.*

## See also

- `01-algebraic-constraints.md` — the constraints being solved.
- `../activity/02-action-inferencing.md` — where the extra constraints in lookahead come from.
- `../procedural/01-exec-blocks.md` — `pre_solve`/`post_solve`/`body` in full.
- `../procedural/03-procedural-statements.md` — the `randomize` statement's syntax.
- `../structural/06-pools-and-binding.md` — pools and the component assignment.
- `../platform/05-core-library-api.md` — `urandom()`, `urandom_range()`.
