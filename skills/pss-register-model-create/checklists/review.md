# Review checklist — PSS register model

Run this against a register model before calling it done, or when reviewing someone else's. Each item
names the page that explains it.

---

## Source of truth

- [ ] The SystemRDL-vs-hand-written decision was **made explicitly**, with the user, and is recorded
      in the package's header comment. (`00-source-of-truth.md`)
- [ ] If hand-written, one of the four exceptions applies and is named — not "it's only a few
      registers".
- [ ] Provenance header: which document, which revision, which sections, and which RTL file the
      layout was cross-checked against.

## Transcription

- [ ] Field declaration order is **LSB-first** — the spec table read bottom-up.
      (`01-read-the-spec.md`)
- [ ] For every value struct: field widths sum to `SZ`, and the last field's high bit is `SZ - 1`.
- [ ] Interior reserved regions are declared explicitly. (Trailing ones may be implied, but declaring
      them is preferred.)
- [ ] Every field has a comment carrying its bit range and its **spec** access class.
- [ ] Only packable field types: numeric, `bool`, enums *with a base type*, packed structs, arrays of
      those. (PSL026)
- [ ] Arrays are parameterized with a base and stride constant, not enumerated.
- [ ] Build-time counts (`static const`, sizing structure) are distinguished from run-time counts
      (component attributes).

## Facts that PSS cannot hold

- [ ] Every register with a **read** side effect (ROC/RC) is commented as such, and the comment says
      reads are not repeatable. (`02-model-registers.md` §2.4)
- [ ] Every register with a **write** side effect (W1C) or a hardware-modified field is commented as
      such.
- [ ] Every such register carries an explicit "do not use `write_masked` / `write_field` /
      `write_fields` on this register" note — RMW performs a hidden read *and* a hidden write-back.
- [ ] Those caller rules were **handed to the operation model**, not just written in a comment.
      (`04-bind-and-verify.md` §4.3)
- [ ] Every spec contradiction has a recorded resolution **stating both sides**, so a later reader
      does not revert it.

## Declarations

- [ ] Register types are `pure component`, derive from `reg_c<…>`, and have empty bodies.
- [ ] `SZ` is stated explicitly on every register type, even when it equals the struct size.
- [ ] `ACC` matches the register-level access; `READONLY` where reads are the only legal access,
      `WRITEONLY` where writes are. (PSL025 is checked against this.)
- [ ] A bit-vector value type was used only where the register genuinely has no field structure the
      model uses — and the dropped layout facts (e.g. alignment) moved somewhere checkable.
- [ ] No `extend` of `reg_c` or `reg_group_c` themselves. (PSL023)
- [ ] No `extend` adding fields to a packed struct. (PSL022)

## Groups

- [ ] Exactly **one** offset scheme is implemented — `get_offset_of_path()`, or the
      `get_offset_of_instance()` / `get_offset_of_instance_array()` pair. Never all three. (PSL021)
- [ ] Both functions of the instance pair are present, even when the group has no arrays, with a
      comment on the empty one.
- [ ] Offset functions return `-1` from `default`, and are free of side effects.
- [ ] Each instance declaration carries its offset in a comment.
- [ ] The array-vs-per-instance shape decision is recorded with its reason.
      (`03-model-groups.md` §3.3)
- [ ] Address-map constants (base, stride, max count, total span) live in the top-level bank's file.

## Binding

- [ ] `set_handle()` is called only on the **top-level** group, only from `exec init_up` /
      `init_down`. (PSL024)
- [ ] The MMIO region is **non-allocatable**, and its size is the full span, not one bank.
- [ ] `\init` is written with the trailing space at both declaration and call site.

## Verification

- [ ] The model was checked against an artifact **other than** the document it was typed from —
      preferably the RTL register file. (`04-bind-and-verify.md` §4.2)
- [ ] Reset values were used as an independent cross-check on field boundaries.
- [ ] It compiles clean, and passes PSL021–PSL026.
- [ ] A read-back test exists, or its absence is a stated gap. Registers with side effects are
      excluded from it.

## Organization

- [ ] One file per bank, named for the group; value structs and register types live with the bank
      that uses them. (`pss-coding-guidelines` rules 5.1, 5.2)
- [ ] Offset functions are inline in the group, not in a `functions/` directory.
- [ ] Each file opens the package explicitly and carries its own `import std_pkg::*;` and
      `import addr_reg_pkg::*;`.
- [ ] Naming: `_s` value struct, `_r` register type, `_c` group component, `_pkg` package.
- [ ] No forward reference to a type declared in a later file of the same package; the working file
      order is recorded in `src/pss/README.md`.
