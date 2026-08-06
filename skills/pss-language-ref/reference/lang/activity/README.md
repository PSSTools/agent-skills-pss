# Domain: activity — what happens, and in what order

You are here because you are writing an `activity {}` body: composing actions into a scenario.

**The one idea to internalize:** an activity specifies a *partial order*, not a program. You are
describing which schedulings are legal, and the tool picks one. Writing an activity as if it
were a sequence of function calls produces models that are technically legal and far more
rigid than intended — that is this domain's characteristic failure, and nothing will warn you.

The second failure mode is the opposite: leaving so much implicit that no legal schedule exists
(uninferable action, unbindable flow object), which surfaces as a tier-3 solver failure with no
line number.

---

## Decide: how much should I say?

Start at the top and stop as soon as the row is true. **Prefer the least specific form that is
still correct** — every extra ordering constraint removes scenarios the user wanted.

| The requirement is… | Write | Why not more |
|---|---|---|
| "these things must happen, order doesn't matter" | `schedule { ... }` | the tool finds a legal order, including a sequential one if needed |
| "these start together" | `parallel { ... }` | forces simultaneous start — only correct if that is the actual requirement |
| "Y needs what X produced" | *nothing* — connect them with a flow object | the data dependency **is** the ordering; stating it again over-constrains |
| "Y must follow X, and it's not about data" | sequential block (`{ a; b; }` or `sequence {}`) | fine, but ask whether a `state` object expresses the real reason |
| "one of these, tool's choice" | `select { ... }` | |
| "one of these, per a solved value" | `if`/`else` or `match` on a `rand` field | branch is decided at solve time |
| "N of these, N chosen by the solver" | `repeat (n)` with `rand` n | |
| "N of these, and I need to refer to them individually" | `replicate (n) L[]:` | `repeat` gives you no handles; `replicate` gives a label array |
| "keep going until a condition holds" | `repeat {...} while (expr)` | |
| "once per element of this collection" | `foreach` | |

### `parallel` vs `schedule` — the single most common activity error

`parallel` says *"these begin at the same time"*. `schedule` says *"these all happen; any legal
order is fine, including overlapping"*.

Most requirements phrased as "do these concurrently" are actually `schedule`. Reach for
`parallel` only when simultaneous start is genuinely required — which in practice means you are
connecting a `stream` object, whose producer and consumer *must* start together anyway.

### Sequential block vs flow object

```pss
// over-specified: works, but only ever produces one order
activity { do configure; do transfer; }

// says the actual reason, and lets the tool reorder/interleave anything independent
action configure { output cfg_s cfg; }
action transfer  { input  cfg_s cfg; }
activity { do configure; do transfer; }   // ordering now comes from the data
```

The second form also survives being reused inside a larger scenario. The first does not.

### Explicit traversal vs inferencing

`do a;` names an action. But if `a` has an unbound `input`, the tool will *infer* a producer
for it — possibly an action you never mentioned. That is a feature (it is how partially
specified scenarios get filled in) and a trap (you get actions you did not ask for). See
`02-action-inferencing.md` before assuming a scenario is fully specified by its activity.

---

## Pages

| Page | Covers |
|---|---|
| `01-activities.md` | `activity`, `do`, action handles and arrays, sequential/`parallel`/`schedule`, join specs, `select`, `if`/`match`, `repeat`, `foreach`, `replicate`, named sub-activities, symbols, `atomic` (Clause 11) |
| `02-action-inferencing.md` | how unbound inputs pull in producers, what limits inference, pools' role, data constraints and inference (Clause 14) |
| `03-scheduling-semantics.md` | the formal scheduling model: sequential/parallel/concurrent, what "completes" means, scheduling assumptions the tool is allowed to make (Clause 6) |

## See also

- `../structural/04-flow-objects.md` — the scheduling rules that flow objects impose. Read
  this *before* deciding you need a sequential block.
- `../constraints/02-scheduling-constraints.md` — `constraint { A before B; }` and friends:
  ordering expressed as a constraint rather than as activity structure.
- `../coverage/02-behavioral-coverage.md` — `monitor` activities look like activities but
  describe *observation*, not generation. Different semantics; easy to conflate.
- `../../playbooks/04-write-an-activity.md` — task-first version of this decision.
