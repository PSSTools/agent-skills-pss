# Behavioral coverage: `cover` and `monitor`

*Domain: coverage. LRM Clause 16; formal semantics in Annex F.*

Answers "which **scenarios** did we exercise?". Where a `covergroup` samples values, a
`monitor` recognizes a *pattern of action executions over time*.

> **A monitor observes. It does not generate.** Writing a monitor for "read after write" does
> not cause a read-after-write to be produced. If you need it produced, that is a constraint or
> an activity. This is the single most important thing on this page.

## When you are writing this

- The user said "cover the case where a read follows a write".
- The user wants evidence about *ordering* or *concurrency*, not values.
- The user wants coverage of a sequence that spans several actions.
- You need coverage that is per-scenario rather than per-action.

## Decide

| The pattern to observe | Statement |
|---|---|
| one action execution | action traversal (`do read;` / `r;`) |
| A then B, gaps allowed | `sequence { … }` (or a bare `{ … }`) |
| A then B, **immediately** — B's checkpoint is A's match point | `concat { … }` |
| A, then B **at some later point** | `eventually <stmt>;` |
| all of these, any order, no shared executions | `schedule { … }` |
| all of these, **simultaneously active at some instant** | `overlap { … }` |
| any one of these | `select { … }` |
| a reusable named pattern | `monitor m { … }` traversed with `do m;` |
| relate the observed executions' data | action handles + `constraint` |
| count values along the observed scenario | a `covergroup` inside the monitor / cover statement |

**`sequence` vs `concat`** is the pairing that gets confused. `sequence` allows an arbitrary
gap between subscenarios; `concat` requires the next to start exactly at the previous one's
match point.

**`schedule` vs `overlap`**: `schedule` requires only that the realizations be pairwise
disjoint, with any gaps or overlaps; `overlap` additionally requires a **time instant at which
all member scenarios are simultaneously active**.

## Canonical form

```pss
action read  { rand locked_e     lock_mode;  }
action write { rand write_mode_e write_mode; }

// in-line cover statement
c1 : cover {
    write w;
    read  r;
    activity {
        w;
        r;                                  // a read after a write
    }
    constraint w.addr == r.addr;            // ...from the same address
    covergroup {
        cpw : coverpoint w.write_mode;
        cpr : coverpoint r.lock_mode;
        wXr : cross cpw, cpr;
    } cg;
}

// a named, reusable monitor
monitor rd_after_wr {
    write w;
    read  r;
    activity { concat { w; r; } }           // immediately consecutive
    constraint w.addr == r.addr;
}

component pss_top {
    c2 : cover rd_after_wr;                 // instantiate the monitor type

    monitor twice {
        activity { schedule { do rd_after_wr; do rd_after_wr; } }
    }
}
```

## Rules

### `cover` and `monitor` (§16.1)

- `[label:] cover type_identifier;` or `[label:] cover { monitor_body_items }`.
- **Cover statements are only active in component instances actually instantiated from the root
  component.**
- **Monitors are the coverage counterpart of actions.** All rules applicable to actions apply
  to monitors unless stated otherwise.
- Monitor body: activity, constraints, fields, covergroups, `override`, `compile if`,
  annotations.
- **Monitor fields may be action handles and monitor handles only.** Data attributes,
  references, and resource claims are **not supported**; other data fields must be
  `static const`.
- **A non-abstract monitor — initial definition plus all extensions — shall have one or more
  activity statements.** An abstract monitor may have none.
- `abstract monitor` follows the same rules as abstract actions: not instantiable directly; may
  derive only from another abstract monitor; extension leaves it abstract.
- **If a monitor declares more than one activity, the result is those scenarios combined in a
  `schedule`** (§16.3.8).

### Monitor activity statements (§16.3)

| Statement | Semantics |
|---|---|
| action traversal | observes an execution of that action (atomic or compound). Same syntax as an activity traversal, but inline constraints use the **monitor** constraint set |
| `[sequence] { … }` | consecutive matching, **arbitrary gaps allowed**: each subscenario matched at or after the previous one's match point |
| `concat { … }` | **immediate** consecutive matching: the next subscenario's checkpoint **is** the previous one's match point |
| `eventually stmt;` | matches the sub-scenario at **any** checkpoint t ≥ t₀ |
| `overlap { … }` | as `schedule`, plus **a time instant where all members are simultaneously active** |
| `schedule { … }` | members in any order, gaps and overlaps allowed, realizations **pairwise disjoint** |
| `select { … }` | realizations are the union of the alternatives' realizations |
| empty | `monitor m {}`, `activity {}`, `{}`, `sequence {}`, `concat {}`, `eventually {}`, `schedule {}`, `overlap {}` |
| monitor traversal | `do monitor_t;` or a declared monitor handle; may carry an initializer list and inline constraints |

**The empty scenario always has a realization, and that realization is empty (∅).** This is
distinct from an *empty set of realizations*, which means the attempt failed. An empty member
inside a sequence/concat/schedule/overlap therefore contributes nothing but does not fail.

### Action handles and constraints (§16.4)

Handles exist for readability and for **constraining which realizations count**. A monitor
constraint restricts the observed executions' attributes — e.g. `constraint w.addr == r.addr;`
turns "a read after a write" into "a read after a write to the same address".

### Covergroups in monitors (§16.5)

- **A monitor covergroup is sampled at the *first match* of the attempts of the cover statement
  in which the monitor is traversed** (directly or indirectly).
- Sampling uses the action-handle mapping of that first-match realization. **If several
  first-match realizations exist, the implementation may pick any of them.**
- Per-instance coverage in cover statements and monitors follows §16.5.2.

### Extension and inheritance (§16.6)

Monitor activity evaluation with extension and inheritance mirrors §11.6 for actions: a derived
monitor's activity shadows the base's, reachable with `super;`; extensions are additive.

### Formal semantics

Annex F defines realizations, checkpoints and match points precisely. Consult it when the
informal descriptions above are not enough to decide whether a trace matches — particularly for
nested `eventually` and `overlap`.

## Gotchas

**Expecting a monitor to generate the scenario.** It only observes. A cover statement with no
matching traffic simply reports nothing.
*Tier 4* — this is the most common misunderstanding of behavioral coverage.

**Using `sequence` when `concat` was meant.** `sequence { w; r; }` matches a read *any time*
after a write, with arbitrary traffic in between. If "immediately after" matters, use `concat`.
*Tier 4.*

**Using `schedule` when `overlap` was meant.** `schedule` does not require any temporal overlap;
it only requires disjoint realizations.
*Tier 4.*

**A data attribute in a monitor.**
```pss
monitor m { rand bit[8] x; }            // WRONG: no data attributes in monitors
monitor m { static const int X = 4; }   // RIGHT
```
*Tier 2.*

**A non-abstract monitor with no activity.** Required to have one or more (§16.1).
*Tier 2.*

**A cover statement in a component that is never instantiated from the root.** Silently
inactive.
*Tier 4.*

**Assuming which realization was sampled.** With multiple first-match realizations, the choice
is implementation-defined — so covergroup results in a monitor can differ between tools on the
same trace.
*Tier 4.*

**Unconstrained handles making the pattern trivial.** `sequence { w; r; }` with no constraint
matches almost any trace containing both. Constrain the handles to express the actual intent.
*Tier 4.*

**Empty scenario mistaken for a failed match.** An empty scenario always matches, with an empty
realization.
*Tier 4.*

**Inline constraints written with the action constraint set.** In a monitor traversal they must
use the **monitor** constraint set (§16.3.1).
*Tier 1–2.*

## See also

- `01-data-coverage.md` — `covergroup`, including the ones you instantiate inside monitors.
- `../activity/01-activities.md` — the activity syntax monitors borrow, with generation
  semantics.
- `../activity/03-scheduling-semantics.md` — what "simultaneously active" means.
- `../structural/03-actions.md` — the actions being observed.
- `../../playbooks/08-add-coverage.md` — task-first.
