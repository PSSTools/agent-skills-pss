# Checker rules: platform qualification

Checker `name = "pss-platform"`. All tier 2. **Implemented** —
`packages/pss-lang-checkers/src/pss_lang_checkers/platform.py`, with the triggering and
near-miss examples below as its test suite.

These were implemented first because they are the most frequently violated rules in PSS, are
decidable from the linked AST alone, and carry minimal false-positive risk.

### Implementation notes against the current `pssparser` build

Two binding gaps shaped the implementation, and any other implementer will hit them:

- **`ExprRefPathContext.getTarget()` returns a `SymbolRefPath` that Python cannot walk**, so a
  call cannot be resolved to one declaration. Calls are resolved by **simple name**, and a
  diagnostic is emitted only when every function of that name agrees on a platform. This makes
  the multiple-definition caveat below automatic rather than a special case — and it is a
  deliberate false negative, traded for a zero false-positive rate.
- **Procedural statements carry no source location** (only the `ExecBlock` does), so every
  diagnostic anchors to the `exec` keyword and names the offending symbol in the message.

Also note that `CheckContext.file_map` is empty under the current CLI, because `Parser.link()`
clears `_filenames` before checkers run; fileids are mapped to paths positionally instead.

Reference pages: `../reference/lang/procedural/01-exec-blocks.md`,
`../reference/lang/structural/02-components.md`.

---

## PSL001 — solve function called from a target exec

| | |
|---|---|
| **Rule** | A `solve function` shall not be called, directly or transitively, from `exec body`, `exec run_start`, or `exec run_end`. |
| **LRM clause** | §20.2.1.3 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL001",
    severity="error",
    summary="Solve function called from a target exec block",
    detail=(
        "A function declared `solve` is available only during generation "
        "(init_down, init_up, pre_solve, post_solve, pre_body). It shall not be "
        "called from a target exec block (body, run_start, run_end) or from any "
        "function reachable from one.\n\n"
        "Either remove the `solve` qualifier if the function is platform-neutral, "
        "or compute the value in `exec post_solve` and store it in a non-rand "
        "attribute the body can read."
    ),
)
```

**Detection**

1. Build the call graph over all function definitions (native definitions, imported functions,
   target-template functions). Instance functions: an edge per possibly-dispatched definition —
   for a call on a static type `T`, every definition in `T` and its subtypes.
2. Compute, for each function, its **effective platform**: `solve`, `target`, or `both`.
   Unqualified with a qualified definition takes the definition's qualifier (§20.2.1.3).
3. For each exec block of kind `body` / `run_start` / `run_end`, walk the statement tree,
   collect direct calls, and take the transitive closure over the call graph.
4. Report when any reached function has effective platform `solve`.

Report at the **call site** where the solve-qualified function first enters the closure, and
include the chain in the detail when the call is transitive — a bare "somewhere below here" is
much less useful.

**False-positive risk**

- **Unqualified functions with several definitions.** If a declaration is unqualified and one
  definition is `solve` while another (in a different component subtype) is `target`, the call
  is legal in a target exec so long as a target definition exists for the dispatched type. Do
  not report unless **every** candidate definition is `solve`.
- **Core-library functions.** `format()` and `print()` are `solve`; `message()`, `error()`,
  `fatal()`, `urandom()` are not. Take the qualifiers from the stdlib source, not from a
  hard-coded list.
- **Calls inside a `compile if` branch that is disabled.** Check only elaborated code.

**Triggering example**

```pss
package p {
    solve function bit[32] alloc(bit[32] s) { return s; }
}
component c {
    import p::*;
    action a {
        rand bit[32] sz;
        bit[32] addr;
        exec body { addr = alloc(sz); }        // PSL001 here
    }
}
component pss_top { c c0; }
```

**Near-miss example** — must **not** report:

```pss
package p {
    solve function bit[32] alloc(bit[32] s) { return s; }
    function       bit[32] compute(bit[32] s) { return s + 1; }
}
component c {
    import p::*;
    action a {
        rand bit[32] sz;
        bit[32] addr;
        exec post_solve { addr = alloc(sz); }   // solve fn, solve exec: legal
        exec body       { addr = compute(sz); } // unqualified: legal on both
    }
}
component pss_top { c c0; }
```

---

## PSL002 — target function called from a solve exec

| | |
|---|---|
| **Rule** | A `target function` shall not be called from `init_down`, `init_up`, `pre_solve`, `post_solve`, or `pre_body`. |
| **LRM clause** | §20.2.1.3 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL002",
    severity="error",
    summary="Target function called from a solve exec block",
    detail=(
        "A function declared `target` is available only in the generated test "
        "(body, run_start, run_end). It shall not be called from a solve-platform "
        "exec block (init_down, init_up, pre_solve, post_solve, pre_body) or from "
        "any function reachable from one.\n\n"
        "Register and memory access functions, message(), and yield are all target "
        "operations."
    ),
)
```

**Detection** — the mirror of PSL001: exec kinds `init_down`, `init_up`, `pre_solve`,
`post_solve`, `pre_body`; report when a reached function's effective platform is `target`.

**False-positive risk**

- Same multiple-definition caveat as PSL001.
- **`pre_body` is a solve exec** despite its name, and this is exactly where people get it
  wrong in the other direction: `executor()`, `addr_value_solve()` and `addr_value_abs()` are
  legal there and must not be reported.
- Core-library register access (`read_val`, `write_val`, `write_masked`, `read8`…`write64`,
  `read_struct`, `write_struct`) is `target`; `add_region`, `add_nonallocatable_region` and
  `set_handle` are `solve`. Again, read the qualifiers from the stdlib.

**Triggering example**

```pss
package p { import target C function void poke(bit[32] a, bit[32] d); }
component c {
    import p::*;
    action a {
        rand bit[32] sz;
        exec post_solve { poke(0, sz); }       // PSL002 here
    }
}
component pss_top { c c0; }
```

**Near-miss example**

```pss
package p { import target C function void poke(bit[32] a, bit[32] d); }
component c {
    import p::*;
    action a {
        rand bit[32] sz;
        exec body { poke(0, sz); }             // legal
    }
}
component pss_top { c c0; }
```

---

## PSL003 — write to a component attribute outside an init exec

| | |
|---|---|
| **Rule** | Component data fields are immutable once the component tree is built. Actions may read them but shall not modify them. Only `init_down` / `init_up` may assign them. Fields declared `mutable` (3.1) are exempt. |
| **LRM clause** | §9.1.4.1 e, §9.1.6 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL003",
    severity="error",
    summary="Assignment to a component attribute outside an init exec",
    detail=(
        "Component data is configuration: it is assigned while the component tree "
        "elaborates and read thereafter. Assignments are permitted only in "
        "`exec init_down` and `exec init_up`.\n\n"
        "Move the assignment into an init exec, or -- if the value genuinely must "
        "change during solving -- declare the field `mutable` (PSS 3.1, 9.1.6). "
        "Note that a `mutable` field still may not be written from a target exec."
    ),
)
```

**Detection**

For every assignment statement (including compound assignments and `output`/`inout` arguments
to imported functions), resolve the left-hand reference path to its declaration.

Report when **all** of these hold:

- the declaration is a **data field of a component type** (not an action, struct, or object
  field, and not a local);
- the field is **not** declared `mutable`;
- the enclosing exec is **not** `init_down` or `init_up` — including when the assignment is
  inside a function called from such an exec, which requires the same closure walk as PSL001.

Additionally report, at **error** severity, any write to a `mutable` field from a **target**
exec (`body`, `run_start`, `run_end`) — §9.1.6 forbids it directly or indirectly.

**False-positive risk**

- **`comp.f()` calling an instance function that writes a field.** That is still a violation if
  reached from a non-init exec, and it is the interesting case — but only report when the
  function is *only* reachable from non-init execs, or report at the call site with the chain.
- **Local variables shadowing a component field name.** Resolve the path properly; do not
  string-match.
- **A struct-typed component field mutated through a native function parameter.** Aggregates
  pass by handle (§20.3.2), so `f(comp.cfg)` where `f` assigns into its parameter *is* a write.
  Detecting this requires propagating through non-`const` aggregate parameters. Implement the
  direct-assignment case first and treat the parameter case as a follow-on.
- **`mutable` fields.** Exempt outside target execs. Check the qualifier, and remember it
  **propagates into aggregates** — a `mutable` struct field makes all its fields mutable.

**Triggering example**

```pss
component c {
    bit[32] base_addr;
    action a {
        exec post_solve { comp.base_addr = 0x2000; }    // PSL003 here
    }
}
component pss_top { c c0; }
```

**Near-miss example**

```pss
component c {
    bit[32]     base_addr;
    mutable int total;
    action a {
        exec post_solve { comp.total = comp.total + 1; }   // mutable: legal
    }
}
component pss_top {
    c c0;
    exec init_up { c0.base_addr = 0x2000; }               // init exec: legal
}
```

---

## PSL004 — handle-type field accessed in `pre_solve`

| | |
|---|---|
| **Rule** | Statements in `pre_solve` cannot access handle-type fields (`input`/`output`, `lock`/`share`, action handles) or their children, since these are null prior to the completion of randomization. |
| **LRM clause** | §13.4.12 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL004",
    severity="error",
    summary="Handle-type field accessed in pre_solve",
    detail=(
        "input/output fields, lock/share claim fields, and action handles are null "
        "until randomization completes, so they cannot be read or written in "
        "`exec pre_solve`.\n\n"
        "Move the access to `exec post_solve`, where the solver has resolved the "
        "referenced objects. Plain-data rand fields MAY be read in pre_solve, but "
        "they hold their initial values and anything written to them is overwritten "
        "by the solve."
    ),
)
```

**Detection**

Within each `pre_solve` exec (and functions reachable only from `pre_solve` execs), resolve
every reference path root. Report when the root declaration is a flow-object reference field, a
resource claim field, or an action-handle field of the enclosing type.

**False-positive risk**

- **Plain-data `rand` fields are legal to read** in `pre_solve` — do not report those.
- **`comp`** is a reference field but is assigned by the solver's component-assignment step;
  reading `comp` in `pre_solve` is a separate question. Leave `comp` out of this rule rather
  than guess.
- A function shared between `pre_solve` and `post_solve` must not be reported for the
  `post_solve` path. Report at the **call site** in that case, not in the function body.

**Triggering example**

```pss
package p { buffer b_s { rand bit[16] size; } }
component c {
    import p::*;
    pool b_s bp; bind bp *;
    action a {
        input b_s i;
        bit[16] n;
        exec pre_solve { n = i.size; }        // PSL004 here
    }
}
component pss_top { c c0; }
```

**Near-miss example**

```pss
package p { buffer b_s { rand bit[16] size; } }
component c {
    import p::*;
    pool b_s bp; bind bp *;
    action a {
        input b_s i;
        rand bit[16] r;
        bit[16] n;
        exec pre_solve  { n = 0; }            // plain data: legal
        exec post_solve { n = i.size + r; }   // after the solve: legal
    }
}
component pss_top { c c0; }
```
