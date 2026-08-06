# Checker rules: registers and data layout

Proposed checker `name = "registers"`. All tier 2. **Implement after `01-`** — register-model
violations are silent and produce wrong bus traffic rather than wrong-looking models.

Reference page: `../reference/lang/platform/04-registers.md`.

---

## PSL021 — conflicting register offset schemes

| | |
|---|---|
| **Rule** | A register group shall implement **either** `get_offset_of_path()` **or both** of `get_offset_of_instance()` and `get_offset_of_instance_array()`. Implementing all three is an error. |
| **LRM clause** | §21.14.2 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL021",
    severity="error",
    summary="Register group implements conflicting offset schemes",
    detail=(
        "A reg_group_c subtype supplies element offsets through exactly one of two "
        "schemes: get_offset_of_path(), or the pair get_offset_of_instance() and "
        "get_offset_of_instance_array(). Implementing all three is an error, "
        "because the address of an element would be ambiguous.\n\n"
        "Delete whichever scheme is not in use. The same one-of-two rule applies "
        "to the get_mnemonic_* functions (21.14.6)."
    ),
)
```

**Detection**

For each component type derived, directly or indirectly, from `reg_group_c`: collect which of
the three functions the type **defines** (a body, native or foreign-bound — not merely
inherits). Report when all three are defined.

Apply the identical check to `get_mnemonic_of_path` / `get_mnemonic_of_instance` /
`get_mnemonic_of_instance_array` (§21.14.6.1a), which holds **regardless of which access mode
is active** (§21.14.6.5).

**False-positive risk**

- **Inherited declarations.** `reg_group_c` *declares* all three; only a definition counts.
- **A definition in an `extend` block.** `reg_group_c` itself shall not be extended (§21.14.2),
  but a user subtype may be — count definitions across the initial definition and all
  extensions.
- **Offset and mnemonic sets are independent.** A group may implement both sets simultaneously;
  do not report that.

**Triggering example**

```pss
package p {
    import addr_reg_pkg::*;
    struct r_s : packed_s<> { bit[32] v; }
    pure component r_c : reg_c<r_s> {}
    pure component g_c : reg_group_c {                 // PSL021 here
        r_c r0;
        function bit[64] get_offset_of_instance(string name) { return 0; }
        function bit[64] get_offset_of_instance_array(string name, int i) { return 0; }
        function bit[64] get_offset_of_path(list<node_s> path) { return 0; }
    }
}
component pss_top { }
```

**Near-miss example**

```pss
package p {
    import addr_reg_pkg::*;
    struct r_s : packed_s<> { bit[32] v; }
    pure component r_c : reg_c<r_s> {}
    pure component g_c : reg_group_c {                 // legal: one scheme
        r_c r0;
        function bit[64] get_offset_of_instance(string name) { return 0; }
        function bit[64] get_offset_of_instance_array(string name, int i) { return 0; }
    }
}
component pss_top { }
```

---

## PSL022 — type extension adds fields to a packed struct

| | |
|---|---|
| **Rule** | Type extensions of a packed struct shall not add new fields. |
| **LRM clause** | §21.13.1 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL022",
    severity="error",
    summary="Extension adds a field to a packed struct",
    detail=(
        "A struct derived from packed_s has a fixed memory layout that existing "
        "code depends on. Adding a field in an extension would silently change "
        "that layout -- and, for a register value type, the register's width.\n\n"
        "Declare a new packed struct type instead, or add the field to the initial "
        "definition."
    ),
)
```

**Detection**

For each `extend struct T { ... }` where `T` derives directly or indirectly from `packed_s<...>`:
report if the extension body declares any **data field**. Constraints, covergroups, execs and
nested types are not fields and are not reported.

**False-positive risk**

- **A flow or resource object deriving from `packed_s` is not a packed struct** (§17.1). Its
  extensions are not covered by this rule — check the *struct kind* as well as the base type.
- `static const` members are not layout-bearing fields; whether to report them is a judgement
  call. Recommendation: do not report.

**Triggering example**

```pss
package p {
    import addr_reg_pkg::*;
    struct s : packed_s<> { bit[8] a; }
}
package q {
    extend struct p::s { bit[8] b; }        // PSL022 here
}
component pss_top { }
```

**Near-miss example**

```pss
package p {
    import addr_reg_pkg::*;
    struct s : packed_s<> { bit[8] a; }
}
package q {
    extend struct p::s { constraint a != 0; }   // constraint only: legal
}
component pss_top { }
```

---

## PSL023 — extension of `reg_c` or `reg_group_c`

| | |
|---|---|
| **Rule** | It shall be illegal to extend the `reg_c` component and its base components. `reg_group_c` shall not be extended. |
| **LRM clause** | §21.14.1, §21.14.2 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL023",
    severity="error",
    summary="Extension of a core-library register component",
    detail=(
        "reg_c, reg_sized_c, reg_base_c and reg_group_c are core-library pure "
        "components whose behaviour the tool implements. They shall not be "
        "extended.\n\n"
        "Derive a user register or register-group type from them instead, and put "
        "the additions there."
    ),
)
```

**Detection**

Report any `extend component T` where `T` resolves to `addr_reg_pkg::reg_c`, `reg_sized_c`,
`reg_base_c`, or `reg_group_c` — including through a template instantiation
(`extend component reg_c<my_s>`).

**False-positive risk**

- Extending a **user subtype** (`extend component my_reg_c { ... }`) is legal; resolve the
  target type before reporting.
- `extend component executor_base_c { ... }` is a **different** and explicitly supported idiom
  (§21.13.9.5) — do not generalize this rule to all core-library components.

---

## PSL024 — `set_handle()` on a nested register group

| | |
|---|---|
| **Rule** | Only the top-level register group is associated with an address region, via `set_handle()`, from `init_down`/`init_up`. Calling `set_handle()` on a nested group is an error. |
| **LRM clause** | §21.14.3 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL024",
    severity="error",
    summary="set_handle() called on a nested register group",
    detail=(
        "A register group's base address comes from the top-level group's handle "
        "plus the offsets returned by the get_offset_* functions along the path. "
        "Only the top-level group -- the one instantiated directly in a non-"
        "register-group component -- may be given a handle.\n\n"
        "set_handle() and set_mnemonic() may also only be called from exec "
        "init_down or exec init_up."
    ),
)
```

**Detection**

For each call to `set_handle()` (and `set_mnemonic()`), resolve the receiver's instance path.
Report when:

- the receiving instance's **containing component** is itself derived from `reg_group_c`
  (i.e. the group is nested); **or**
- the enclosing exec is not `init_down` / `init_up`.

**False-positive risk**

- A group instantiated in a plain component but *reached* through a longer path
  (`comp.sub.regs.set_handle(h)`) is still top-level if `sub` is not a register group. Test the
  containing **type**, not the path length.
- Reference-typed receivers (`ref reg_group_c g; g.set_handle(h);`) may not be resolvable
  statically — skip rather than guess.

**Triggering example**

```pss
package p {
    import addr_reg_pkg::*;
    struct r_s : packed_s<> { bit[32] v; }
    pure component r_c   : reg_c<r_s> {}
    pure component sub_c : reg_group_c {
        r_c r0;
        function bit[64] get_offset_of_instance(string n) { return 0; }
        function bit[64] get_offset_of_instance_array(string n, int i) { return 0; }
    }
    pure component top_c : reg_group_c {
        sub_c s;
        function bit[64] get_offset_of_instance(string n) { return 0; }
        function bit[64] get_offset_of_instance_array(string n, int i) { return 0; }
    }
}
component c {
    import addr_reg_pkg::*;
    p::top_c regs;
    transparent_addr_space_c<> mem;
    exec init_up {
        transparent_addr_region_s<> rg;
        addr_handle_t h;
        rg.size = 1024; rg.addr = 0xA000_0000;
        h = mem.add_nonallocatable_region(rg);
        regs.s.set_handle(h);            // PSL024: nested group
    }
}
component pss_top { c c0; }
```

**Near-miss example** — as above, but `regs.set_handle(h);`.

---

## PSL025 — access mode violation

| | |
|---|---|
| **Rule** | Calling a read on a `WRITEONLY` register, or a write or read-modify-write on a `READONLY` register, is an error. |
| **LRM clause** | §21.14.1 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL025",
    severity="error",
    summary="Register access conflicts with its declared access mode",
    detail=(
        "The register's reg_access parameter constrains which access functions may "
        "be called on it:\n"
        "  READONLY  -- read(), read_val() only\n"
        "  WRITEONLY -- write(), write_val() only\n"
        "  READWRITE -- all of them\n\n"
        "Note that write_masked, write_val_masked, write_field and write_fields are "
        "read-modify-write, so they are illegal on BOTH a READONLY and a WRITEONLY "
        "register."
    ),
)
```

**Detection**

For each call whose receiver resolves to a `reg_c<R, ACC, SZ>` instantiation, classify the
callee:

| Function | Reads | Writes |
|---|---|---|
| `read`, `read_val` | ✓ | |
| `write`, `write_val` | | ✓ |
| `write_masked`, `write_val_masked`, `write_field`, `write_fields` | ✓ | ✓ |

Report when a read is performed on `WRITEONLY`, or a write is performed on `READONLY`.

**False-positive risk**

- `ACC` defaults to `READWRITE` when omitted — do not report defaults as violations.
- A register reached through a `ref reg_sized_c<SZ>` has lost its access mode statically. Skip
  those; do not infer.
- `get_handle()` is neither a read nor a write.

**Triggering example**

```pss
package p {
    import addr_reg_pkg::*;
    pure component sts_c : reg_c<bit[32], READONLY> {}
    pure component g_c : reg_group_c {
        sts_c sts;
        function bit[64] get_offset_of_instance(string n) { return 0; }
        function bit[64] get_offset_of_instance_array(string n, int i) { return 0; }
    }
}
component c {
    p::g_c regs;
    action a { exec body { comp.regs.sts.write_val(0); } }   // PSL025 here
}
component pss_top { c c0; }
```

**Near-miss example** — as above, but `comp.regs.sts.read_val();`.

---

## PSL026 — non-packable field in a packed struct

| | |
|---|---|
| **Rule** | A packed struct may contain only numeric types, `bool`, enumerated types **that have a base type**, packed struct types, and arrays of those. A field of type `addr_handle_t` shall be declared with `sized_addr_handle_s`, not directly. |
| **LRM clause** | §21.13.1, §21.13.3.1 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL026",
    severity="error",
    summary="Non-packable field type in a packed struct",
    detail=(
        "A packed struct has an exact bit layout, so every field must have a known "
        "width. Permitted: numeric types, bool, enums WITH a base type, packed "
        "structs, and arrays of those.\n\n"
        "An enum without a base type has no defined width -- add one, e.g. "
        "`enum m_e : bit[2] { A, B }`. An address field must use "
        "sized_addr_handle_s<SZ>, which supplies the width, rather than "
        "addr_handle_t directly."
    ),
)
```

**Detection**

For each struct deriving from `packed_s<...>`, walk its declared fields (initial definition plus
extensions). Report a field whose type is: `string`, `chandle`, `addr_handle_t`, a `list`/`map`/
`set`, a non-packed struct, a reference type, or an enum with **no** base type. Recurse into
packed struct fields and array element types.

**False-positive risk**

- `float32`/`float64` are numeric; the storage types `float32_s`/`float64_s` are themselves
  packed structs. Both are fine.
- `sized_addr_handle_s<...>` **is** a packed struct wrapping a `chandle` — exempt it explicitly
  rather than reporting on its inner field.
- Flow/resource objects deriving from `packed_s` are not packed structs (§17.1) and are outside
  this rule.
