# 4 — Binding to an address space, and verifying

A register group with no handle is inert: the access functions have nowhere to go. Binding is the
last modelling step, and verification is the one that decides whether any of the preceding work was
correct.

---

## 4.1 Binding

Only the **top-level** group — the one instantiated directly in a non-register-group component — is
given a handle, and only from `exec init_up` or `exec init_down`. Calling `set_handle()` on a nested
group is an error (PSL024); nested offsets compose from the `get_offset_*` functions instead.

```pss
component wb_dma_c {
    wb_dma_regs_c               regs;
    transparent_addr_space_c<>  sys_mem;

    exec init_up {
        transparent_addr_region_s<> mmio;
        addr_handle_t h;
        mmio.addr = WB_DMA_REG_BASE;
        mmio.size = WB_DMA_REG_SPAN;        // from 03-model-groups §3.4

        h = sys_mem.add_nonallocatable_region(mmio);
        regs.set_handle(h);
    }
}
```

Three things to get right:

- **Non-allocatable.** MMIO is not memory the solver may hand out for buffers. Use
  `add_nonallocatable_region()`; an allocatable region will eventually be allocated over your
  register file.
- **The size is the full span**, base through the last instance's last register — not the size of one
  bank.
- **`init_up` vs `init_down`.** Use `init_up` when the component computes its own base;
  `init_down` when a parent hands it down. For a per-instance shape (`03-model-groups` shape B) the
  handle is usually computed in a `solve function \init (…)` called by the parent, using
  `make_handle_from_handle(base, offset)`.

Note the escaped identifier: `\init` is written `\init (…)` with a space before the paren, at both
declaration and call site — `init` collides with the `exec init` keyword, and `\init(` lexes as one
token (`pss-coding-guidelines` rule 9).

### Symbolic names (PSS 3.1)

3.1 adds `get_mnemonic_of_*` on `reg_group_c` and `set_mnemonic()` alongside `set_handle()`, so
generated target code can refer to registers by symbolic name rather than computed address. Same
one-of-two rule as the offset functions (§21.14.6.1), same `init_up`/`init_down` restriction on
`set_mnemonic()`. Add these only if the target flow consumes them; see
`pss-language-ref` → `reference/lang/platform/04-registers.md` §21.14.6.

---

## 4.2 Verification

A hand-written register model that has only been read back against the document it was typed from
has not been verified — you will re-make the same transcription error twice. Verify against a
**different** artifact.

In priority order:

**1. The RTL register file.** The decode and field assignments are what the DUT does. Check:
   - each register's offset against the address decode
   - each field's bit position against the assignment or the packed struct in the RTL package
   - the register-level access — is there a write enable? is the read a constant, or a masked
     combination of state?
   - the build-time instance count parameter

**2. An existing RAL / UVM register model or C header**, if one exists. Different transcription,
same source; disagreement localizes the error immediately.

**3. The spec's reset values**, which are an independent cross-check on field boundaries — as with
the WISHBONE DMA address-mask register, where a reset of `FFFFFFFCh` contradicts the table's
`31:4` field boundary and settles the question in favour of `31:2`.

**4. A read-back test.** The strongest check available: write a known pattern to each RW register and
read it back through the model. It catches offset errors, width errors and endianness errors at once,
and it is the only check that exercises the offset functions rather than reviewing them. Registers
with side effects (§2.4) must be excluded from a naive read-back sweep — which is itself a useful
forcing function for having identified them.

### Compile and check

The model should compile clean and pass the register checker rules:

| Rule | Checks |
|---|---|
| PSL021 | not all three offset schemes implemented |
| PSL022 | no `extend` adding fields to a packed struct |
| PSL023 | no `extend` of `reg_c` / `reg_group_c` |
| PSL024 | `set_handle()` only on the top-level group, only from `init_up`/`init_down` |
| PSL025 | no read on `WRITEONLY`, no write or RMW on `READONLY` |
| PSL026 | only packable field types in packed structs |

Details in `pss-language-ref` → `checker-rules/03-registers-and-layout.md`.

### Record what you verified

The bank file's header comment says which document *and* which RTL file the layout was cross-checked
against — e.g. `wb_dma_regs_c.pss` opens with "Map layout, cross-checked against
`src/spl/wb_dma_rf.svh`" and then reproduces the map. Without that line, the next reader cannot tell
a verified model from a typed one.

---

## 4.3 Hand off to the operation model

The register model is not the deliverable; it is an input to `pss-operation-model-create`. What you
hand over is more than the package:

- **the bank types and the handle contract** — who calls `set_handle()`, with what base;
- **the caller rules from §2.4** — which registers must not be read twice, which must not be
  read-modify-written, which fields hardware clears behind the caller's back;
- **the completion surfaces** — which registers report done/error, and whether reading them has a
  side effect. This is usually the single most consequential thing the register model tells the
  operation model.
- **the address-space requirements** — the MMIO span, and any in-memory structures (descriptors,
  buffers) whose layout constants live in the register package.

→ Finish with `../checklists/review.md`.
