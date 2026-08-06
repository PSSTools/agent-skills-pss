# Playbook: choosing constructs

*The first question: the user described something; what is it in PSS?*
*LRM Clause 5 (modeling concepts).*

## The decision, in order

Work down this list. The first row that fits is your answer.

| The user described… | It is a… | Then read |
|---|---|---|
| a piece of the system that *does* things — an engine, a block, an agent | `component` | `../lang/structural/02-components.md` |
| an operation — configure, transfer, reset, poll | `action` (atomic) | `../lang/structural/03-actions.md` |
| a test made of several operations | `action` (compound) with an `activity` | `../lang/activity/01-activities.md` |
| data one step makes and another uses | flow object — `buffer` / `stream` / `state` | `../lang/structural/04-flow-objects.md` |
| a condition or mode of the environment | `state` object | `../lang/structural/04-flow-objects.md` |
| "there are only N of these" | `resource` + `lock`/`share` | `../lang/structural/05-resource-objects.md` |
| a rule about legal values | `constraint` | `../lang/constraints/01-algebraic-constraints.md` |
| configuration fixed before the test | component attribute, set in `init_down`/`init_up` | `../lang/structural/02-components.md` |
| plain data with no scheduling meaning | `struct` | `../lang/data/02-data-types.md` |
| a device register map | `reg_c` / `reg_group_c` | `../lang/platform/04-registers.md` |
| memory to allocate | address claim | `../lang/platform/03-address-spaces.md` |
| which core / agent runs something | executor claim | `../lang/platform/01-executors.md` |
| "make sure we hit all of X" | `covergroup` | `../lang/coverage/01-data-coverage.md` |
| "make sure we exercised this sequence" | `cover` / `monitor` | `../lang/coverage/02-behavioral-coverage.md` |
| a variant of the model for a different SoC | `extend` in its own package | `../lang/structural/07-inheritance-extension-overrides.md` |

## The four confusions worth pre-empting

**Flow object vs resource.** A flow object is *exchanged* — the consumer cares what is in it. A
resource is *occupied* — the consumer only cares that nobody else has it. Modelling a DMA
channel as a `buffer` gives you data dependencies where you wanted exclusion.

**Activity structure vs flow objects.** Both create ordering. Prefer the flow object: it states
*why* the order exists, and it survives the action being reused in a different scenario.
Hard-coded `{ do a; do b; }` does neither.

**Component vs struct.** Can it own an action? Component. Otherwise struct. A component is a
position in the system; a struct is a value.

**`extend` vs inheritance.** `extend` changes a type everywhere it is already used; inheritance
creates a new type someone must choose. Project configuration is almost always `extend`.

## Building a model from a description — the usual order

1. **Components** — the structure of the system. What has actions? What has config?
2. **Actions** — one per operation the user named. Atomic first; compose later.
3. **Flow and resource objects** — the *relationships* between actions. This is where ordering
   and exclusion come from, so do it before writing any activity.
4. **Pools and binds** — every object reference needs one. `../lang/structural/06-pools-and-binding.md`
5. **Constraints** — the legal-value rules.
6. **Activities** — only the ordering the user actually asked for; let inference and flow
   objects do the rest.
7. **Realization** — `exec body`, functions, registers.
8. **Coverage** — last, once the shape is stable.

Steps 3 and 4 are the ones agents skip, and skipping them produces models that parse cleanly and
have no legal scenarios.

## What "good PSS" looks like

- Ordering has a stated reason (a flow object), not just a position in a block.
- Every object reference has a reachable pool.
- Constraints are the *rules*, not the *values you happened to want* — those are `soft` or
  `dist`.
- Realization code is on the right platform, and `comp` is never written.
- The model would still make sense if someone reused one of its actions elsewhere.

## See also

- `../lang/structural/README.md` — the domain that most of this list points into.
- `01-model-a-flow.md`, `02-model-a-resource.md`, `03-write-an-action.md` — the next step for
  the three most common answers.
- `../tooling.md` — before you claim any of it is correct.
