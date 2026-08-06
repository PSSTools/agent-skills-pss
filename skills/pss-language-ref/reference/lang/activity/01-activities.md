# Activities

*Domain: activity. LRM Clause 11 (§11.1–11.5, 11.7, 11.8).*

An activity is the body of a compound action. It specifies **which actions participate and what
schedulings are legal** — a partial order, not a program.

## When you are writing this

- The user described a test as a sequence of steps.
- The user said "at the same time", "in any order", "one of these", "repeat until".
- You have several atomic actions and need to compose them.
- You need to refer to one traversal from another (a constraint, a join, a hierarchical path).

## Decide

See `README.md` for "how much should I say?" — start there. Once you know the shape:

| Statement | Meaning | Use for |
|---|---|---|
| `a1;` / `do A;` | traverse one action | the basic step |
| `{ s1; s2; }` or `sequence { }` | s2 after s1 completes | genuine sequencing |
| `parallel { }` | all branches **begin together** | streams; true simultaneity |
| `schedule { }` | all branches happen, **any legal order** | "these must all occur" |
| `atomic { }` | as above, but nothing outside may interleave | protecting an intended structure |
| `select { }` | exactly one branch | alternatives |
| `if (e) … else …` | branch on a solved value | conditional structure |
| `match (e) { }` | multi-way branch on a solved value | many alternatives on one expression |
| `repeat (n)` / `repeat (i : n)` | n iterations | counted repetition |
| `repeat … while (e)` | until a condition fails | data-dependent repetition |
| `foreach (e : coll [i])` | once per element | collection-driven repetition |
| `replicate (n) L[]:` | **in-place expansion**, addressable | n copies you need to name individually |
| `symbol s { }` | a named reusable fragment | repeated activity shapes |
| `L: <stmt>` | a named sub-activity | hierarchical references |

**`repeat` vs `replicate`** — `repeat` is a loop: one statement, executed n times, no handles.
`replicate` expands in place to n copies and, with a label array, gives each a name you can
reference (`L[0].a`). If you need to constrain the third iteration differently, you need
`replicate`.

## Canonical form

```pss
component dma_c {
    action A { rand bit[4] f1; }
    action B { }

    action test {
        rand bool  use_array;
        rand int in [2..4] n;
        A a1, a2;                       // named handles
        A a_arr[4];                     // an array of handles

        activity {
            a1;                          // traverse a declared handle
            do A with { f1 < 10; };      // anonymous traversal + inline constraint
            do A { .f1 = 3 };            // attribute initialization (3.1)

            L1: parallel {               // labelled: a named sub-activity
                b1: do B;
                b2: do B;
            } join_branch(b1)            // continue once b1 completes

            schedule { a2; a_arr; }      // any legal order; array traversed as a whole

            select {
                (n > 2) [3]: do A;       // guard + weight
                            [1]: do B;
            }

            replicate (i : n) R[]: { do A with { f1 == i; }; }

            repeat (k : 4) { do B; }
            foreach (e : some_list [j]) { do A with { f1 == e; }; }
        }

        constraint parallel { L1.b1, L1.b2 };     // hierarchical reference
    }
}
```

## Rules

### Activity declaration (§11.1, 11.2)

- An activity belongs to a **compound** action; an action with an activity shall not have an
  `exec body`.
- **If an action declares more than one activity, the semantics are as if they were combined in
  a `schedule` block** (§11).

### Traversal (§11.3.1)

- Two forms: **handle traversal** (`a1;`, where `a1` was declared) and **type traversal**
  (`[label:] do Type;`). With `do`, a label serves as the handle; without one the instance is
  anonymous.
- Either form may carry an **attribute initializer list** and/or **inline constraints**
  (`with { … }`).
- Traversal is the point at which the action is randomized and evaluated.

### Attribute initialization **3.1** (§11.3.1.2)

`do A { .f1 = expr };` passes data from the activity into the sub-action.

- **Evaluation order within an initializer list is unspecified.**
- Initialization statements **may not mutate action-level attributes**.
- Functions called in an initialization expression **must have no side effects**.
- The left-hand identifier must be an attribute of the traversed action type.
- Only fields of the traversed action **accessible in `pre_solve`** may be initialized.
- Only fields of the parent action **accessible in `post_solve`** may be referenced on the
  right.

### Action handle arrays **3.1 (multidimensional)** (§11.3.2)

- Arrays of action handles, possibly multidimensional, may be declared in an action.
- They may be traversed **element-wise** (`a_arr[0];` — same semantics as a single handle) or
  **as a whole** (`a_arr;`), including a sub-array of a multidimensional array.
- **When traversing an array as a whole, no attribute initializer list and no inline constraint
  may be given.**
- Traversed as a whole, each element is traversed **independently, per the semantics of the
  containing scope** — so `parallel { a_arr; }` starts all elements together.

### Sequential, `parallel`, `schedule` (§11.3.3–11.3.5)

- A sequential block: each statement is scheduled after the previous one completes.
- `parallel { }`: branches **begin execution at the same time**.
- `schedule { }`: all statements execute; the tool may pick **any order satisfying the other
  scheduling requirements**, including introducing dependencies needed for input/output binding
  and resource assignment.
- Without a join spec, the statement after a `parallel`/`schedule` block begins after **all**
  statements in the block complete.

### Fine-grained scheduling / join specs (§11.3.6)

Applied to a `parallel` or `schedule` block:

| Spec | Meaning |
|---|---|
| `join_branch(L1, L2, …)` | continue after the listed **top-level labelled branches** complete. If a label names an array traversal, after **all** its actions complete |
| `join_select(expr)` | continue after **N randomly selected** top-level branches. `0` ⇒ `join_none` |
| `join_none` | **no scheduling dependency** on the block |
| `join_first(expr)` | a **runtime** dependency on the first N to complete — no scheduling dependency |

- Join expressions must be **integer** and **determinable at solve time**.
- The application scope of a fine-grained block is **bounded by the containing sequential
  block**: everything started inside it must complete before the statement after that
  sequential block. Unjoined activities are **not** implicitly waited for by containing
  `parallel`/`schedule` blocks — only the containing sequential block joins them.

### `atomic` (§11.3.7)

`atomic { }` prevents other actions — including **inferred** ones — from interleaving into the
block's scheduling structure. Formally, all actions traversed in the block form one scheduling
cluster with a single incoming and single outgoing edge: any outside dependency on one member
becomes a dependency on all of them, in both directions. Inferred actions are **never** part of
an atomic set. Atomic sets nest but never partially overlap.

### Control flow (§11.4)

- `repeat ([index :] expr) stmt` — count form. `repeat stmt while (expr);` — while form.
- `foreach ([iter :] expr [[index]]) stmt`.
- `select { [ (guard) ] [ [weight] ] : stmt … }`:
  - guards are boolean; only branches whose guard is true **or absent** are *enabled*;
  - exactly one enabled branch is evaluated, and all scheduling requirements must hold for it;
  - weights are non-negative integers; probability = this weight / sum of enabled weights; a
    branch with no explicit weight when others have one gets weight **1**;
  - for an array of action handles, the weight applies to each element and one element is
    selected;
  - **it is illegal if no branch is valid** under constraints, scheduling, and guards.
- `if (expr) stmt [else stmt]`, `match (expr) { open_range_list : stmt … }`.

### `replicate` (§11.5.1)

- `replicate ([index :] expr) [Label[]:] stmt` — **generative**, expands in place; it adds **no
  scheduling or control-flow layer**. `N` copies under a `parallel` run in parallel.
- `expr` must be a positive integer and **known at solve time** — it may not depend on an
  attribute assigned in a runtime exec (`body`/`run_start`/`run_end`).
- With a label array, the expansions become `Label[0] … Label[N-1]`, individually referenceable.
- **Labels inside a `replicate` scope require the label array** — otherwise the expansions
  conflict.
- Traversing a handle **declared outside** the replicate scope does not produce multiple
  traversals. Anonymous traversals and handles declared *inside* the scope are fine.

### Symbols (§11.7)

`symbol name [(params)] { activity_stmts }` — a named activity fragment usable as a node. A
symbol may activate another symbol, but **symbols are not recursive**.

### Named sub-activities (§11.8)

- A **label** on an activity statement creates a named sub-activity and a new naming scope.
  **Unlabelled statements do not create a scope.**
- Labels must be unique within the containing named sub-activity, and **must not conflict with
  local variable or action-handle names**.
- Hierarchical paths (`L1.b1`) reference action handles and statements from constraints, from
  the same activity, and from the containing action's scope.

### Inheritance and extension (§11.6)

A derived action's activity **shadows** the base's; call the base with the `super;` statement.
Extension activities are additive.

## Gotchas

**`parallel` where `schedule` was meant.**
```pss
parallel { do a; do b; }    // forces simultaneous START
schedule { do a; do b; }    // "both happen, any legal order"
```
*Tier 4.* `parallel` is a strong requirement and often unsatisfiable once resources or flow
objects are involved — when it *is* satisfiable, it removes orderings the user wanted.

**Inline constraint or initializer on a whole-array traversal.**
```pss
a_arr with { f1 < 4; };    // WRONG
foreach (a_arr[i]) { a_arr[i] with { f1 < 4; }; }   // RIGHT
```
*Tier 2.*

**Label inside `replicate` without a label array.**
```pss
replicate (4) { L: do A; }      // WRONG: four conflicting L's
replicate (4) R[]: { L: do A; } // RIGHT: R[0].L … R[3].L
```
*Tier 1–2.*

**Traversing an outer handle inside `replicate` and expecting N instances.** You get one.
Declare the handle inside the scope, or traverse anonymously.
*Tier 4.*

**Label conflict with an action handle.**
```pss
L: schedule { A a; B b; a: { do C; } }   // WRONG: `a` is both a handle and a label
```
*Tier 1–2.*

**Expecting an unlabelled block to be a naming scope.** It isn't — two `L2:` labels under
different unlabelled `if` branches collide.
*Tier 1–2.*

**`join_none` and then assuming completion.** `join_none` removes the scheduling dependency
entirely; the following statement may run before anything in the block finishes. Only the
containing *sequential* block joins unjoined activities.
*Tier 4.*

**`join_first` treated as a scheduling constraint.** It is a **runtime** dependency only — the
solver does not order anything on it.
*Tier 4.*

**A `replicate` count that depends on runtime data.**
```pss
replicate (comp.count_from_body) { do A; }   // WRONG: must be solve-time known
```
*Tier 2–3.*

**`select` with no satisfiable branch.** Illegal (§11.4.4f) — but the diagnostic is a solve
failure, not a pointer at the `select`. Guards that are all false at solve time are the usual
cause.
*Tier 3.*

**Assuming `do A;` fully specifies the scenario.** If `A` has an unbound `input`, the tool will
**infer** a producer and insert it. Wrap in `atomic { }` if that is unwanted — and read
`02-action-inferencing.md` before assuming your activity is complete.
*Tier 4.*

**Two activities in one action treated as sequential.** They combine as a `schedule` block, not
a sequence.
*Tier 4.*

**Forgetting `super;` in a derived activity.** The base activity is *shadowed*, so its
traversals silently stop happening.
*Tier 4.*

## See also

- `02-action-inferencing.md` — what the tool adds to your activity without being asked.
- `03-scheduling-semantics.md` — the formal meaning of sequential/parallel/concurrent.
- `../structural/04-flow-objects.md` — the scheduling rules that come from data, not structure.
- `../constraints/02-scheduling-constraints.md` — ordering as a constraint, and `constraint
  parallel { … }` over hierarchical labels.
- `../structural/03-actions.md` — compound vs atomic.
- `../../playbooks/04-write-an-activity.md` — task-first.
