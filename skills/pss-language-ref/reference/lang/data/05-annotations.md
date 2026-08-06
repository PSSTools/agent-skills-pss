# Annotations

*Domain: data. LRM §7.13 (declaration and application), §21.6 (standard annotations).* **3.1**

Annotations attach **metadata** to model elements. They are advisory: they have no effect on
the model's meaning, and a tool that does not recognize one **must ignore it**.

## When you are writing this

- You want documentation to survive into generated target code.
- A tool's documentation tells you it consumes a particular annotation.
- The user asked for structured metadata on model elements (ownership, requirement IDs,
  traceability).

## Decide

| You want… | Use |
|---|---|
| a note for the *reader of the PSS* | a `//` comment |
| a note that should appear in generated target code | `@code_doc {.text="…"}` |
| model-level documentation a tool can extract | `@doc {.text="…"}` |
| tool-specific metadata the tool documents | that tool's annotation type |
| your own structured metadata | declare an `annotation` type in a package |
| behaviour to actually change | **not an annotation** — a constraint, a `compile if`, or a field |

The last row is the real decision. Annotations cannot make anything happen. If you find
yourself wanting one to control generation, you want a `static const` and a `compile if`.

## Canonical form

```pss
package my_meta_pkg {
    annotation requirement_s {
        string id;
        string owner = "unassigned";     // initializers must be constant
    }
}

package dma_pkg {
    import my_meta_pkg::*;
    import std_pkg::*;

    component dma_c {
        @doc {.text="Programs the DMA descriptor and starts the transfer"}
        @requirement_s {.id="REQ-DMA-014", .owner="verif"}
        action xfer {
            exec body {
                @code_doc {.text="Kick the channel"}
                write32(comp.regs_h, 1);
            }
        }

        @doc {.text="a standalone annotation, attached to this lexical point"};
    }
}
```

Note the punctuation: an annotation **attached to an element has no semicolon**; a **standalone**
annotation ends with one.

## Rules

- Declaration: `annotation ID [<template params>] [: base] { ... }`, containing
  `[static const] data_declaration` fields, `compile assert`, and `compile if`.
- **Annotation types may only be declared in package scope** (§7.13b).
- Annotation attributes may only be of **plain data types and collections thereof** (§7.13a).
- Annotations are **extensible** like other types (`extend annotation T { ... }`) (§7.13c).
- Application: `@type_id [ { .field = constant_expression, … } ]`.
- **All initializer expressions must be constant** (§7.13a).
- An annotation with no terminating semicolon attaches to **the next model element declared in
  the scope**. It is an **error** if no subsequent element exists.
- A **standalone** annotation — terminated by `;` — attaches to a lexical location.
- **Annotations are advisory.** Tools shall disregard unrecognized annotations, and shall only
  perform semantic checking on annotation types they recognize.
- **An annotation is not a data type.** It cannot be used as a field type, a parameter type, or
  in an expression.

### Standard annotations (§21.6)

Both live in `std_pkg`:

```pss
package std_pkg {
    annotation code_doc { string text; }   // implementation-level; may become a target comment
    annotation doc      { string text; }   // model-level; extracted by tools
}
```

- **`code_doc`** applies to statements and other executable elements. A tool *may* emit the
  text as a comment in generated target code. Interpretation is tool-specific.
- **`doc`** associates model-level documentation with an element, for tools to extract.

## Gotchas

**Dangling element annotation at the end of a scope.**
```pss
action config {
    @doc {.text="Scope annotation"};   // standalone — fine
    @doc {.text="orphan"}              // WRONG: no following element
}
```
*Tier 1–2* — one of the few annotation errors a tool must diagnose.

**Semicolon on an element annotation.** Adding one turns it into a *standalone* annotation, so
it silently stops applying to the element below.
*Tier 4* — both forms are legal; only one does what you meant.

**Non-constant initializer.**
```pss
@requirement_s {.id=comp.name}    // WRONG: must be a constant expression
```
*Tier 2.*

**Expecting an unrecognized annotation to be an error.** Tools must ignore them — so a typo in
an annotation type name may produce nothing at all beyond an unresolved-name error, and a typo
in a *field* name inside a recognized annotation may be checked or not.
*Tier 4.*

**Expecting an annotation to change behaviour.** It cannot. If a tool documents an annotation
that influences generation, that is that tool's extension — note the dependency explicitly.
*Tier 4.*

**Declaring an annotation type inside a component.** Package scope only.
*Tier 1–2.*

## See also

- `02-data-types.md` — what an annotation field may hold.
- `../structural/07-inheritance-extension-overrides.md` — `extend annotation`.
- `../platform/05-core-library-api.md` — `std_pkg` in general.
- `../../3.1-deltas.md` — annotations as a 3.1 addition.
