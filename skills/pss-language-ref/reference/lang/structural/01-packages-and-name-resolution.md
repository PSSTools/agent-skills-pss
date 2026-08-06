# Packages, imports, and name resolution

*Domain: structural. LRM Clause 18.*

Packages group type declarations and type extensions, and give them a namespace. They are also
where you put extensions that must be able to *contradict* each other — a package is the unit a
tool can include or exclude from a given test.

## When you are writing this

- You are starting a new file and need somewhere to put a type.
- A name won't resolve, or resolves to the wrong thing.
- The user asked for variants that must not be active at the same time.
- You need to extend a type from somewhere else.

## Decide

| You want… | Use |
|---|---|
| a namespace for types, functions, constants | `package p { ... }` |
| variants that must not coexist in one test | one package per variant, containing the extensions |
| to use a name from another package, once | qualified: `my_lib::public_s x;` |
| to use several names from a package | `import my_lib::*;` (wildcard) |
| to use exactly one name, unambiguously | `import my_lib::public_s;` (explicit) |
| to shorten a deeply nested namespace | package alias: `package p1 = a::b::c;` |
| to see a package's **type extensions** | **wildcard import** — extensions are unnamed and cannot be explicitly imported |
| something instantiable, with data and actions | `component`, not a package |

**Package vs component as a namespace**: identical for name-resolution purposes. The difference
is that packages cannot be instantiated and cannot contain attributes, sub-component instances,
or *concrete* action definitions. (Abstract actions are fine.)

## Canonical form

```pss
package dma_types_pkg {
    struct desc_s { rand bit[32] addr; rand bit[16] len; }
    enum   mode_e { IDLE, ACTIVE }
    const  int MAX_LEN = 4096;              // `static` is optional; it is static regardless
    abstract action base_xfer { rand bit[16] len; }
}

package dma_pkg {
    import dma_types_pkg::*;                // wildcard: also brings in extensions

    component dma_c {
        import dma_types_pkg::*;            // components may import too
        action xfer : base_xfer {
            constraint len <= MAX_LEN;
        }
    }
}

// a variant, kept separate so it can be included per-test
package dma_lowpower_pkg {
    import dma_pkg::*;
    extend action dma_c::xfer { constraint len <= 64; }
}
```

## Rules

- **Multiple `package` statements may share a name**; the package is the union of all of them,
  including the type extensions declared in each (§18.1.1a).
- Declarations outside any package belong to the **unnamed global package**, visible everywhere
  with no import (§18.1).
- In a `const` field declaration, `static` is optional — the field is a static constant either
  way (§18.1.1b).
- Packages may nest, either lexically or via a `::`-qualified `package a::b { }` declaration.
- **Three ways to reference a package member**: qualified (`p::x`), explicit import, wildcard
  import (§18.1.3).
- An `import` is a **name-resolution directive**. It introduces no declaration and no alias into
  the importing namespace.
- It is **illegal** to explicitly import an identifier that is already declared in the importing
  namespace, or to explicitly import the same identifier from two different packages.
- Precedence, highest first:
  1. a local declaration,
  2. an explicit import,
  3. a wildcard import.
- **If the same name is wildcard-imported from two packages, neither is imported** — you must
  qualify. No error is required at the import; you find out at the reference (§18.1.3).
- `import` may appear only in the **global scope of a source file** or in a **package
  declaration** — and, per the component grammar, in a component body.
- Package aliases are visible only in the lexical scope where they appear. They are not members:
  `consumer_pkg::p1` is not a thing, and wildcard-importing `consumer_pkg` does not export them
  (§18.1.4).
- Type extensions are **unnamed** — they can only be brought in by a wildcard import of the
  package that declares them.

### Declaration and reference ordering (§18.2)

Most elements may be referenced before their declaration in the same source unit. The
exceptions:

- a variable in a **procedural or activity block** may only be referenced after its declaration;
- a constant or enum item may be referenced in another constant's **initializer** only after its
  declaration;
- a constant inside a type may reference type-level and package-level constants; a
  **package-level constant may only reference other package-level constants**.

### Name resolution order (§18.3)

Unqualified names resolve in this order, stopping at the first hit:

1. **Enum context** — if the expected type is an enumeration, its items (from the initial
   definition, then from visible extensions).
2. **Enclosing type** — members of the type's initial definition, then its visible extensions,
   then its supertypes (recursively), then explicit imports of that scope, then wildcard
   imports of that scope; then repeat all of that for the *outer* type if this is an inner type
   (e.g. an action inside a component).
3. **Package namespaces**, from the immediate lexical scope outward: members of all
   `package` statements of that package, then package aliases, then explicit imports, then
   wildcard imports.

A **qualified** name resolves its first element by that same process, then walks down.

The practical consequence: **the current type scope beats imports, and imports beat outer
packages.** If you need to override that, qualify.

## Gotchas

**Wildcard-importing two packages that both declare the name.**
```pss
import a::*;   // declares  cfg_s
import b::*;   // also declares cfg_s
cfg_s x;       // WRONG: neither is imported
a::cfg_s x;    // RIGHT
```
*Tier 1* — reported as an unknown identifier, which points you at the wrong problem. The name
exists; it is ambiguous.

**Explicit-importing a name that already exists locally.** Illegal (§18.1.3), and easy to hit
when a package grows a type that a component already declared.
*Tier 1–2.*

**Expecting an explicit import to bring in extensions.** It cannot — extensions are unnamed.
Symptom: fields added by an extension are "unknown" even though you imported the type.
```pss
import p::my_action;   // the type, but not p's extensions of it
import p::*;           // the type AND p's extensions
```
*Tier 1*, and the message names the *field*, not the import.

**A local name silently shadowing an imported one.** Precedence gives the local declaration the
win with no diagnostic. If a reference is resolving to something unexpected, walk §18.3's order.
*Tier 4.*

**Forward-referencing a constant in an initializer.**
```pss
const int A = B + 1;   // WRONG: B declared later
const int B = 4;
```
*Tier 1–2.* The general "declare anywhere" rule does not extend to constant initializers.

**Putting a concrete action in a package.** Only `abstract` actions may live outside a
component (§9.2.3.3).
*Tier 2.*

**Assuming a package alias is exported.** It is lexically scoped and invisible elsewhere.
*Tier 1.*

## See also

- `07-inheritance-extension-overrides.md` — what `extend` does and why packages contain it.
- `02-components.md` — components as namespaces (`pkg::comp::nested`).
- `09-conditional-code.md` — `compile if`, the other way to make code conditional.
- `../../playbooks/09-organize-and-extend-a-model.md` — task-first.
- `pss-coding-guidelines` (separate skill) — where files go in this repository.
