# Registers and data layout

*Domain: platform. LRM §21.13.1 (packing), §21.14 (registers). All types from `addr_reg_pkg`.*

## When you are writing this

- The user described register programming: "write the control register", "set the mode field".
- The user gave you a register map, an IP-XACT file, or a datasheet table.
- You need a struct with an exact memory layout.
- You are writing `exec body` code that touches MMIO.

## Decide

| You need… | Use |
|---|---|
| a struct with an exact bit layout | `struct s : packed_s<LITTLE_ENDIAN> { … }` |
| the size of a layout | `sizeof_s<T>::nbytes` / `::nbits` |
| one register | `reg_c<value_type [, access [, SZ]]>` |
| a register map | `pure component g : reg_group_c { … }` + one offset scheme |
| to write the whole register | `write(r)` / `write_val(v)` |
| to change some fields, leaving others | `write_masked` / `write_val_masked` / `write_field(s)` |
| generic code over same-width registers | `ref reg_sized_c<32>` |
| the register's address handle | `get_handle()` on `reg_base_c` |
| generated code to use symbolic names, not addresses | `get_mnemonic_*` + `use_symbolic_reg_names()` **3.1** |
| raw memory, not registers | `03-address-spaces.md` |

**Struct-typed vs bit-vector registers.** A `packed_s` value type gives you named fields,
`write_masked({.en=~0},{.en=1})`, and `write_field("en",1)`. A `bit[N]` value type gives you
numbers only — `read()`/`read_val()` and `write()`/`write_val()` become equivalent. Prefer the
struct form unless the register genuinely has no fields.

## Canonical form

```pss
package my_ip_regs_pkg {
    import addr_reg_pkg::*;

    struct CR : packed_s<> {          // LITTLE_ENDIAN default
        bit     en;
        bit[11] pad;
        bit[4]  mode;
        bit[16] coeff;
    }

    pure component cr_r  : reg_c<CR> {}                       // READWRITE, SZ = 32
    pure component sts_r : reg_c<bit[32], READONLY> {}

    pure component ch_regs_c : reg_group_c {
        cr_r  cr;
        sts_r sts;
        cr_r  aux[4];

        function bit[64] get_offset_of_instance(string name) {
            match (name) {
                ["cr"]:  return 0x0;
                ["sts"]: return 0x4;
                default: return -1;
            }
        }
        function bit[64] get_offset_of_instance_array(string name, int index) {
            match (name) {
                ["aux"]: return 0x10 + index*4;
                default: return -1;
            }
        }
    }
}

component dma_c {
    my_ip_regs_pkg::ch_regs_c  regs;          // TOP-LEVEL group
    transparent_addr_space_c<> sys_mem;

    exec init_up {                             // association happens ONCE, here
        transparent_addr_region_s<> mmio;
        addr_handle_t h;
        mmio.size = 1024;
        mmio.addr = 0xA000_0000;
        h = sys_mem.add_nonallocatable_region(mmio);
        regs.set_handle(h);
    }

    action cfg {
        rand bit[4]  mode;
        rand bit[16] coeff;
        exec body {                            // register access is TARGET-side
            comp.regs.cr.write_masked({.mode=~0, .coeff=~0}, {.mode=mode, .coeff=coeff});
            comp.regs.cr.write_field("en", 1);
            bit[32] s = comp.regs.sts.read_val();
        }
    }
}
```

The mask idiom is worth memorizing: `~0` sets every bit of a field, and fields omitted from a
struct literal default to 0 — so they are automatically excluded from the mask.

## Rules

### `packed_s` and packing (§21.13.1)

```pss
enum endianness_e { LITTLE_ENDIAN, BIG_ENDIAN };
struct packed_s <endianness_e e = LITTLE_ENDIAN> {};
```

- Any struct deriving from `packed_s`, directly or indirectly, is packed.
- A packed struct may contain **only** numeric types, `bool`, **enums that have a base type**,
  packed struct types, and arrays of those. `bool` occupies 1 bit; bit fields may be any size.
- **Type extensions of a packed struct shall not add new fields.**
- Layout is de-facto GNU C/C++: **the first-declared field is at the lowest address**, and a
  base packed struct's fields are considered declared **before** the derived struct's.
  - **LITTLE_ENDIAN** — fields packed LSB→MSB in declaration order, memory LSbyte→MSbyte;
    padding at the **MSB** side.
  - **BIG_ENDIAN** — fields packed MSB→LSB, memory MSbyte→LSbyte; padding at the **LSB** side.
- A **flow or resource object deriving from `packed_s` is not a packed struct** (§17.1) and
  cannot be used where one is expected.

### `sizeof_s` (§21.13.2)

```pss
struct sizeof_s<type T> {
    static const int nbytes;   // consecutive byte addresses needed (rounded up)
    static const int nbits;    // exact bit count in a byte-addressable space
};
```

Valid for numeric types, `bool`, based enums, packed structs, and arrays thereof.
`sizeof_s<int>::nbytes == 4`; `sizeof_s<bit[33]>::nbytes == 5`;
`sizeof_s<array<int,10>>::nbytes == 40`.

### Register types (§21.14.1)

```pss
enum reg_access { READWRITE, READONLY, WRITEONLY };

pure component reg_base_c { function addr_handle_t get_handle(); }

pure component reg_sized_c<int SZ> : reg_base_c {
    target function bit[SZ] read_val();
    target function void    write_val(bit[SZ] r);
    target function void    write_val_masked(bit[SZ] mask, bit[SZ] val);
    target function void    write_field(string name, bit[SZ] val);
    target function void    write_fields(list<string> names, list<bit[SZ]> vals);
}

pure component reg_c <type R,
                      reg_access ACC = READWRITE,
                      int SZ = (8*sizeof_s<R>::nbytes)> : reg_sized_c<SZ> {
    target function R    read();
    target function void write(R r);
    target function void write_masked(R mask, R val);
}
```

- `reg_c` and its base components are **`pure component`s** and **shall not be extended**.
- `R` is a **packed struct type** or a **bit-vector type `bit[N]`**.
- `SZ` defaults to the value type's size rounded up to a byte multiple. **If given, it shall be
  ≥ `sizeof_s<R>::nbits`**; the surplus behaves as reserved trailing bits that `read()`/`write()`
  cannot access and whose value in `read_val()`/`write_val()` is unspecified.
- Access functions are **`target`** — call them from `exec body` / `run_start` / `run_end`.
- A `reg_c<…>` instantiation, or a component derived from one, is a **register type** and may
  be instantiated **only inside a register group**.
- With a bit-vector `R`, `read()`≡`read_val()` and `write()`≡`write_val()`.
- `write_masked` / `write_val_masked` are read-modify-write:
  `new = (current & ~mask) | (val & mask)`.
- `write_field` / `write_fields` are read-modify-write **by field name**, and require a
  struct-typed register. Restrictions: **string literals only**; **top-level field names only**
  (no dotted paths); **no aggregate-typed fields**; names passed to `write_fields` must be
  **unique**.
- **Reading or read-modify-writing a `WRITEONLY` register is an error. Writing or
  read-modify-writing a `READONLY` register is an error.**
- `reg_sized_c<SZ>` lets you write code generic over registers of the same width:
  `target function void zero_r32(list<ref reg_sized_c<32>> regs)`.

### Register groups (§21.14.2)

```pss
struct node_s { string name; int index; };

pure component reg_group_c {
    pure function bit[64] get_offset_of_instance(string name);
    pure function bit[64] get_offset_of_instance_array(string name, int index);
    pure function bit[64] get_offset_of_path(list<node_s> path);
    solve function void   set_handle(addr_handle_t addr);
}
```

- `reg_group_c` is a `pure component` and **shall not be extended**.
- A group may contain registers, register arrays, other groups, and arrays of groups. A group
  instance may live in another group, or directly in a non-register-group component — the latter
  is what can be bound to an address region.
- Every element has an offset relative to the group's notional base, supplied by **exactly one
  of two schemes**:
  - `get_offset_of_instance(name)` **and** `get_offset_of_instance_array(name, index)`, or
  - `get_offset_of_path(path)`.
- **Implementing all three is an error.** Whichever you implement must cover every element.
- These functions are **`pure`** — no side effects. They may be native or foreign-bound.
- Different elements **may share the same offset** — the usual `READONLY`/`WRITEONLY` overlay.

### Association with an address region (§21.14.3, §21.14.4)

- Only the **top-level** group is associated with a region, via `set_handle()`, from
  `exec init_down` or `init_up`. **Calling `set_handle()` on a nested group is an error.**
- `get_handle()` on `reg_base_c` returns the address handle for a register.

### Translation of a register access (§21.14.5)

1. The primitive access is chosen by register size — a 32-bit read becomes `read32(handle)`.
2. The total offset is summed from the top-level group down, using `get_offset_of_path()` where
   an intermediate group provides it, otherwise `get_offset_of_instance[_array]()`.
3. The access handle is `make_handle_from_handle(h, offset)`, `h` from `set_handle()`.

### Symbolic register names **3.1** (§21.14.6)

Makes generated code refer to registers by **name** rather than by resolved numeric address —
useful for readability and for aligning with an existing software stack's headers.

```pss
pure component reg_group_c {
    // ... plus:
    solve pure function string get_mnemonic_of_instance(string name);
    solve pure function string get_mnemonic_of_instance_array(string name, int index);
    solve pure function string get_mnemonic_of_path(list<node_s> path);
    solve function void        set_mnemonic(string prefix);
}
package addr_reg_pkg {
    solve function void use_symbolic_reg_names(ref reg_group_c grp, bool enable);
}
```

- Same one-of-two-schemes rule: implement **either `get_mnemonic_of_path()` or both** of the
  instance forms. **All three is an error** — and this holds regardless of which access mode is
  currently active.
- Argument semantics match the corresponding `get_offset_*` function.
- These are **`solve pure`** and shall have no side effects.
- `set_mnemonic(prefix)` may only be called in `exec init_down`/`init_up`, and **only on a
  top-level group** — the same instance `set_handle()` is called on.
- Name construction: start with the prefix (empty if `set_mnemonic()` was not called); descend
  the hierarchy, appending each level's fragment; if a group implements `get_mnemonic_of_path()`
  it is invoked with the remaining path and descent **stops**. **No delimiters are inserted** —
  the fragments must supply their own separators.
- Mode selection: `get_mnemonic_*` and `get_offset_*` are independent and a group may implement
  both. Address-handle mode is the default and applies unless `use_symbolic_reg_names(grp, true)`
  was called.

## Gotchas

**Implementing all three offset functions.** An error, and an easy one to reach by adding
`get_offset_of_path` to a group that already has the instance pair.
*Tier 2* — a strong candidate for a static check.

**`set_handle()` on a nested group.** Only the top-level group is bound.
*Tier 2.*

**Calling a register access from a solve exec.**
```pss
exec post_solve { comp.regs.cr.write_val(0); }   // WRONG: target function
```
*Tier 2.*

**Extending `reg_c` or `reg_group_c`.** Explicitly illegal.
*Tier 2.*

**Adding fields to a `packed_s` by extension.** Illegal — it would silently change every
existing layout.
*Tier 2.*

**An enum without a base type in a packed struct.** Not permitted; its width is undefined.
```pss
enum m_e { A, B }               // no base type
struct s : packed_s<> { m_e m; } // WRONG
enum m_e : bit[2] { A, B }      // RIGHT
```
*Tier 2.*

**Assuming `SZ` bits beyond the value type are readable.** They are reserved; `read()`/`write()`
cannot reach them and their `read_val()` value is **unspecified**.
*Tier 4.*

**Dotted or aggregate field names in `write_field`.**
```pss
write_field("sub.en", 1);       // WRONG: top-level, non-aggregate names only
```
*Tier 2.*

**Non-literal field names.** `write_field(name_var, v)` — string **literals only**.
*Tier 2.*

**Duplicate names in `write_fields`.** Must be unique.
*Tier 2.*

**Reading a `WRITEONLY` register, or `write_masked` on a `READONLY` one.** Both errors — and
`write_field`/`write_masked` count as reads.
*Tier 2.*

**Endianness assumed rather than declared.** `packed_s<>` defaults to LITTLE_ENDIAN. On a
big-endian target that is a silently wrong layout, with padding on the wrong side.
*Tier 4.*

**Registering a group under a `pure component` that also wants an action.** Pure components
cannot declare actions, execs, pools, or non-static data (§9.1.7). Put the group inside a normal
component and the actions there.
*Tier 2.*

**Forgetting that `default: return -1;` is the error case.** An offset function that silently
returns `-1` for a real element produces a wrong address, not a diagnostic. Make sure every
element is covered.
*Tier 4.*

## See also

- `03-address-spaces.md` — regions, handles, and the raw access operations registers compile to.
- `../structural/02-components.md` — `pure component` rules.
- `../structural/08-templates.md` — every type here is a template.
- `../data/02-data-types.md` — what may appear in a packed struct.
- `01-executors.md` — executor-based customization of memory access.
- `../../playbooks/06-access-registers-and-memory.md` — task-first.

### Recommended packaging

Put a device's register and group definitions in their own file and package, so the file can be
generated from a register specification (IP-XACT and friends) without touching the model
(§21.14.7).
