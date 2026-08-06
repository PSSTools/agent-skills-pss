# Playbook: diagnose

Two tables, because there are two kinds of symptom: **a message you have in hand**, and
**behaviour with no message at all**. The second is the larger one.

Before anything else, read `../tooling.md`:

- **Fix the first diagnostic, re-run, repeat.** Syntax errors cascade; the tail is noise.
- **A clean check means names resolve and braces match**, nothing more.
- **The tool may be wrong.** Verify against the cited clause before rewriting legal PSS.

---

## Table 1 — diagnostics, by message shape

Keyed on the **shape** of the message, not on any tool's exact wording or error codes. Grouped
by check tier (`../tooling.md`).

### Tier 1 — parse and name resolution

| Message shape | Usual cause | Go to |
|---|---|---|
| `expected ';' before …`, `unexpected '<token>'`, `unexpected end of input` | a real syntax error **at or before the first such message** — the rest is cascade | the relevant `lang/` page's *Canonical form* |
| `unknown type '<T>'` | missing `import`; or the name is ambiguous because two wildcard imports declare it | `../lang/structural/01-packages-and-name-resolution.md` |
| `unknown identifier '<x>'` on a field you added by extension | explicit import instead of a **wildcard** import | same |
| `unknown identifier` for an enum item | no enum type is expected in that context — qualify it | `../lang/data/04-expressions-operators.md` §type inference |
| `unknown method '<m>'` on a collection | wrong collection kind, or a deprecated property spelling (`a.size` vs `a.size()`) | `../lang/data/03-collections.md` |
| `duplicate declaration of '<x>'` | a `compile if` block introduces **no new scope**; or a label colliding with an action handle | `../lang/structural/09-conditional-code.md`, `../lang/activity/01-activities.md` |
| `cannot extend unknown type '<T>'` | the extension's package doesn't see the base type; or a typo in the type kind (`extend action` vs `extend struct`) | `../lang/structural/07-inheritance-extension-overrides.md` |
| `failed to resolve ref-path …` / `root ref-path element is not a composite scope` | a hierarchical path through an unlabelled activity statement, or through a `static` member via `comp` | `../lang/activity/01-activities.md`, `../lang/structural/02-components.md` |
| a rejection of `rand` in an exec or function | there is no grammar production for it | `../lang/procedural/03-procedural-statements.md` |
| a rejection of a template type used without `<>` | angle brackets are required even when every parameter defaults | `../lang/structural/08-templates.md` |

### Tier 2 — semantic elaboration

| Message shape | Usual cause | Go to |
|---|---|---|
| a `solve`/`target` function complaint | platform crossing — the #1 PSS error | `../lang/procedural/01-exec-blocks.md` |
| assignment to a component attribute rejected | `comp` is read-only outside `init_down`/`init_up`; consider `mutable` (3.1) | `../lang/structural/02-components.md` |
| parameter direction rejected | `input`/`output`/`inout` are for **imported** functions only | `../lang/procedural/02-functions.md` |
| a `const` parameter complaint on a literal argument | aggregate literals are constants; the parameter must be `const` | `../lang/procedural/02-functions.md` |
| `pure` rejected | on a `void` function, or one with `output`/`inout` parameters | same |
| a type mismatch in a pool bind | object and pool types must match **exactly** — no base/derived | `../lang/structural/06-pools-and-binding.md` |
| conflicting register offset schemes | all three offset functions implemented | `../lang/platform/04-registers.md` |
| a packed-struct extension rejected | extensions may not add fields to a `packed_s` | same |
| both `activity` and `exec body` rejected | atomic and compound are mutually exclusive | `../lang/structural/03-actions.md` |
| more than one executor claim | at most one anywhere under an action or object, nested structs included | `../lang/platform/01-executors.md` |

### Tier 3 — solve and generation

| Message shape | Usual cause | Go to |
|---|---|---|
| "no legal scenario" / unsatisfiable | see the triage below — it has **four** different causes | ↓ |
| unbindable input / no producer | no action outputs this type **in this pool** | `../lang/structural/06-pools-and-binding.md` |
| resource over-subscription | pool smaller than an array claim; or `lock` where `share` was right | `../lang/structural/05-resource-objects.md` |
| unschedulable activity | a `parallel` whose branches acquired different dependencies; or a scheduling constraint conflicting with a flow object | `../lang/activity/03-scheduling-semantics.md` |
| a constraint conflict reported after an exec | **no backtracking across exec blocks** — a `post_solve` or `body` assignment contradicts a constraint | `../lang/constraints/03-randomization.md` |

---

## Triage: "there is no legal scenario"

Four distinct causes with four different fixes. Check in this order — the cheapest first.

1. **A missing pool or bind.** Declaring a `pool` does **not** bind it. Every
   `input`/`output`/`lock`/`share` needs a `bind`, and the pool type must match the object type
   exactly. → `../lang/structural/06-pools-and-binding.md`
2. **Nothing can be inferred.** Does *any* action output that type, bound to the *same* pool,
   reachable from this action's component? → `../lang/activity/02-action-inferencing.md`
3. **A resource or executor claim that cannot be met.** Pool size vs array claim; two matching
   executor groups, or none. → `../lang/structural/05-resource-objects.md`,
   `../lang/platform/01-executors.md`
4. **Actually over-constrained.** Bisect the constraint blocks. Start with implications
   (reread every `->` backwards) and `forall`. → `05-constrain-and-randomize.md`

---

## Table 2 — symptoms with no diagnostic

These are **Tier 3** and **Tier 4**: the model is legal and the behaviour is wrong.
**Nothing will tell you.**

| Symptom | Likely cause | Go to |
|---|---|---|
| the test has more actions than you wrote | action inference satisfying an unbound input — expected; `atomic { }` to stop it | `../lang/activity/02-action-inferencing.md` |
| the scenario is far more rigid than asked for | sequential activity blocks where flow objects belonged | `04-write-an-activity.md` |
| nothing ever overlaps | resource pool of size 1, or `lock` where `share` was right, or a `buffer` where concurrency was needed | `02-model-a-resource.md` |
| everything overlaps; no contention | resource pool declared per-instance when the resource is system-wide | same |
| a base action's `exec body` stopped running | a derived `exec body` without `super;` | `../lang/procedural/01-exec-blocks.md` |
| a field is always its default | the path to it isn't `rand`; or it was written in `pre_solve` (overwritten by the solve) | `../lang/constraints/03-randomization.md` |
| a `soft` constraint didn't hold | it was contradicted and discarded — that is what `soft` means | `../lang/constraints/01-algebraic-constraints.md` |
| an enum field defaults to the wrong item | the default is the **first declared** item, not 0 | `../lang/data/02-data-types.md` |
| a constraint appears to have no effect | vacuous implication (antecedent never true), or a vacuous `unique` on an empty slice | `../lang/constraints/01-algebraic-constraints.md` |
| a value is truncated | a shift or `**` takes the **left operand's** width; mixed signedness goes unsigned | `../lang/data/04-expressions-operators.md` |
| a runtime error on an unmatched `match` | no `default` and the arms don't cover the domain | `../lang/procedural/03-procedural-statements.md` |
| a function returns a stale value | mislabelled `pure` — the tool cached it | `../lang/procedural/02-functions.md` |
| a `message()` argument never evaluated | verbosity gating may elide it; never pass side effects | `../lang/platform/05-core-library-api.md` |
| the test hangs | a target polling loop with no `yield;`, or a channel `get()` the solver never ordered a `put()` before | `../lang/platform/02-sync-and-communication.md` |
| register access goes to a wrong address | an element missing from the offset function (`default: return -1;`), or `set_handle()` on a nested group | `../lang/platform/04-registers.md` |
| the allocator hands out MMIO addresses | region added with `add_region()` instead of `add_nonallocatable_region()` | `../lang/platform/03-address-spaces.md` |
| an address is undefined at solve time | `addr_value_solve()` called outside `pre_body` | same |
| coverage reports 100% and means nothing | auto bins on a wide integer coverpoint | `../lang/coverage/01-data-coverage.md` |
| a covergroup never samples | it samples a value produced on the target platform | same |
| a monitor never matches | monitors observe; they do not generate | `../lang/coverage/02-behavioral-coverage.md` |
| results differ between tools | reliance on an explicitly unspecified order: extension order, sibling init order, sibling solve-exec order, `map` iteration, monitor first-match selection | the relevant page |
| duplicate `#include`s in generated code | untagged `header` templates match nothing and are emitted per instance | `../lang/procedural/01-exec-blocks.md` |
| an extension's fields are invisible | explicit import instead of wildcard | `../lang/structural/01-packages-and-name-resolution.md` |
| a disabled `compile if` branch breaks when enabled | disabled branches are checked for **syntax only** | `../lang/structural/09-conditional-code.md` |

## Last resort

If the behaviour still doesn't match the rules on the page: reduce to the smallest model that
reproduces it, compare against that page's *Canonical form*, and check the cited clause. If the
clause says your code is legal, you have a tool gap or a version lag (`../tooling.md`) — report
it, don't rewrite around it.

## See also

- `../tooling.md` — check tiers and cross-tool realities.
- `../../checklists/review.md` — the pre-flight pass that catches most of Table 2 before it
  happens.
