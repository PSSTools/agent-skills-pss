# Domain: procedural — implementing behavior

You are here because you are writing code that *runs*: an `exec` block, a function body, or the
glue that reaches foreign code.

Everything in this domain is ordinary imperative code. What makes it PSS-specific — and what
makes it the domain where illegal code is written most often — is that PSS restricts **where
each piece runs** and **what it may touch**.

---

## Decide this first: which platform?

Every piece of procedural code runs on the **solve platform** (during generation, while the
scenario is being computed) or the **target platform** (in the generated test, on the DUT).

| exec kind | Valid in | Platform | Purpose |
|---|---|---|---|
| `init_down`, `init_up` | component | solve | assign component attributes as the tree elaborates (down = parent first, up = child first) |
| `pre_solve` | action, flow/resource object, struct | solve | initialize **non-rand** fields the solve will read |
| `post_solve` | action, flow/resource object, struct | solve | compute non-rand fields from solved `rand` values |
| `pre_body` | action, flow/resource object, struct | solve | after executor assignment and address allocation, before body codegen |
| `body` | **action only** | target | the runtime implementation of an atomic action |
| `run_start`, `run_end` | action, flow/resource object, struct | target | one-time test bring-up / bring-down |
| `header`, `declaration` | action, flow/resource object, struct | target | `#include`s and globals — **target-template text only**, never procedural |

Consequences, all of which are rules:

- A `solve function` shall not be called, directly or transitively, from `body` / `run_start` /
  `run_end`.
- A `target function` shall not be called from `init_down` / `init_up` / `pre_solve` /
  `post_solve` / `pre_body`.
- An **unqualified** function is available on both. That is the default and usually right for
  pure computation.
- Multiple exec blocks of the same kind in one scope concatenate in source order.

```pss
function       int      compute(int a, int b);       // both platforms
solve function bit[32]  alloc_addr(bit[32] sz);      // generation only
target function void    poke(bit[32] a, bit[32] d);  // runtime only

action xfer {
    rand bit[32] size;
    bit[32]      addr;                  // NOT rand: computed after the solve

    exec post_solve { addr = alloc_addr(size); }     // solve fn, solve exec — OK
    exec body       { poke(addr, size); }            // target fn, target exec — OK
}
```

### The direction of information flow

Solve → target, never back. A value computed in `exec body` cannot influence a constraint, a
coverage sample, or another action's attributes. If you need the target to affect the scenario,
you need a different model, not a different exec kind. (§13.4.13)

---

## Decide: how do I reach code outside PSS?

In order of preference:

| Mechanism | Use when | Page |
|---|---|---|
| native PSS function | the logic is computation | `02-functions.md` |
| `import C/CPP/SV function` | you must call a real function that exists in the target/solve environment | `04-foreign-interface.md` |
| target template (`exec body C = """…"""`) | you need to *emit text* into the generated test | `04-foreign-interface.md` |
| `export action` | foreign code needs to invoke PSS | `04-foreign-interface.md` |

Templates are text substitution, not calls: `{{expr}}` interpolates, references are **read-only**,
and only scalars may be referenced. If you find yourself wanting to assign a PSS variable from a
template, you want an imported function instead.

---

## Pages

| Page | Covers |
|---|---|
| `01-exec-blocks.md` | all exec kinds, platform rules, inheritance/`super`/extension, evaluation order, target-template execs and tags (§20.1, §20.5) |
| `02-functions.md` | declarations, `solve`/`target`/`pure`/`static`, parameters, `const`, defaults, varargs, parameter-passing semantics, calling rules (§20.2, §20.3) |
| `03-procedural-statements.md` | variable declarations, assignment, `if`, `match`, `repeat`, `while`, `foreach`, `break`/`continue`, `return`, `randomize`, `yield` (§20.7) |
| `04-foreign-interface.md` | imported functions and classes, exported functions and actions, target templates, mapping-mechanism comparison (§20.4–20.6, §20.9, §20.10) |

## See also

- `../data/README.md` — what your variables may hold, and how aggregates copy.
- `../platform/README.md` — the core-library APIs most exec bodies actually call: registers,
  memory access, executors, messages.
- `../structural/02-components.md` — where component data lives and why `comp` is read-only.
- `../../playbooks/07-connect-to-c-cpp-sv.md` — task-first version of the foreign-interface
  decision.

## Before you call this done

1. Every function called from a target exec has a target-available definition; every function
   called from a solve exec has a solve-available definition.
2. No `rand` declarations in procedural scope; no component-attribute writes outside
   `init_down`/`init_up`.
3. Native functions declare **no** parameter directions; aggregates the callee must not mutate
   are `const`.
4. Every `match` has a `default` or provably covers its domain; arms do not overlap.
5. `foreach` bodies do not write the collection, the index, or the iterator.
6. `pure` appears only on side-effect-free, non-`void`, output-free functions.
7. Non-`void` calls used as statements are discarded explicitly: `(void)f();`
8. `message()` gets solve-time-known verbosity, format string, and string arguments, and no
   argument with a side effect.
