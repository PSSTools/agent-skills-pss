# Template types

*Domain: structural. LRM Clause 10.*

Parameterized types: a struct, flow/resource object, action, monitor, or component whose
definition depends on a value or a type. The core library is built out of them (`reg_c<T>`,
`packed_s<E>`, `contiguous_addr_space_c<T>`), so you will *read* templates long before you
write one.

## When you are writing this

- You are about to copy a type and change one width, one size, or one field type.
- The user described "the same register block, but 32-bit and 64-bit variants".
- You are using a core-library type — every one of them is a template.
- You need a container parameterized by what it contains.

## Decide

| You need to vary… | Parameter kind |
|---|---|
| a size, width, count, or flag | **value** parameter: `<int n_locks = 4>` |
| a type, with no restriction | **generic type** parameter: `<type T>` |
| a type, restricted to a category | **category type** parameter: `<struct T>`, `<action A>`, `<component C>`, `<numeric N>` |
| a type, restricted to a subtree of a base type | category + restriction: `<struct T : base_t>` |

**Prefer a category parameter over `type`.** It documents intent and lets a tool reject bad
instantiations early — a real benefit given that most PSS checking is shallow.

**Do not reach for templates when `extend` will do.** If there is one variant per project, use
`extend` in a package; templates are for when *several specializations coexist in one model*.

## Canonical form

```pss
// value parameter, with a compile-time assertion
action multi_lock <int n_locks = 4> {
    compile assert (n_locks in [1..16]);
    lock my_resource_s res[n_locks];
}

// category type parameter, restricted by inheritance
struct base_t { rand bit[4] core; }
struct wrapper_s <struct T : base_t> {
    rand T payload;
    constraint payload.core != 0;
}

// a parameter whose default depends on an earlier parameter
// (a boolean > or < default must be parenthesized)
abstract action sized_op <int width, bool is_wide = (width > 10)> {
    compile assert (width > 0);
}

// instantiation: positional, angle brackets ALWAYS required
component dma_c {
    wrapper_s<my_sub1_t> w;
    action a4 : multi_lock<>   { }      // all defaults — still needs <>
    action a8 : multi_lock<8>  { }
}
```

## Rules

- A template type is declared by adding `<...>` after the type name. It is **not an actual
  type** — only an explicit instantiation is (§10.1).
- **All instantiations with the same parameter values are the same actual type** (§10.4). This
  is what makes template-instance extension meaningful.
- Parameter values are **positional**. Angle brackets are **always required at instantiation**,
  even when every parameter has a default: `multi_lock<>` (§10.4b).
- Parameters with defaults must come **last**; a defaulted parameter followed by a
  non-defaulted one is an error (§10.3).
- A default may reference **previously declared parameters** (§10.3.1c, §10.3.2b).
- A boolean `>` or `<` expression, as a default or as an argument, must be **parenthesized** to
  avoid ambiguity with the closing bracket (§10.3.1d, §10.4d).
- **Value parameters** may be any scalar type **except `chandle`**, and may be used anywhere a
  constant expression is allowed inside the body and supertype spec (§10.3.1).
- **Type parameters**: `type` is fully generic; a *category* keyword (`action`, `monitor`,
  `component`, or a struct kind) restricts the category; `: base_t` further restricts to types
  related to `base_t` by inheritance (§10.3.2).
- A parameter may be referenced in the template's body, in its **supertype specification**, and
  in all subsequent generic and instance extensions of the template. It **may not** be
  referenced from subtypes that inherit from the template (§10.3).
- Inheritance: a template type may inherit from a template or non-template type; a non-template
  type may inherit from a template *instance*. Normal category rules apply (§10.2).
- Extension (§17.2.6): `extend struct my_s<...>` — extending the **generic** type applies to
  all instances; extending an **instance** applies only to instantiations with that exact
  parameter set. **Partial specialization is not supported.**
- Restrictions (§10.5). A *generic* template type may not be used:
  - as the root component,
  - as the root action,
  - as an **inferred** action completing a partial scenario.

  and template types may **not** be parameter or return types of imported functions.

## Gotchas

**Omitting the angle brackets when all parameters default.**
```pss
multi_lock  a;    // WRONG
multi_lock<> a;   // RIGHT
```
*Tier 1* — and the message is usually about an unknown type, which sends you looking in the
wrong place.

**Unparenthesized boolean default.**
```pss
action a <int w, bool is_wide = w > 10> { }     // WRONG: parse ambiguity at `>`
action a <int w, bool is_wide = (w > 10)> { }   // RIGHT
```
*Tier 1.*

**Defaulted parameter before a non-defaulted one.**
```pss
struct s <int a = 4, int b> { }   // WRONG
```
*Tier 1–2.*

**Referencing a template parameter from a derived type.**
```pss
struct t_s <int W> { bit[W] f; }
struct d_s : t_s<8> { bit[W] g; }   // WRONG: W is not visible here
```
*Tier 1.* Re-parameterize the derived type if it needs the value.

**Expecting a generic template action to be inferred.** Inference only produces actual types
(§10.5). If a partially specified scenario needs a producer and the only candidate is a generic
template, no scenario exists.
*Tier 3* — reported as an inference failure with no hint that templates are involved.

**Expecting partial specialization.** `extend struct wrapper_s<struct T : narrow_t>` is not a
thing. Extend the generic type or a fully-specified instance.
*Tier 1–2.*

**Passing a template type to an imported function.** Not permitted (§10.5). Pass its fields, or
a non-template struct.
*Tier 2.*

**Two instantiations you think are different types.** `wrapper_s<my_sub1_t>` written in two
files is *one* type. Extending it in one place affects both.
*Tier 4* — usually what you want, occasionally a surprise.

## See also

- `07-inheritance-extension-overrides.md` — template type extension, generic vs instance.
- `09-conditional-code.md` — `compile assert`, which is how you validate parameters.
- `../platform/04-registers.md`, `../platform/03-address-spaces.md` — the core library's
  templates, in use.
- `../data/02-data-types.md` — what a value parameter may be.
