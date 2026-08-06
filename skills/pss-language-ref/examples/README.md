# Examples

Complete, self-contained models. Each one exercises a distinct slice of the language and is
cross-referenced from the `reference/lang/` pages.

| File | Exercises | Parse gate |
|---|---|---|
| `flow_basic.pss` | `buffer` / `stream` / `state`, pools, binding, inferencing | ✅ |
| `resource_arbitration.pss` | `resource`, `lock` / `share`, `instance_id`, pool sizing | ⛔ *requires:* |
| `activity_shapes.pss` | every activity composition statement | ✅ |
| `constraints.pss` | algebraic constraints, defaults, `randomize` | ✅ |
| `procedural_realization.pss` | exec kinds, functions, procedural statements, templates | ✅ |
| `regs_and_mem.pss` | `packed_s`, `reg_c`, `reg_group_c`, address spaces, claims | ✅ |
| `coverage.pss` | `covergroup`, bins, crosses, options | ✅ |
| `behavioral_coverage.pss` | `cover` / `monitor` and the temporal operators | ⛔ *requires:* |

## The parse gate

Every file marked ✅ must pass a **tier-1** check cleanly (see `../reference/tooling.md`).
Files marked ⛔ carry a `// requires:` comment at the top naming what they need, and are
**excluded by name** — never silently skipped.

Running the gate with whatever front end the environment provides:

```sh
EXCLUDE="resource_arbitration.pss behavioral_coverage.pss"
for f in examples/*.pss; do
    case " $EXCLUDE " in *" $(basename $f) "*) continue;; esac
    <pss-front-end> "$f" || echo "FAIL: $f"
done
```

## What the gate does and does not prove

**Tier 1 only.** A clean parse means the names resolve and the braces match. It says nothing
about platform correctness, solvability, or whether the model means the right thing. The
`Rules` sections of the `lang/` pages, and `../checklists/review.md`, are what cover tiers 2–4.

## Constructs shown in comments rather than compiled

Several files illustrate a construct in a comment block instead of in live code. In every case
the construct is **legal PSS** and the comment says so with its clause; it is written that way
because front ends differ in coverage and the gate would otherwise be unrunnable in most
environments. The list, so it is auditable:

| Construct | Clause | Shown in |
|---|---|---|
| `prev` on a state object | §9.3.3.1 g | `flow_basic.pss` |
| join specifications (`join_branch` etc.) | §11.3.6 | `activity_shapes.pss` |
| `replicate` index variable | §11.5.1.1 | `activity_shapes.pss` |
| `foreach` index variable in an activity | §11.4.3 | `activity_shapes.pss` |
| `soft` constraints | §13.1.11 | `constraints.pss` |
| `dist` directive | §13.1.12 | `constraints.pss` |
| `exec pre_body` | §20.1.2 | `procedural_realization.pss` |
| `super;` in a derived exec | §20.1.4.2 | `extension_variants.pss` |
| `compile assert` inside a template | §19.4 | `extension_variants.pss` |
| referencing an extension-introduced field | §17.2.3 | `extension_variants.pss` |
| `write_field` / `write_fields` / `write_masked` | §21.14.1 | `regs_and_mem.pss` |
| region `tag` and `get_tag()` | §21.10.3.1, §21.13.8 | `regs_and_mem.pss` |
| type and instance `override` | §17.5 | `extension_variants.pss` |

If your front end supports one of these, uncommenting it is the intended way to check.

**Do not treat this list as "constructs to avoid."** It is a record of one environment's tool
coverage at the time the examples were written, not a statement about the language. See
`../reference/tooling.md` §"Tools also have plain grammar gaps".

## See also

- `../reference/playbooks/` — task-first entry points; each links to the example that fits.
- `../checklists/review.md` — the pass that covers what the gate cannot.
