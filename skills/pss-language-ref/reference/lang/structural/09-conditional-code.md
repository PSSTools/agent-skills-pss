# Conditional code processing: `compile if`, `compile has`, `compile assert`

*Domain: structural. LRM Clause 19.*

Elaboration-time conditionals. `compile if` decides what gets *elaborated at all* — before
types are fully known, before anything is solved. It is not a runtime `if`, and it is not a
C preprocessor.

## When you are writing this

- The user described a build-time configuration: "only if the DMA is present", "for protocol
  version 1.2".
- The model must support several DUT configurations from one source tree.
- You want to fail the build early when a configuration is nonsense — `compile assert`.
- Some source may or may not be present, and you must not reference it when it isn't —
  `compile has`.

## Decide

| The variation is decided… | Use |
|---|---|
| at build time, and code should not exist otherwise | `compile if` |
| at build time, and it is only about *values* | `static const` + a normal constraint |
| by which packages a test includes | separate packages + `extend` (usually better) |
| at solve time, per scenario | a `rand` field and an activity `if`/`select` |
| at test runtime | a procedural `if` in an `exec` |

**Prefer package selection over `compile if`.** `extend` in a package that the tool includes or
excludes achieves most configuration without conditionals, and keeps every branch semantically
checked. Reach for `compile if` when the *declarations themselves* must differ — different
field sets, types that only exist in some configurations.

## Canonical form

```pss
package config_pkg {
    static const bool HAS_DMA          = true;
    static const bool PROTOCOL_VER_1_2 = false;
}

package dma_pkg {
    import config_pkg::*;

    compile if (HAS_DMA) {
        component dma_c {
            action xfer { }
        }
    }

    // guard a reference to something that may not have been declared
    compile if (compile has (config_pkg::PROTOCOL_VER_1_2)) {
        compile if (config_pkg::PROTOCOL_VER_1_2) {
            action new_flow { }
        } else {
            action old_flow { }
        }
    }

    compile assert (HAS_DMA, "this package requires HAS_DMA");
}
```

## Rules

- **Processing is strictly top-to-bottom within a source unit** (§19.1.2). Steps: syntactic
  analysis; evaluation of compile-time expressions (`static const` initializers, then
  `compile if` conditions); then elaboration of globally-visible content and enabled branches.
- A `compile if` condition may reference only types and constants declared **unconditionally, or
  in an already-enabled branch**, either in a previously processed source unit or **earlier in
  this one**.
- **Only package-scope types and constants may be referenced.** Members declared in *type*
  scopes cannot: `compile if (t::A == 2)` is illegal where `t` is a struct and `A` its member
  (§19.1.3b).
- A disabled branch must be **syntactically correct but need not be semantically correct**
  (§19.1.1). This is the whole point — a branch may reference things that do not exist in that
  configuration.
- **A `compile if` block introduces no new scope.** Declarations inside it land in the enclosing
  scope (§19.1.1).
- `compile if` may appear in: global/package scope, action, component, struct, procedural scopes
  (execs and functions) **excluding target-template exec bodies**, constraints, covergroups, and
  overrides (§19.2.1).
- `compile has (static_ref_path)` tests whether that declaration is **visible at this point in
  the evaluation** (§19.3). Combine with `compile if` to guard optional configuration.
- `compile assert (constant_expression [, "message"]);` fails elaboration when the expression is
  not true, reporting the message (§19.4). Use it to validate template parameters and
  configuration constants.

## Gotchas

**Referencing a constant declared later in the same file.**
```pss
compile if (HAS_DMA) { ... }              // WRONG if HAS_DMA is declared below
static const bool HAS_DMA = true;
```
*Tier 1–2* — and the failure mode is often *silent*: the condition may evaluate as if the name
were absent rather than erroring. Declare configuration constants in their own package,
imported first.

**Referencing a member of a type.**
```pss
compile if (my_struct_s::WIDTH == 32) { ... }   // WRONG: inner member of a type
```
*Tier 1–2.* Hoist the constant to package scope.

**Expecting a new scope.**
```pss
compile if (A) { static const int X = 1; }
compile if (!A){ static const int X = 2; }      // fine — only one is elaborated
compile if (A) { static const int Y = 1; static const int Y = 2; }  // WRONG: same scope
```
*Tier 1.*

**Using `compile if` where a constraint belongs.** If the difference is only in *values*, a
`static const` referenced by an ordinary constraint keeps both configurations semantically
checked. `compile if` makes the disabled branch unchecked.
*Tier 4.*

**Assuming a disabled branch is validated.** It is checked for syntax only. A disabled branch
can contain type errors, dangling references, and rule violations indefinitely — they surface
the day someone flips the flag.
*Tier 4* — this is the strongest argument for package selection over `compile if`.

**`compile if` inside a target-template exec body.** Not permitted (§19.2.1 footnote). Put the
conditional around the whole `exec`, or use a procedural `if` inside a native exec.
*Tier 1–2.*

**Relying on cross-source-unit ordering.** The rules are defined per source unit and by
*previously processed* units; the standard does not define how a tool orders them. Keep
`compile if` conditions dependent only on a configuration package that is unambiguously
processed first.
*Tier 4.*

## See also

- `01-packages-and-name-resolution.md` — package selection, the usually-better alternative.
- `07-inheritance-extension-overrides.md` — `extend` for configuration.
- `08-templates.md` — `compile assert` for validating template parameters.
- `../data/02-data-types.md` — `static const` and constant expressions.
