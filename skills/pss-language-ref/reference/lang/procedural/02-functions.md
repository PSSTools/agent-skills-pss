# Functions

*Domain: procedural. LRM §20.2, §20.3.*

## When you are writing this

- You have logic used in more than one exec block.
- You need to compute something during the solve, or during the run, or both.
- You need to call into C/C++/SystemVerilog (see also `04-foreign-interface.md`).
- A function call is being rejected and you need the platform or parameter rules.

## Decide

| You need… | Declare |
|---|---|
| computation usable anywhere | `function T f(...);` — **unqualified** |
| computation only during generation | `solve function T f(...);` |
| an operation only meaningful at runtime | `target function void f(...);` |
| a result the tool may cache | `pure function T f(...);` |
| a component-independent helper | `static function ...` (in a component) or any package function |
| behaviour that varies by component subtype | an **instance** function, overridden per subtype |
| a binding to existing foreign code | `import [target|solve] [C|CPP|SV] function ...` |
| to emit target text rather than call | a target-template function — `04-foreign-interface.md` |

**Default to unqualified.** Qualify only when the function genuinely cannot exist on the other
platform. Over-qualifying is the usual cause of "solve function called from a target exec".

**Instance vs static.** Component functions are instance functions unless declared `static`.
Instance calls are **polymorphic** on the context component; static calls are not.

## Canonical form

```pss
// declarations
function       int  compute(int a, int b);
solve function bit[32] alloc_addr(bit[32] size);
target function void   poke(bit[32] addr, bit[32] data);
pure   function int    factorial(int n);

// native definitions
function int compute(int a, int b) { return a + b; }

component base_c {
    function void do_it();                      // instance function, defined per subtype
    action a {
        exec post_solve { comp.do_it(); }       // valid where a solve definition exists
    }
}
component c1 : base_c { solve  function void do_it() { print("c1\n"); } }
component c2 : base_c { target function void do_it() { message(LOW, "c2"); } }

// parameters
struct params_s { int x; }
function void bump(params_s p, int a) {         // p by handle, a by value
    p.x = a;
    a = 0;                                      // invisible to the caller
}
function void copy_array(const array<int,3> src, array<int,3> dst) {
    foreach (dst[i]) { dst[i] = src[i]; }
}
```

## Rules

### Declaration (§20.2.1)

```
function_decl       ::= [target|solve] [pure] [static] function function_prototype ;
procedural_function ::= [target|solve] [pure] [static] function function_prototype
                        { { procedural_stmt } }
function_prototype  ::= (void | data_type) identifier function_parameter_list_prototype
function_parameter  ::= [ (input|output|inout) | const ] data_type ID [= constant_expression]
                      | [const] ( type | ref type_category | struct ) ID
varargs_parameter   ::= ( data_type | type | ref type_category | struct ) ... ID
type_category       ::= action | component | struct_kind
```

- Declarable in global, package, or component scope.
- **Global and package functions are always static.** Component functions are instance functions
  unless `static`.
- Declaration and definition may be in different scopes. **A model shall contain exactly one
  definition per function** (per derived component type, for instance functions).
- Three definition forms: **native PSS** (§20.3), **imported** (§20.4, static only), and
  **target template** (§20.6, always target, `void` only).

### Shadowing and polymorphism (§20.2.1)

- A **static** component function may be shadowed by a same-named static *or* instance function
  in a derived component, with a **different signature**. **Static calls are not polymorphic.**
- An **instance** function may be shadowed **only by an instance function with an identical
  signature**; calls are **polymorphic** on the context component. `super.name(...)` reaches the
  base version.
- **An instance function may not be shadowed by a static function.**
- **A `pure` function may not become non-`pure`, and a non-`pure` function may not be declared
  `pure` in a derived type.**

Calls: static functions optionally qualified with `pkg::` / `Component::`; instance functions
with `.` on a component instance expression (`comp.f()`, `handle.f()`).

### Platform qualifiers (§20.2.1.3)

- **Unqualified** — available in every phase.
- **`solve`** — `init_down` / `init_up` / `pre_solve` / `post_solve` / `pre_body` only.
- **`target`** — `body` / `run_start` / `run_end` only.
- If a separate declaration is qualified, the definition's qualifier must **match or be
  omitted**. If the declaration is unqualified, the definition's qualifier **narrows** the
  model's availability.
- **A call is valid only if a definition exists for the relevant platform** — and, for an
  instance function, for the relevant component type. Declaring an instance function in a base
  component and defining it only in subtypes is legal, provided no call occurs in a base-type
  context.

### Parameters and return types (§20.2.2)

- Return type must be a data type or `void`. **Only plain-data types or reference types may be
  returned** — action/component/flow-object types are illegal without `ref`. Same for
  parameters.
- **Direction modifiers (`input`/`output`/`inout`) may only be used on imported functions**
  (and built-in core-library declarations). **Native and target-template definitions shall not
  use directions.**

### Native parameter passing (§20.3.2)

| Kind | Semantics |
|---|---|
| **scalar** | **by value** — callee assignments are invisible to the caller |
| **aggregate** (struct, collection) | **by handle** to the caller's instance — **callee assignments mutate the caller**. Passing a derived value as a base parameter exposes only base fields. As variables they still have *value* semantics for `=` and `==` |
| **reference** (`ref …`) | reference assignment — the parameter aliases the entity, may be `null`. Reference semantics for `=` and `==` |

### `const` parameters (§20.2.3)

- **Native functions only.** A `const` parameter cannot be modified in the body.
- **`const` may not be applied to reference types or collections thereof.**
- **`const` is part of the signature** and must appear in redeclarations and overrides.
- **`const` together with a direction modifier is illegal.**
- Consequences:
  - a **`static const` aggregate** may only be passed to a `const` parameter;
  - an **aggregate literal argument is constant** in the call context regardless of its
    elements, so its parameter must be `const`.

### Default parameter values (§20.2.4)

Constant expressions, **plain-data parameters only**. Once a parameter has a default, **all
later parameters must too**. A default is in effect for redeclarations and overrides and
**shall not be repeated there**, even with the same value. **Not allowed on `output`/`inout`
import parameters.**

### Generic and varargs parameters (§20.2.5)

**For built-in / core-library declarations only** — PSS has no native mechanism to operate on
them. A generic parameter uses `type` or a type category (`action`/`component`/`struct_kind`);
with the `struct` category the `ref` modifier is **not** used, for the others it **is**.
**Generic parameters may not have defaults.** `...` marks a varargs parameter, which **must be
last**; all varargs arguments must share the declared type or category.

### `pure` functions (§20.2.6)

- Promise: the return value depends **only** on the parameters, with **no side effects**.
- **Only non-`void` functions with no `output`/`inout` parameters may be `pure`.**
- **The tool may reuse results for repeated arguments**, so a mislabelled `pure` function
  misbehaves **silently**.
- `pure` may be omitted at the definition if the declaration had it.

### Calling (§20.2.7)

- **`void` functions: standalone statements only.**
- Non-`void` functions are expression operands. As a statement, **discard explicitly with
  `(void)f();`** — legal without the cast, recommended with.
- **Recursion is allowed.**

## Gotchas

**Parameter directions on a native function.**
```pss
function void f(output int x) { x = 1; }   // WRONG: imported functions only
```
*Tier 2* — a strong static-check candidate.

**Expecting a scalar parameter to be an out-parameter.** Scalars are by value. Return the value,
or pass a struct (which is by handle).
*Tier 4.*

**Expecting a struct parameter to be a copy.** It is not — the callee mutates the caller's
instance. Mark it `const` if that is wrong.
*Tier 4* — silent action-at-a-distance.

**Aggregate literal against a non-`const` parameter.**
```pss
function void g(array<int,3> a);
g({1,2,3});                        // WRONG: the literal is const
```
*Tier 2.*

**`pure` on a `void` function, or one with `output` parameters.** Illegal.
*Tier 2.*

**Mislabelled `pure`.** The tool may cache the result and never call it again.
*Tier 4* — the worst kind of silent wrongness, and a good reason to be conservative with `pure`.

**Over-qualifying with `solve`/`target`.** A helper marked `solve` cannot be reached from
`exec body`, even though its logic is platform-neutral. Leave computation unqualified.
*Tier 2.*

**Two definitions of one function.** Exactly one per model (per derived component type for
instance functions).
*Tier 1–2.*

**Shadowing an instance function with a different signature.** Only identical signatures shadow;
otherwise you have declared a second, unrelated function.
*Tier 2.*

**Repeating a default value in an override.** Shall not be repeated, even identically.
*Tier 2.*

**Default before a non-defaulted parameter.** All later parameters need defaults too.
*Tier 1–2.*

**Non-`void` call used bare.** Legal, but discard explicitly — `(void)f();` — so the intent is
visible.
*Tier 4.*

## See also

- `01-exec-blocks.md` — where each qualifier is callable.
- `03-procedural-statements.md` — what goes in a native function body.
- `04-foreign-interface.md` — imported, exported, and target-template functions.
- `../data/02-data-types.md` — what may be a parameter or return type.
- `../data/03-collections.md` — aggregates, and what "by handle" means for them.
