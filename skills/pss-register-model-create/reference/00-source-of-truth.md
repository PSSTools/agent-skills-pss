# 0 — Choosing the source of truth

**Default answer: SystemRDL.** Hand-written PSS registers are the exception, and this page is the
gate you pass through to claim the exception.

---

## Why SystemRDL is the default

A register map is not owned by the PSS model. It is owned by the device, and it has at least four
other consumers:

| Consumer | Artifact |
|---|---|
| RTL | the register file module |
| UVM | the RAL model (`uvm_reg_block`) |
| Firmware | the C header / driver struct |
| Documentation | the register table in the datasheet |
| **PSS** | the `reg_group_c` bank this skill builds |

Every one of those is a *projection* of the same map. Maintaining them independently means a bit
that moves in RTL is corrected in three places and missed in a fourth — and the one it is missed in
produces silently wrong bus traffic, not a compile error. A register-model bug does not look like a
bug; it looks like the DUT misbehaving.

SystemRDL also expresses things PSS cannot, and that a hand-written PSS model therefore *loses*:

- per-field access classes (`rw`, `ro`, `wo`, `w1c`, `rclr`, `woset`, …) — PSS has three values, for
  the whole register
- reset values
- `hw`/`sw` access split, `volatile`, hardware-modified fields
- `regfile`/array replication with strides, and address maps composed of blocks

So the SystemRDL file remains the place those facts live, and the PSS bank becomes a generated
projection that carries what PSS can carry — plus comments carrying what it cannot.

**Before writing any PSS registers, check whether this project has a SystemRDL skill or generator
flow available, and offer it.** If a `systemrdl`-oriented skill is present, that is the path; this
skill exists for when it is not.

---

## When hand-writing is the right answer

Claim the exception only if one of these is true, and say which one:

1. **No machine-readable register description exists and none is planned.** A 2002 OpenCores PDF is
   not a register description you can generate from. Authoring SystemRDL *first* would be defensible,
   but it is a second deliverable — decide that explicitly with the user rather than assuming it.
2. **The register map is frozen and small.** A handful of registers in a block that is not under
   development. The drift risk that justifies the generator is not present.
3. **No RDL toolchain in the project.** Introducing `systemrdl-compiler` plus a PSS exporter is
   larger than the register model itself, and the user has not asked for it.
4. **Prototyping.** You are establishing whether the operation model is right at all, and the
   register bank is scaffolding. Say so, and say what would replace it.

**Not** reasons: "it's only a few registers" on a block still being designed; "generating it is
extra setup"; "I already started typing it".

### What you owe the reader when you hand-write

Because the generator's guarantees are gone, the file has to carry them itself:

- **A provenance header.** Which document, which revision, which section — and which RTL file the
  layout was cross-checked against. The banks in `src/pss/wb_dma_regs_pkg/` open with exactly this,
  citing `docs/dma_doc.md §4.1-4.3` and `src/spl/wb_dma_rf.svh`.
- **A per-field access comment** for every field whose class is not plain RW. This is the only
  surviving record (see SKILL.md, "the one idea").
- **A recorded resolution for every spec contradiction** you had to settle (see
  `01-read-the-spec.md`).
- **A verification step that actually ran** (see `04-bind-and-verify.md`) — the model checked
  against the RTL register decode, not merely against the datasheet it was typed from.

---

## Ask, don't assume

This decision belongs to the user, not to you. If it has not already been made, ask before writing:

> The register map can be modelled two ways: author SystemRDL as the single source of truth and
> generate the PSS bank from it (recommended — the RTL, RAL, C header and PSS then cannot drift), or
> write the PSS registers directly against the datasheet. Direct PSS is reasonable here if <the
> applicable exception>. Which do you want?

Record the answer in the package file's header comment so the next reader does not re-litigate it.
