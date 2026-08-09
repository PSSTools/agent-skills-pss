# 2 — From inventory to register types

Each inventory row becomes at most two declarations: a packed value struct and a register type. This
page is the mapping, and — more importantly — the disposal of the facts that have no declaration to
go into.

Language rules (`packed_s` semantics, `sizeof_s`, the `reg_c` hierarchy, symbolic names) are in
`pss-language-ref` → `reference/lang/platform/04-registers.md`. This page assumes them.

---

## 2.1 Does this register need a value struct at all?

The register-value type `R` may be a packed struct **or** a plain bit-vector.

Use `bit[N]` when the register has **no field structure the model uses** — an address register, a
pointer, a data word. `read()`/`read_val()` and `write()`/`write_val()` then become equivalent, and
you avoid inventing field names nobody will reference.

Use a packed struct as soon as any caller wants to touch a field by name, which is nearly always
true for control and status registers.

One plain-word register type, reused across the bank, is idiomatic:

```pss
// The address / mask / descriptor-pointer registers: no field structure.
pure component wb_dma_word_r : reg_c<bit[32], READWRITE, 32> {}
```

Note the trade-off you are accepting: the spec's `31:2 RW Address / 1:0 RO RESERVED` layout is now
unrepresented. That is fine when callers always write aligned addresses, and it is a bug when they
do not — so if alignment is a *requirement* rather than a convention, keep the struct and let the
reserved field carry it. Record which you chose and why.

---

## 2.2 The value struct

```pss
struct wb_dma_ch_sz_s : packed_s<> {
    rand bit[12]  tot_sz;       // 11:0   RW  total transfer size, words
    rand bit[4]   reserved0;    // 15:12  RO
    rand bit[9]   chk_sz;       // 24:16  RW  chunk size, words (0 = all)
    rand bit[7]   reserved1;    // 31:25  RO
}
```

Rules that bite:

- **LSB-first.** Declaration order is bit order (see `01-read-the-spec.md`). Transcribe the spec
  table bottom-up.
- **Comment every field with its bit range and its spec access class.** The bit range lets a reader
  check the transcription without counting; the access class is information PSS is about to lose.
- **`rand` on fields** you want a scenario to be able to randomize into. Reserved fields are
  conventionally `rand` too in this project's banks — harmless, and it keeps the struct uniform —
  but constrain them where a nonzero reserved value would be illegal.
- **Only packable field types**: numeric types, `bool`, enums *with a base type*, packed structs, and
  arrays of those. An enum without `: bit[N]` has no width and is an error (checker rule PSL026).
- **Never add fields in an `extend`** of a packed struct — it silently changes the layout, and the
  register width with it (PSL022).
- Endianness is `packed_s<>` (little-endian) unless the device says otherwise; `packed_s<BIG_ENDIAN>`
  flips the packing to MSB-first.

Sanity check before moving on: the field widths sum to `SZ`, and the last field's high bit is
`SZ - 1`.

---

## 2.3 The register type

```pss
pure component wb_dma_ch_sz_r : reg_c<wb_dma_ch_sz_s, READWRITE, 32> {}
```

- **`pure component`**, always. The LRM recommends it so the tool can handle large static register
  structures efficiently; this project treats it as mandatory.
- **Name it `<reg>_r`** (`pss-coding-guidelines` rule 6) and keep it beside its struct (rule 5.1).
- **State `SZ` explicitly** even when it equals the struct size. It documents the bus access width —
  §21.14.5 selects `read32`/`write32` from `SZ` — and it is the number you check the field sum
  against. `SZ` must be `>=` the struct's bit size; the difference becomes trailing reserved bits.
- The body is empty. Anything you are tempted to put in it belongs in the operation model.

### Mapping the access class

`ACC` is **one value for the whole register**, chosen from three:

| Spec says | `ACC` | Also record |
|---|---|---|
| all fields RO | `READONLY` | — |
| all fields WO | `WRITEONLY` | — |
| any mix, or all RW | `READWRITE` | per-field classes, in comments |
| RO fields + RW fields | `READWRITE` | which fields are RO — writes to them are ignored by HW |
| ROC / RC (read-clears) | `READONLY` **or** `READWRITE` per the writable fields | **the read side effect** — see below |
| W1C | `READWRITE` | **the write side effect** — see below |

Two registers may share an offset when one is `READONLY` and the other `WRITEONLY` (§21.14.2) —
that is the idiom for a read-port/write-port pair at one address, and the offset functions are
allowed to return the same value for both.

Getting `ACC` wrong is not cosmetic: a read on a `WRITEONLY` register, or a write or read-modify-write
on a `READONLY` one, is an error (checker rule PSL025).

---

## 2.4 The RMW trap — the most consequential thing on this page

`write_masked()`, `write_val_masked()`, `write_field()` and `write_fields()` are **read-modify-write**.
They read the register, compute `(current & ~mask) | (val & mask)`, and write it back.

That makes them **unsafe on any register with a read or write side effect**:

- **Read-clear (ROC/RC) fields** — the implicit read consumes them. An RMW to set an enable bit will
  also silently clear the pending interrupt-source bits sharing the register.
- **Write-1-clear (W1C) fields** — the implicit write-back writes the value just read, so every
  currently-set W1C bit gets cleared.
- **Hardware-modified fields** — the read/write pair is not atomic, and a bit hardware set in between
  is lost.

None of this is expressible in PSS. `ACC` cannot say it, and the tool will not warn. So:

> **Rule:** if any field of a register is read-clear, write-1-clear, or hardware-modified, put a
> comment on the register type saying so, and state that the RMW functions must not be used on it.
> Then tell `pss-operation-model-create`, because it changes the completion contract.

The WISHBONE DMA channel CSR is the live example: `int_err`, `int_done`, `int_chk_done` and `err` are
all ROC, so **any** host read of that register consumes the error and completion status. That single
fact is why the operation model reads the channel CSR *exactly once* per operation, and why the
side-effect-free `INT_SRC` snapshot is the preferred completion probe. It appears nowhere in the PSS
type system.

### When RMW *is* right

For a plain RW control register, RMW is exactly what you want, and it is better than a hand-rolled
read / assign-field / write sequence: the field name is resolved by the front end and folded to a
constant mask, so a misspelled field is a compile-time error rather than a wrong bit.

```pss
// Set two fields, leave the rest of the register alone.
comp.regs.cr.write_fields({"mode", "coeff"}, {mode, coeff});
comp.regs.cr.write_field("en", 1);
```

Field names must be string literals naming top-level, non-aggregate fields (§21.14.1). This
toolchain supports all four RMW forms through to generated SV and C.

---

## 2.5 Where the dropped facts go

Close the loop on the inventory. Every fact must have a destination:

| Fact | Destination |
|---|---|
| bit layout, widths | the packed struct |
| register width | `SZ` |
| register-level access direction | `ACC` |
| per-field access class | comment on the field |
| read-clear / write-1-clear / HW-modified | comment on the register **and** a stated caller rule → operation model |
| reset value | comment, if a caller depends on it; otherwise it may be dropped |
| "reading clears the interrupt", "HW clears CH_EN on done" | the operation model's completion contract |
| field value legality (aligned, nonzero, ≤ max) | a constraint in the operation model or on the value struct |

If a fact has no destination, it will be lost — decide that deliberately rather than by omission.

→ Continue to `03-model-groups.md`.
