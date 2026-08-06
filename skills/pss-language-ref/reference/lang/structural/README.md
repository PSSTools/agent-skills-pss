# Domain: structural — the model skeleton

You are here because you are **declaring things**: what types exist, what they contain, where
they live, and how they find each other. Nothing on this page runs; it all describes shape.

The characteristic failure of this domain is **wrong containment** — a type declared in a place
that cannot reach what it needs, most often an action whose `input`/`output`/`lock` cannot be
bound because no pool of that type is visible from its context component. That failure surfaces
much later, as an empty solution space, with no message pointing back here.

---

## Decide: which structural construct?

| You want to express… | Use | Page |
|---|---|---|
| a unit of behavior the tool may schedule | `action` | `03-actions.md` |
| behavior composed of other behavior | compound `action` with an `activity` | `03-actions.md`, then `../activity/` |
| a piece of the DUT/environment that owns actions and config | `component` | `02-components.md` |
| configuration data fixed before the test is solved | component attribute | `02-components.md` |
| data one action produces and another consumes, persistently | `buffer` | `04-flow-objects.md` |
| data exchanged *while both actions run* | `stream` | `04-flow-objects.md` |
| a mode/condition of the environment, with history | `state` | `04-flow-objects.md` |
| "there are only N of these" / mutual exclusion | `resource` + `lock`/`share` | `05-resource-objects.md` |
| the container that makes objects available to actions | `pool` + `bind` | `06-pools-and-binding.md` |
| plain data with no scheduling meaning | `struct` | `../data/02-data-types.md` |
| a namespace, and a home for extensions | `package` | `01-packages-and-name-resolution.md` |
| "same type, extra fields, everywhere" | `extend` | `07-inheritance-extension-overrides.md` |
| "a variant of this type" used explicitly | inheritance (`: base`) | `07-inheritance-extension-overrides.md` |
| "everywhere `A` is used, use `B` instead" | `override` | `07-inheritance-extension-overrides.md` |
| a type parameterized by a value or another type | template type | `08-templates.md` |
| code that exists only in some configurations | `compile if` | `09-conditional-code.md` |

### The two choices that go wrong most often

**`buffer` vs `stream` vs `state`** — decided by *when* producer and consumer run, and it is a
hard scheduling constraint, not a hint:

| | Producers | Consumers | Scheduling |
|---|---|---|---|
| `buffer` | exactly 1 | 0 or more | consumer starts **after** producer completes |
| `stream` | exactly 1 | exactly 1 | producer and consumer start **at the same time** |
| `state` | pool holds one object at a time | any number of readers | a writer is never concurrent with any other reader or writer of that pool |

If you find yourself wanting "produced by one, consumed by many, concurrently", you want a
`buffer` read by several actions — not a `stream`.

**Flow object vs resource** — a flow object is *exchanged*; a resource is *occupied*. If the
consumer cares what is in it, it's flow. If the consumer only cares that nobody else has it,
it's a resource. Modeling a DMA channel as a `buffer` is the classic error: you get data
dependencies where you wanted exclusion.

**`extend` vs inheritance** — `extend` changes a type *everywhere it is already used*, without
touching the code that uses it; inheritance creates a *new* type that someone must explicitly
choose. Use `extend` for "this SoC's version of the model", inheritance for "a kind of".

---

## Pages

| Page | Covers |
|---|---|
| `01-packages-and-name-resolution.md` | `package`, nested packages, `import`, aliases, declaration/reference ordering, name lookup (Clause 18) |
| `02-components.md` | `component`, `pss_top`, instantiation, attributes and their mutability, `comp`, component refs, `pure component` (§9.1) |
| `03-actions.md` | atomic vs compound actions, action fields, `abstract`, action inheritance (§9.2) |
| `04-flow-objects.md` | `buffer`, `stream`, `state`, `input`/`output`, object-reference arrays (§9.3) |
| `05-resource-objects.md` | `resource`, `lock`, `share`, `instance_id` (§9.4) |
| `06-pools-and-binding.md` | `pool`, `bind`, default vs explicit binding, state pools and `initial`, hierarchical binding (Clause 12, §11.9–11.11) |
| `07-inheritance-extension-overrides.md` | `: base`, `extend`, extension ordering, access protection, `override` (Clause 17) |
| `08-templates.md` | template value and type parameters, instantiation, restrictions (Clause 10) |
| `09-conditional-code.md` | `compile if`, `compile has`, compile-time expressions (Clause 19) |

## See also

- `../activity/README.md` — once the types exist, this is how they get composed.
- `../constraints/README.md` — the legal-value rules that live inside these declarations.
- `../platform/README.md` — components that model registers and address spaces.
- `../../playbooks/00-choosing-constructs.md` — the same decision, task-first.
