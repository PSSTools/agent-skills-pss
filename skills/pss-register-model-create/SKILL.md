---
name: pss-register-model-create
description: Derive a PSS register model — packed value structs, reg_c register types, reg_group_c
  banks, offset functions and handle binding — from a device specification (datasheet, register
  tables, RTL register file, IP-XACT). Use when asked to write, review, or extend PSS registers by
  hand. Prefer SystemRDL as the source of truth wherever a generator flow is available; this skill
  starts by making that call explicitly, then covers the hand-written path when SystemRDL is not on
  the table.
---

# Creating a PSS register model

This skill answers **"what is in this device's register map, and how does it become PSS?"**

It is a *derivation procedure*, not a language reference. Its inputs are things that are not PSS —
a datasheet, a register table, a Verilog register file, an IP-XACT file — and its output is the
register package the operation model programs against.

Neighbouring skills, which this one hands off to constantly:

| Skill | Answers |
|---|---|
| `pss-language-ref` | *What does `reg_c` mean? Is this legal PSS?* (see `reference/lang/platform/04-registers.md`) |
| `pss-coding-guidelines` | *Which file does this go in?* (rules 5.1, 5.2, 6) |
| `pss-operation-model-create` | *What does the device **do**?* — the consumer of this model |
| **this skill** | ***What registers exist, what do they mean, and what survives the trip into PSS?*** |

---

## Step 0 — do not write this by hand if you don't have to

**A PSS register model should normally be generated from SystemRDL, not typed.** A register map is
consumed by the RTL, the UVM RAL model, the C header, the documentation *and* the PSS model; every
hand-maintained copy is a copy that will drift, and register drift fails silently as wrong bus
traffic rather than loudly as a compile error.

Before writing a line of PSS, run the gate in **`reference/00-source-of-truth.md`**. It is short.
It tells you when hand-writing is genuinely the right answer (it sometimes is — the OpenCores
WISHBONE DMA in this repo is one such case) and, when it is, what you owe the reader in exchange.

Only continue past this point once that decision is recorded.

---

## The procedure

Each step has a reference page. Work them in order; each one closes questions the next depends on.

```
   0. choose the source of truth            reference/00-source-of-truth.md
            │
   1. read the spec: map, then fields       reference/01-read-the-spec.md
            │        ← produces a register inventory with every fact, before any PSS
   2. decide what PSS can carry             reference/02-model-registers.md
            │        ← value structs, reg types, access modes, widths
   3. shape the groups                      reference/03-model-groups.md
            │        ← banks, arrays vs per-instance, offset functions
   4. bind and verify                       reference/04-bind-and-verify.md
            │        ← set_handle, address regions, cross-check against RTL
   5. review                                checklists/review.md
```

A worked end-to-end example — the OpenCores WISHBONE DMA `docs/dma_doc.md` §4 turning into
`src/pss/wb_dma_regs_pkg/`, with every judgement call shown — is in
**`examples/wb-dma-walkthrough.md`**. Read it if you learn faster from a finished artifact than
from a procedure.

---

## The one idea that makes the rest make sense

**PSS's register model is deliberately thin, and most of what a register spec says has no PSS
construct to land in.**

`reg_c<R, ACC, SZ>` carries exactly four things: the field layout (via the packed struct `R`), one
access mode for the *whole* register (`ACC`), the width (`SZ`), and — via the enclosing group's
offset functions — the address.

It does **not** carry reset values, per-field access classes, read-clear or write-1-clear side
effects, volatility, hardware-modified fields, or field-level constraints. There is nowhere to put
them.

So every step of this procedure is really the same question asked repeatedly: *this fact from the
spec — does it become a PSS declaration, a comment, or a rule the operation model must obey?* A
register model that answers "declaration" for the layout and silently drops the rest is the common
failure. The read-clear status bit that the spec mentions in one sentence of prose is the fact that
decides whether the operation model may poll a register twice — and it will vanish unless you
carry it forward deliberately.

Concretely, the three destinations:

| Spec fact | Lands in |
|---|---|
| bit positions, widths, register width, offsets, array strides | **PSS declarations** — the packed struct, `SZ`, the offset functions |
| whole-register access direction (RO / WO / RW) | **PSS declaration** — the `ACC` template argument |
| per-field access class, read-clear / write-1-clear, reset value, hardware-cleared fields | **a comment on the field** *and* a stated constraint the operation model inherits |
| "reading this register clears the interrupt", "hardware clears CH_EN on done" | **the operation model's completion contract** — hand it to `pss-operation-model-create` |

The comment is not documentation politeness. It is the only surviving representation of a fact that
changes what callers may legally do.

---

## Fastest path when you already know the shape

If you have a clean register table and just need the PSS idiom, the canonical bank is:

```pss
package dev_regs_pkg {
    import std_pkg::*;          // packed_s
    import addr_reg_pkg::*;     // reg_c, reg_group_c, reg_access

    struct dev_ctrl_s : packed_s<> {        // LSB-first: declaration order IS bit order
        rand bit      en;           //  0     RW
        rand bit[31]  reserved;     // 31:1   RO
    }
    pure component dev_ctrl_r : reg_c<dev_ctrl_s, READWRITE, 32> {}

    pure component dev_regs_c : reg_group_c {
        dev_ctrl_r  ctrl;           // 0x00

        function bit[64] get_offset_of_instance(string name) {
            match (name) {
                ["ctrl"]: return 0x00;
                default:  return -1;
            }
        }
        function bit[64] get_offset_of_instance_array(string name, int index) {
            return -1;
        }
    }
}
```

Everything else in this skill is about the cases where the table is not clean, the access classes do
not fit three enum values, or the map has arrays. Those are the majority.
