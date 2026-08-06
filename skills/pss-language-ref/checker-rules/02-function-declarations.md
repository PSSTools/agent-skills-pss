# Checker rules: function declarations and calls

Proposed checker `name = "functions"`. All tier 2, all AST-local.

Reference page: `../reference/lang/procedural/02-functions.md`.

---

## PSL011 — parameter direction on a non-imported function

| | |
|---|---|
| **Rule** | Parameter direction modifiers (`input`, `output`, `inout`) may only be used on imported functions and built-in core-library declarations. Native and target-template definitions shall not use them. |
| **LRM clause** | §20.2.2 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL011",
    severity="error",
    summary="Parameter direction modifier on a non-imported function",
    detail=(
        "input/output/inout describe how values cross the foreign-language "
        "boundary and are legal only on imported functions. A native PSS function "
        "passes scalars by value and aggregates by handle (20.3.2).\n\n"
        "Remove the modifier. To let a native function return more than one value, "
        "pass a struct -- aggregates are passed by handle, so the callee's writes "
        "are visible to the caller. Mark it `const` if it must not be mutated."
    ),
)
```

**Detection**

For each function **definition** (native procedural body, or target-template) and for each
declaration that has no corresponding `import`, inspect the parameter list. Report any
parameter carrying `input`, `output`, or `inout`.

A declaration with a matching `import_function` is exempt; so is anything originating in the
bundled stdlib.

**False-positive risk**

- A **declaration/import pair** where the direction appears on the declaration and the import
  matches it — legal (§20.4.1). Resolve the pairing before reporting.
- **Stdlib declarations**, which legitimately use `output` (e.g. `try_get(output T t)`). Exempt
  files loaded as the core library.

**Triggering example**

```pss
package p {
    function void f(output int x) { x = 1; }        // PSL011 here
}
component pss_top { }
```

**Near-miss example**

```pss
package p {
    function void f(output int x);
    import C function f;                            // imported: legal
    function void g(int x) { }                      // no direction: legal
}
component pss_top { }
```

---

## PSL012 — invalid `pure` declaration

| | |
|---|---|
| **Rule** | Only non-`void` functions with no `output` or `inout` parameters may be declared `pure`. A `pure` function may not become non-`pure`, and a non-`pure` function may not be declared `pure` in a derived type. |
| **LRM clause** | §20.2.6, §20.2.1 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL012",
    severity="error",
    summary="Invalid pure function declaration",
    detail=(
        "`pure` asserts that the return value depends only on the parameters and "
        "that the function has no side effects, which permits the tool to cache "
        "results. It is therefore legal only on non-void functions with no output "
        "or inout parameters.\n\n"
        "Purity is also invariant under inheritance: a derived type may not add or "
        "remove `pure`."
    ),
)
```

**Detection**

Three independent conditions, all local:

1. `pure` on a function whose return type is `void`.
2. `pure` on a function with any `output` or `inout` parameter.
3. For an instance function shadowed in a derived component: the base's `pure` flag differs
   from the derived definition's. (A definition may **omit** `pure` when the declaration had it
   — that is not a difference.)

**False-positive risk**

- **Omitted `pure` at the definition.** Legal when the declaration carried it (§20.2.6).
  Compare against the *declaration*, not the definition text.
- **Static shadowing.** A static function may be shadowed with a *different signature*
  (§20.2.1), so condition 3 applies only to instance functions with identical signatures.

**Triggering example**

```pss
package p {
    pure function void f(int a) { }                 // PSL012: void
    pure function int  g(output int a);             // PSL012: output parameter
}
component pss_top { }
```

**Near-miss example**

```pss
package p {
    pure function int f(int a);
    function      int f(int a) { return a * a; }    // pure omitted at definition: legal
}
component pss_top { }
```

---

## PSL013 — non-`void` call used as a bare statement

| | |
|---|---|
| **Rule** | A `void` function call may be a standalone statement. A non-`void` call used as a statement should discard the result explicitly: `(void)f();` |
| **LRM clause** | §20.2.7 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL013",
    severity="warning",
    summary="Non-void call used as a statement without discarding the result",
    detail=(
        "The call is legal, but discarding the result silently hides whether the "
        "return value was meant to be used. Write `(void)f();` to say so "
        "explicitly.\n\n"
        "This is also a useful signal for a mislabelled `pure` function: a pure "
        "function called only for effect is a contradiction."
    ),
)
```

**Severity note:** this one is `warning`, not `error` — the LRM permits the bare form.

**Detection**

For each expression statement in a procedural scope whose expression is a function call, look
up the callee's return type. Report when it is not `void` and the call is not wrapped in a
`(void)` cast.

**False-positive risk**

- Calls whose callee cannot be resolved (an unresolved import) — skip rather than guess.
- Method calls on collections that return a value which is idiomatically discarded, e.g.
  `l.pop_back();`. Consider exempting the core-library collection mutators, or accept the noise
  and let the rule be disabled per project.

**Triggering example**

```pss
package p { function int f(int a) { return a; } }
component c {
    import p::*;
    action a { exec body { f(1); } }                // PSL013 here
}
component pss_top { c c0; }
```

**Near-miss example**

```pss
package p {
    function int  f(int a) { return a; }
    function void g(int a) { }
}
component c {
    import p::*;
    action a {
        exec body {
            (void)f(1);                             // explicit discard: legal
            g(1);                                   // void: legal
        }
    }
}
component pss_top { c c0; }
```

---

## PSL014 — constant argument passed to a non-`const` parameter

| | |
|---|---|
| **Rule** | An aggregate literal argument is constant in the call context, so its parameter must be `const`. A `static const` aggregate may only be passed to a `const` parameter. |
| **LRM clause** | §20.2.3 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL014",
    severity="error",
    summary="Constant aggregate passed to a non-const parameter",
    detail=(
        "Native functions pass aggregates by handle, so a non-const parameter may "
        "be mutated by the callee. An aggregate literal, and a `static const` "
        "aggregate, are constants in the call context and cannot be bound to such "
        "a parameter.\n\n"
        "Declare the parameter `const`. Note that `const` is part of the signature "
        "and must appear in every redeclaration and override."
    ),
)
```

**Detection**

For each call to a **native** function, for each argument:

- if the argument is an **aggregate literal** (`{...}`), or resolves to a `static const`
  aggregate declaration, and
- the corresponding formal parameter is an aggregate type **without** `const`,

report at the argument.

**False-positive risk**

- **Imported functions** — the by-handle rule and this restriction are native-function
  semantics (§20.3.2). Check the definition form first.
- **Scalar `static const`s** — the rule is about aggregates.
- **A `const` aggregate passed to a `const` parameter** — legal, obviously; make sure the
  parameter's `const` is read from the *declaration* if the definition omits it.

**Triggering example**

```pss
package p {
    static const array<int,3> ARR = {1, 2, 3};
    function void f(array<int,3> a) { }
    function void g() {
        f({1, 2, 3});     // PSL014: aggregate literal
        f(ARR);           // PSL014: static const aggregate
    }
}
component pss_top { }
```

**Near-miss example**

```pss
package p {
    static const array<int,3> ARR = {1, 2, 3};
    function void f(const array<int,3> a) { }
    function void g() {
        f({1, 2, 3});     // legal
        f(ARR);           // legal
    }
}
component pss_top { }
```
