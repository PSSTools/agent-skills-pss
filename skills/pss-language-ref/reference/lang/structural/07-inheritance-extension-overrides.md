# Inheritance, extension, overrides, access protection

*Domain: structural. LRM Clause 17 (+ §11.6, §20.1.4).*

Three different mechanisms for "the same thing, but different". Choosing the wrong one is the
main way PSS models become hard to reuse.

## When you are writing this

- The user asked for a variant: "same model, but on the other SoC", "the low-power version".
- You need to add a field or constraint to a type you don't own.
- You have several actions that share fields and constraints.
- The user asked you to configure a generic model for a specific DUT.

## Decide

| You want… | Use | Who chooses |
|---|---|---|
| a new type that is a *kind of* the old one | inheritance (`action b : a {}`) | whoever writes `do b;` |
| to add to a type **everywhere it is already used** | `extend` | nobody — it just happens |
| every `A` in the model to actually be a `B` | `override { type A with B; }` | the containing scope |
| this *one field* to be a `B` | `override { instance path.f with B; }` | the containing scope |
| a shared base with no instances of its own | `abstract action` | — |
| to hide an attribute from the rest of the model | `private` / `protected` | — |

The decision in one line: **inheritance adds a choice; extension removes one.**

- Reusable library type that different projects specialize → inheritance.
- Project-specific configuration of a generic model → `extend`, in a package, so it can be
  included or excluded per test.
- Legacy code you cannot edit that must instantiate your subtype → `override`.

## Canonical form

```pss
// --- inheritance: a new, separately-chosen type -----------------
package base_pkg {
    abstract action base_xfer { rand bit[16] len; constraint len > 0; }
}
component dma_c {
    action xfer     : base_pkg::base_xfer { exec body { ... } }
    action fast_xfer: xfer                { constraint len >= 1024; }   // a *kind of* xfer
}

// --- extension: changes the type everywhere --------------------
package soc_a_pkg {
    extend action dma_c::xfer {
        rand int in [1,2,4,8] ta_width;             // new attribute
        constraint ta_width < 4 -> len <= 256;      // new constraint
    }
}

// --- override: substitute a subtype -----------------------------
component sys_c {
    dma_c dma;
    action test {
        override { type dma_c::xfer with dma_c::fast_xfer; }   // all of them
        activity { do dma_c::xfer; }                           // actually a fast_xfer
    }
}

// --- access protection ------------------------------------------
struct s_s {
    rand int a;              // public by default
    private rand int b;
protected:
    rand int c, d;           // both protected, until the next modifier
public:
    rand int e;
}
```

## Rules

### Inheritance (§17.1)

- The base type must be **the same type category** (action, monitor, component, struct, buffer,
  stream, state, resource).
- **Exception:** a flow or resource object may inherit from a `struct`. It gains the struct's
  members but **is not a struct** — it cannot be passed where a struct is expected, and a flow
  object deriving from `packed_s` is *not* a packed struct.
- A derived type includes all base elements. A same-named field **shadows** the base's; reach
  the base one with `super.<name>`.
- Unnamed elements — activities and procedural exec blocks — invoke the base with the `super;`
  statement.
- `exec` blocks are **virtual**: a derived same-kind exec *replaces* the base's. Use `super;` to
  splice the base in.

```pss
action A  { exec body { message(LOW, "A"); } }
action A1 : A { exec body { super; message(LOW, "A1"); } }   // A then A1
action A2 : A { exec body { message(LOW, "A2"); super; } }   // A2 then A
```

### Extension (§17.2)

- Composite and enumeration types are extensible: `extend action|monitor|component|<struct
  kind>|enum|annotation T { ... }`. The kind named must match the type.
- The full definition of a type is its initial definition **plus all extensions in active
  packages**, woven together.
- Every extension is associated with the **nearest lexically enclosing package** (or the
  unnamed global package).
- **Visibility:** members introduced in an extension are referenceable throughout the package
  that declares the extension. Outside it, only from a scope that **wildcard-imports** that
  package. This applies to static and non-static members alike, qualified or not.
- Field names introduced in an extension must not conflict with the initial definition, and
  must be unique within their type *within that package*. They **may** collide across packages;
  the declaring package's name shadows the others, and referencing a name wildcard-imported
  from two packages is an error.
- **Enum extension**: new items join the domain of every variable of that type. Values are
  assigned as if all items were in the initial definition, in package-processing order. An
  explicitly conflicting value is illegal.
- **Extension order is undefined by the standard.** It is observable only in: invocation order
  of same-kind exec blocks, multiple default-value / default-disable constraints and type
  overrides in the same type, and implicit enum item values. The initial definition always
  comes first. **Write extensions that do not care about order.**
- Extension execs run **after** the initial definition's, in tool-defined order among extensions.
- Template types may be extended generically (all instances) or per-instantiation (same
  parameter values). **Partial specialization is not supported** (§17.2.6).

### Overrides (§17.5)

- `override { type A with B; }` — every field declared `A` in scope becomes `B`.
- `override { instance path.f with B; }` — that one field.
- Resolution: walking from the field upward, the applicable directive is the one **highest** in
  the containment tree; within a container, **instance beats type**; for the same container and
  kind, **later in the code beats earlier**.
- **Overrides do not apply to reference fields** — `input`, `output`, `lock`, `share`.
- Component-type overrides under actions/monitors, and action/monitor-type overrides under
  components, are an **error**.
- `override action` in a component is a different mechanism — see `03-actions.md`.

### Access protection (§17.4)

- Data attributes of components, actions, monitors and structs are **public by default**.
- `public` / `private` / `protected` may prefix a single attribute, or appear as a block
  modifier (`private:`) that changes the default for everything after it.
- `private` — only the declaring element. `protected` — the declaring element, types inheriting
  from it, and their extensions.

## Gotchas

**Using inheritance where the requirement is configuration.**
```pss
// WRONG: now every traversal site must be edited to say soc_a_xfer
action soc_a_xfer : xfer { constraint len <= 256; }
// RIGHT: the existing model is unchanged; include or exclude the package per test
package soc_a_pkg { extend action dma_c::xfer { constraint len <= 256; } }
```
*Tier 4.* Both compile. Only one is reusable.

**Referencing an extension's field without wildcard-importing its package.**
```pss
import soc_a_pkg::xfer_ext;      // there is no such name — extensions are unnamed
import soc_a_pkg::*;             // RIGHT
```
*Tier 1*, and the message names the *field*, not the import.

**Relying on extension order.** Two extensions each adding an `exec body`, or each adding a
default value constraint, produce a tool-dependent result.
*Tier 4* — works on one tool, differs on another.

**Forgetting `super;` in a derived exec.** The base's `exec body` is *replaced*, not appended
to — so the base implementation silently stops running.
*Tier 4.* This is the single most damaging inheritance gotcha in PSS.

**Expecting a flow object derived from a struct to be usable as that struct.** It is not
(§17.1). Notably: `buffer b : packed_s<> {}` is not a packed struct and cannot be passed to
`write_struct`.
*Tier 2.*

**Overriding a reference field.** Silently does nothing — overrides do not apply to
`input`/`output`/`lock`/`share`.
*Tier 4.*

**Extending an `abstract` action and expecting it to become concrete.** It stays abstract
(§9.2.1d).
*Tier 2.*

**Adding fields to a `packed_s` by extension.** Illegal — it would change the memory layout out
from under existing code. See `../platform/04-registers.md`.
*Tier 2.*

**Assuming `private` protects across extensions.** `protected` reaches inheriting types *and
their extensions*; `private` is the declaring element only. Neither is a security boundary —
they exist to keep model layers from entangling.
*Tier 2.*

## See also

- `01-packages-and-name-resolution.md` — where extensions live and how their members become
  visible.
- `03-actions.md` — `abstract` and `override action`.
- `08-templates.md` — extending template types.
- `../procedural/01-exec-blocks.md` — exec inheritance, `super;`, extension ordering.
- `../activity/01-activities.md` — activity inheritance (§11.6).
- `../../playbooks/09-organize-and-extend-a-model.md` — task-first.
