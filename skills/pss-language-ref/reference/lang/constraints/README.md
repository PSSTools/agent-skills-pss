# Domain: constraints — what values are legal

Supporting domain. You are here because you are restricting the values the solver may choose,
or debugging why it chose what it did.

Two characteristic failures, in opposite directions:

- **Over-constrained** — no solution exists. Tier 3: a generation-capable tool tells you, but
  usually not *which* constraint is at fault.
- **Vacuous** — the constraint is always true, or applies to nothing, so it silently permits
  everything. Tier 4: nothing tells you. Implication constraints with a condition that is never
  satisfiable are the usual cause.

---

## Decide: which form?

| You want to say… | Write |
|---|---|
| "always true of this type" | `constraint { ... }` in the type body |
| "true of this one traversal" | `do a with { ... };` inline constraint |
| "if P then Q" | `P -> Q;` (implication) |
| "P holds under exactly these circumstances" | `if (P) { Q } else { R }` |
| "prefer this, but yield if impossible" | `soft` **3.1** — see `01-algebraic-constraints.md` |
| "this rule applies only where I ask for it" | **generic constraint** `constraint c() { ... }` **3.1** — replaces `dynamic constraint` |
| "the same rule, over different expressions" | **generic constraint with parameters** **3.1** |
| "pick from these values with these weights" | `dist` |
| "one of this set" | `x in [a, b, c..d];` |
| "all different" | `unique { a, b, c };` |
| "true for every element" | `forall (x : T) { ... }` or `foreach` over a collection |
| "this is the value unless something else says otherwise" | default value constraint |
| "A must complete before B" | scheduling constraint — `02-scheduling-constraints.md` |
| "this state may only follow that state" | sequencing constraint on a `state` object |
| "randomize these, here, now" | `randomize` statement — `../procedural/03-procedural-statements.md` |

### Constraint vs activity structure

Ordering can be expressed twice: as activity structure (`{ a; b; }`) or as a scheduling
constraint (`constraint { a before b; }`). Prefer whichever states the *reason*:

- The order is inherent to what the actions are → flow object (`../structural/04-flow-objects.md`).
- The order is a rule about this scenario → scheduling constraint.
- The order is just the shape of this test → sequential block in the activity.

### Hard vs soft

A hard constraint that cannot be satisfied fails the whole solve. A `soft` constraint is
dropped, lowest-priority-first, until a solution exists. Use `soft` for defaults and
preferences; use hard constraints only for things that are actually illegal.

Corollary: **a `soft` constraint is not a guarantee.** Never write a `soft` constraint and then
write code that assumes it held.

### Fixed vs generic **3.1**

An orthogonal axis, and the LRM's own vocabulary since 3.1 (§13.1.1). A **fixed** constraint —
what you write as `constraint { … }` or `constraint name { … }` — always holds. A **generic**
constraint, declared with a parameter list (`constraint name() { … }`), holds *only where it is
referenced*: from inside another constraint, or by traversing it in an activity. Generic
constraints replace deprecated `dynamic` constraints and additionally may take parameters or
yield a value.

Hard/soft is about *priority*; fixed/generic is about *whether the constraint is in effect at
all*. They compose.

---

## Pages

| Page | Covers |
|---|---|
| `01-algebraic-constraints.md` | member constraints, generic constraints (**3.1**), inheritance, inline constraints, implication, `if`/`else`, `foreach`, `forall`, `unique`, default value constraints, `soft` (**3.1**), `dist` (§13.1) |
| `02-scheduling-constraints.md` | scheduling constraints between action handles; sequencing constraints on state objects (§13.2, §13.3) |
| `03-randomization.md` | the solve process: random attribute fields, randomization of lists / flow objects / resource objects / component assignment, solve ordering, relationship lookahead, procedural `randomize`, random stability (§13.4) |

## See also

- `../activity/03-scheduling-semantics.md` — what "before" actually means.
- `../data/04-expressions-operators.md` — constraint expressions follow the same typing rules.
- `../../playbooks/05-constrain-and-randomize.md` — task-first.
- `../../playbooks/10-diagnose.md` — "the solver says no solution".
