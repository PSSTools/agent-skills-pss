# Domain: coverage — what got exercised

Supporting domain. PSS has two distinct coverage mechanisms and they answer different questions.

| | `covergroup` (data coverage) | `cover` / `monitor` (behavioral coverage) |
|---|---|---|
| Answers | "which *values* did we hit?" | "which *scenarios* did we exercise?" |
| Samples | attribute values, at defined points | patterns of action execution over time |
| Declared in | actions, components, packages, monitors | packages, components |
| Clause | 15 | 16 (+ Annex F for formal semantics) |
| Page | `01-data-coverage.md` | `02-behavioral-coverage.md` |

The characteristic failure is **sampling the wrong thing** — a covergroup that samples a
value the user never cared about, or that samples at a point where the value is not yet
meaningful. It reports 100% and means nothing. Nothing checks this; tier 4.

---

## Decide

| The user said… | Use |
|---|---|
| "cover all the transfer sizes" | `covergroup` with a coverpoint on `size`, with explicit `bins` |
| "cover every combination of size and channel" | `covergroup` with a `cross` |
| "make sure we never generate an illegal length" | `illegal_bins` (not a constraint — this catches it if it happens) |
| "cover the case where a read follows a write" | behavioral coverage: `cover` with a `monitor` sequence |
| "cover that these two ran concurrently" | behavioral coverage: overlapping / scheduling scenario |
| "cover per DMA channel, not aggregated" | per-instance coverage (`option.per_instance`) |

### Rules that decide the design

- **Auto bins are almost never what you want.** A coverpoint with no `bins` gets automatic bins
  over the whole declared domain — for a `bit[32]` that is meaningless. Declare bins that match
  the user's intent, or narrow the field's domain.
- **Sampling point matters.** A covergroup in an action samples when that action is traversed.
  Values computed in `exec body` are *not* visible — see `../procedural/README.md` on the
  solve→target direction.
- **Behavioral coverage observes; it does not generate.** A `monitor` describes a pattern to
  recognize in the executed scenario. Writing one does not cause that scenario to be produced —
  if you need it produced, that is a constraint or an activity.

## Pages

| Page | Covers |
|---|---|
| `01-data-coverage.md` | `covergroup` declaration and instantiation, `coverpoint`, `bins`/`ignore_bins`/`illegal_bins`, `cross`, options, per-type and per-instance collection (Clause 15) |
| `02-behavioral-coverage.md` | `cover`, `monitor`, monitor activities (traversal, sequential, concatenation, eventuality, overlapping, selection, empty, scheduling), monitor action handles and constraints, covergroups in monitors (Clause 16) |

## See also

- `../activity/README.md` — monitor activities borrow activity syntax with observational
  semantics. Read both before writing one.
- `../constraints/README.md` — if the goal is to *produce* a case, not to *count* it.
- `../../playbooks/08-add-coverage.md` — task-first.
