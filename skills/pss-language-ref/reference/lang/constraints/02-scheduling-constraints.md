# Scheduling and sequencing constraints

*Domain: constraints. LRM §13.2, §13.3.*

Two mechanisms that constrain *when* things happen rather than *what values* they take.

## When you are writing this

- Two actions are inside a `schedule` block and you need to relate a *pair* of them.
- You need to relate sub-actions of two different compound actions.
- You are modelling a state machine and need "this transition may only follow that one".
- The ordering you want cannot be expressed by nesting activity blocks.

## Decide

| The requirement | Write | Where |
|---|---|---|
| "a then b", structurally | a sequential activity block | `../activity/01-activities.md` |
| "a then b", but they are in a `schedule` and nesting would be wrong | `constraint sequence {a, b};` | this page |
| "a and b start together", across compound-action boundaries | `constraint parallel {a, b};` | this page |
| "b needs what a produced" | a flow object | `../structural/04-flow-objects.md` |
| "this state may only follow that state" | a constraint on `prev` in the state type | this page |
| "the pool starts in this state" | a constraint on `initial` in the state type | this page |

**Prefer activity structure and flow objects.** A scheduling constraint is the right tool
exactly when the actions being related are in *different* sub-activities and restructuring the
activity would misrepresent the intent — typically relating sub-actions of two independently
scheduled compound actions.

## Canonical form

```pss
action my_sub_flow {
    A a; B b; C c; D d;
    activity {
        sequence {
            a;
            schedule { b; c; d; };     // no relative order imposed here
        };
    };
}

action my_top_flow {
    my_sub_flow sf1, sf2;
    activity {
        schedule { sf1; sf2; };
    };
    // relate sub-actions ACROSS the two independently scheduled instances
    constraint sequence { sf1.a, sf2.b };
    constraint parallel { sf1.b, sf2.b, sf2.d };
}
```

Sequencing constraints on state objects:

```pss
enum mode_e { UNKNOWN, A, B }

state config_s {
    rand mode_e mode;
    constraint initial -> mode == UNKNOWN;      // the pool's starting object
    constraint !initial -> mode != prev.mode;   // every transition changes the mode
}

component codec_c {
    pool config_s cfg_var;
    bind cfg_var *;

    action configure {
        input  config_s prev_conf;
        output config_s next_conf;
        constraint prev_conf.mode == UNKNOWN && next_conf.mode in [A, B];
    }
}
```

## Rules

### Scheduling constraints (§13.2)

```
constraint (parallel | sequence) { hierarchical_id, hierarchical_id, … };
```

- They relate **two or more** already-traversed actions or named sub-activities. **They never
  introduce a traversal.**
- They only have effect in contexts that do not already dictate a relative scheduling — i.e.
  actions directly or indirectly under a `schedule` statement.
- `constraint sequence { … }` — each completes before the next starts (equivalent to a
  sequential activity block).
- `constraint parallel { … }` — invoked synchronized, then proceeding without further
  synchronization (equivalent to a `parallel` activity statement).
- **They may not be applied to action handles traversed more than once** — in particular, not to
  actions traversed inside `repeat`, `repeat…while`, or `foreach`. The **iterative statement
  itself**, as a named sub-activity, *can* be related.
- Constraints involving handles that are **never traversed**, or traversed only in a branch not
  chosen by a `select`/`if`, hold **vacuously**.
- **They shall not undo or conflict with the related actions' own scheduling requirements.**

### Sequencing constraints on state objects (§13.3)

- A state pool holds exactly one object at a time, so it acts as a **state variable**; any
  action outputting to it is a **transition** (§12.5).
- Inside a state type, **`prev`** references the previous state object of the same type,
  allowing boolean relations between this state and the last one.
- `prev` is **unresolved for the initial object** — guard with `!initial`.
- **`initial`** is true for the object present before any action writes the pool. Constrain it
  to define the starting state.
- `prev` and `initial` are available **only within a state type declaration or extension**, in
  relation to the state object itself. Accessing `initial` on an *instance field* of a state
  type is illegal.

## Gotchas

**Applying a scheduling constraint to a handle traversed in a loop.**
```pss
activity { repeat (4) { a; } }
constraint sequence { a, b };     // WRONG: `a` is traversed multiple times
```
*Tier 2.* Label the `repeat` and relate the label instead.

**A scheduling constraint that holds vacuously.**
```pss
activity { select { a; b; } }
constraint sequence { a, c };     // no effect on runs where `b` was selected
```
*Tier 4* — legal, silent, and does nothing half the time.

**A scheduling constraint inside a sequential block.** The block already dictates the order, so
the constraint either agrees (no effect) or conflicts (illegal). Scheduling constraints belong
with `schedule`.
*Tier 3.*

**Conflicting with a flow-object requirement.**
```pss
// a outputs a buffer that b inputs — b MUST follow a
constraint parallel { a, b };     // WRONG: contradicts the buffer's scheduling rule
```
*Tier 3.* Scheduling constraints may not undo existing requirements.

**`prev` on the initial state object.**
```pss
constraint mode != prev.mode;               // WRONG for the initial object
constraint !initial -> mode != prev.mode;   // RIGHT
```
*Tier 3–4.*

**A state machine that can only take one step.** A `configure` action requiring
`prev_conf.mode == UNKNOWN` can run **once** per pool, because nothing sets the mode back. If
the scenario needs repeated configuration, model the return transition too.
*Tier 4* — the model solves; the scenario is just much smaller than intended.

**Using `initial` on an instance field.** Illegal (§9.3.3.1c).
*Tier 2.*

**Expecting a scheduling constraint to force an action to exist.** It does not traverse
anything. If the action is not traversed, the constraint is vacuous.
*Tier 4.*

## See also

- `../activity/01-activities.md` — `schedule`, `parallel`, named sub-activities and
  hierarchical paths (which is how you name the operands here).
- `../activity/03-scheduling-semantics.md` — what `sequence` and `parallel` mean formally.
- `../structural/04-flow-objects.md` — `state` objects, `initial`, `prev`.
- `../structural/06-pools-and-binding.md` — state pools as state variables.
- `01-algebraic-constraints.md` — the value side.
