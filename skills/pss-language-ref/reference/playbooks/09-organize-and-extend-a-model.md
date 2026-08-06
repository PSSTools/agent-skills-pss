# Playbook: organize and extend a model

*"The same model, but on the other SoC." "Add a field to their action type." "Make this reusable."*

## Choose the mechanism

| The need | Use |
|---|---|
| a namespace, and a unit a tool can include or exclude | `package` |
| add fields/constraints to a type **everywhere it is used** | `extend`, in its own package |
| a new type someone must explicitly choose | inheritance |
| "every A in the model is really a B" | `override { type A with B; }` |
| "this one field is a B" | `override { instance path.f with B; }` |
| a family sharing fields and constraints, never instantiated itself | `abstract action` |
| a type parameterized by a value or a type | template type |
| declarations that only exist in some configurations | `compile if` |

**The default answer for project configuration is `extend` in a package.** It leaves the base
model untouched, it can be included or excluded per test, and — unlike `compile if` — every
branch stays semantically checked.

## Steps — a configurable model

**1. Base model, no project specifics.**

```pss
package dma_pkg {
    component dma_c {
        action xfer { rand bit[16] len; constraint len > 0; }
    }
}
```

**2. One package per configuration, holding only extensions.**

```pss
package soc_a_pkg {
    import dma_pkg::*;
    extend action dma_c::xfer {
        rand int in [1,2,4,8] ta_width;
        constraint ta_width < 4 -> len <= 256;
    }
}
package soc_b_pkg {
    import dma_pkg::*;
    extend action dma_c::xfer { constraint len <= 64; }
}
```

These can contradict each other freely — that is the point of packaging them separately.

**3. Reference extension members with a wildcard import.**

```pss
component pss_top {
    import soc_a_pkg::*;               // required: extensions are unnamed
    dma_pkg::dma_c dma;
    action test {
        dma_pkg::dma_c::xfer x;
        constraint x.ta_width == 4;    // a field introduced in the extension
        activity { x; }
    }
}
```

An **explicit** import cannot bring in extensions.

## Steps — a reusable library type

- Put the shared fields and constraints in an `abstract action` (which may live in a package).
- Derive concrete actions per component.
- Parameterize with a template if several specializations must coexist in one model — and
  prefer a **category** type parameter (`<struct T : base_t>`) over bare `type`.
- Validate parameters with `compile assert`.

## Checks before you call it done

- [ ] Configuration lives in `extend`, not in edits to the base model.
- [ ] Each mutually exclusive configuration is a separate package.
- [ ] Wildcard imports where extension members are referenced.
- [ ] No dependence on extension **order** — no two extensions adding same-kind execs, default
      value constraints, or type overrides to the same type.
- [ ] Derived `exec body` / `activity` uses `super;` where the base behaviour should persist.
- [ ] A same-named constraint in a derived type — did you mean to replace the base's, or add?
- [ ] No `override` on a reference field (`input`/`output`/`lock`/`share`) — it silently does
      nothing.
- [ ] No fields added to a `packed_s` by extension.
- [ ] `compile if` used only where declarations genuinely differ, and its conditions reference
      only package-scope constants declared **earlier**.

## Common failures

| Symptom | Cause |
|---|---|
| "unknown identifier" for a field you added by extension | explicit import instead of wildcard |
| the base implementation stopped running | derived `exec body` without `super;` |
| behaviour differs between tools | reliance on extension ordering |
| an `override` did nothing | applied to a reference field, or a lower directive lost to a higher one |
| a disabled `compile if` branch is full of errors | disabled branches are checked for **syntax only** |
| a constraint disappeared | a same-named constraint in a derived type replaced it |

## Related

File and directory conventions for **this repository** are in the separate
`pss-coding-guidelines` skill. This page is about language mechanisms only.

## See also

- `../lang/structural/07-inheritance-extension-overrides.md` — the rules.
- `../lang/structural/01-packages-and-name-resolution.md` — packages, imports, name resolution.
- `../lang/structural/08-templates.md`, `../lang/structural/09-conditional-code.md`.
- `../../examples/extension_variants.pss`.
