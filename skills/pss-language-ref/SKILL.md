---
name: pss-language-ref
description: Write, review, and debug PSS (Portable Test and Stimulus, Accellera 3.1) source. Covers the
  whole language — components, actions, flow/resource objects, pools and binding, activities and action
  inferencing, constraints and randomization, data types and collections, exec blocks, native/imported/
  target-template functions, procedural statements, data and behavioral coverage, packages and extension,
  and the core library (executors, address spaces, registers, sync). Use when authoring PSS models,
  reviewing PSS for correctness, choosing between PSS constructs, decoding a PSS tool diagnostic, or
  answering "is this legal PSS?".
---

# PSS language reference

Reference data for writing *good* PSS, organized so you can find the rule that governs the
line you are about to write. Clause citations are to **PSS 3.1 Draft 19 (July 14 2026)**.

**Start here → pick a route below. Do not read this file top-to-bottom and start typing.**

---

## Route 1 — task first (most common)

The user described something they want; you need to know what construct that *is*.

| The user is asking for… | Read |
|---|---|
| "which construct do I use for…?", first orientation on a new model | `reference/playbooks/00-choosing-constructs.md` |
| data produced by one step and consumed by another | `reference/playbooks/01-model-a-flow.md` |
| something exclusive or limited-count (channels, DMA engines, ports) | `reference/playbooks/02-model-a-resource.md` |
| "an operation that does X" — a single unit of behavior | `reference/playbooks/03-write-an-action.md` |
| "test that does X then Y", scenario shape, ordering, concurrency | `reference/playbooks/04-write-an-activity.md` |
| legal-value rules — "must be aligned", "never both", distributions | `reference/playbooks/05-constrain-and-randomize.md` |
| register programming, memory buffers, addresses, DMA descriptors | `reference/playbooks/06-access-registers-and-memory.md` |
| "call my C function", "emit this SystemVerilog" | `reference/playbooks/07-connect-to-c-cpp-sv.md` |
| "make sure we hit all the combinations" | `reference/playbooks/08-add-coverage.md` |
| reuse, variants, "same model, different SoC", refactoring | `reference/playbooks/09-organize-and-extend-a-model.md` |
| a tool or solver error message; PSS that behaves wrongly | `reference/playbooks/10-diagnose.md` |

## Route 2 — construct first

The user named a construct, or you are mid-file and need the rules for what you are writing.

| You are writing… | Domain |
|---|---|
| components, actions, flow/resource objects, pools, packages, `extend`, templates | `reference/lang/structural/` |
| `activity{}` bodies, traversal, ordering, inferencing | `reference/lang/activity/` |
| `exec` bodies, functions, foreign calls, procedural statements | `reference/lang/procedural/` |
| types, literals, collections, expressions, annotations | `reference/lang/data/` |
| `constraint` blocks, `randomize`, solve ordering | `reference/lang/constraints/` |
| `covergroup`, `cover`, `monitor` | `reference/lang/coverage/` |
| executors, address spaces, registers, `std_pkg` and friends | `reference/lang/platform/` |

Each domain has a `README.md` with its own decision table and page list. Two hops: here → domain
README → page.

## Route 3 — keyword first

You saw a token in the user's source and need to know what it does:
**`reference/INDEX.md`** — every PSS keyword and core-library type, mapped to a page.
It also carries the LRM clause → page map.

## Other entry points

- `reference/tooling.md` — what a PSS tool will and will not catch. **Read before claiming
  PSS is correct.**
- `reference/3.1-deltas.md` — what is new in 3.1; what to avoid when the tool targets 3.0.
- `checklists/review.md` — pre-flight pass before declaring PSS done.
- `examples/` — complete, checkable models.

---

## The shape of a PSS model

Orientation, so the domain names mean something.

```
package my_pkg {                  // namespace: types, functions, extensions
    struct cfg_s { ... }          // plain data
    action-and-object types may live here too

    component dma_c {             // structural: instantiated into a tree under pss_top
        bit[32] base_addr;        // config data — set during elaboration, read-only after
        pool mem_seg_s  seg_p;    // pools hold the objects actions exchange
        bind seg_p *;

        action xfer {             // an atomic action: one unit of behavior
            rand bit[16] size;    // solvable attributes
            input  mem_seg_s src; // flow: what it needs
            output mem_seg_s dst; // flow: what it produces
            constraint size in [4..4096];        // legal-value rules
            exec body { ... }     // realization: what actually happens on the target
        }

        action test {             // a compound action: composes other actions
            activity {
                do xfer;          // traversal
                parallel { do xfer; do xfer; }
            }
        }
    }
}
component pss_top { my_pkg::dma_c dma; }   // the implicit root
```

Two halves, and they obey different rules:

| Half | Constructs | Runs when |
|---|---|---|
| **Declarative / scenario** | `action`, `activity`, flow & resource objects, `pool`, `constraint`, coverage | solved by the tool before the test exists |
| **Realization / procedural** | `component` data, `function`, `exec`, procedural statements, registers | on the **solve platform** during generation, or on the **target platform** at test runtime |

---

## Always-load rules

The ten rules that are broken most often. Everything else, look up.

1. **Solve platform vs. target platform is a hard partition.** A `solve function` shall not be
   called from `exec body` / `run_start` / `run_end`; a `target function` shall not be called
   from `init_down` / `init_up` / `pre_solve` / `post_solve` / `pre_body`. (§20.2.1.3)
2. **`comp` is read-only.** Component attributes are set during elaboration — in `init_down` /
   `init_up` — and read thereafter. An action never writes `comp.<field>`. (§9.1.6)
3. **No `rand` declarations in procedural scope.** Randomness inside an exec or function comes
   from the `randomize` statement or `urandom()`. (§20.7.2)
4. **Native PSS functions take no parameter directions.** `input`/`output`/`inout` are for
   *imported* functions only. Native aggregates pass by handle — mark them `const` if the
   callee must not mutate them. (§20.2.2, §20.3.2)
5. **An action's `body` sees only solved values.** Anything computed on the target platform
   cannot feed back into constraints, coverage, or another action's attributes. (§13.4.13)
6. **Flow objects connect actions; resource objects exclude them.** `buffer`/`stream`/`state`
   for produced-and-consumed data; `resource` for "only N of these at once". (§9.3, §9.4)
7. **Every input needs a reachable pool.** An `input`/`output`/`lock`/`share` is only bindable
   if a `pool` of that type is bound to that action's context component. Unbound ⇒ no
   scenario. (Clause 12)
8. **Traversal is `do <action>`, not a function call.** An activity schedules actions; it does
   not execute them. Sequencing in an activity is a *partial* order, not a program. (§11.3)
9. **`match` needs a `default`** unless the arms provably cover the domain — no matching arm is
   an error at runtime, and nothing checks it statically. (§20.7.9)
10. **Register groups implement exactly one offset scheme** — either `get_offset_of_path()`, or
    both of `get_offset_of_instance()` / `get_offset_of_instance_array()`. Never all three.
    (§21.14)

---

## After you write PSS

**Always check it with whatever PSS tooling this environment provides.** Discover the tool the
normal way (its own skill, `--help`, the project's build files); this skill deliberately names
none, because the check *tiers* matter and the tool does not.

Then interpret the result honestly:

> A clean check means the names resolve and the braces match. It does **not** mean the model is
> correct. See `reference/tooling.md` §Check tiers — most of what makes PSS wrong is invisible
> to a parser, and some of it is invisible to every tool.

If the tool rejects something this reference says is legal, check the cited clause before
"fixing" it: tools lag the standard and have grammar gaps. Do not rewrite valid PSS to appease
a tool — say what happened.

## Related skills

- `pss-coding-guidelines` — *where code goes* in this repository (file and directory
  conventions). This skill is deliberately neutral about project layout.
