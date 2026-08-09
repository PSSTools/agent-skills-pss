# 1 — Reading the spec: the map, then the fields

Produce a **register inventory** before writing any PSS. The inventory is a table, not prose, and it
records every fact the spec offers — including the ones PSS cannot represent, because step 2 decides
where each one goes and it cannot decide about facts you did not write down.

Two passes: the address map, then the field layouts.

---

## Pass 1 — the address map

From the map table (and, decisively, from the RTL address decode), record for each entry:

| Column | Notes |
|---|---|
| name | the spec's name, e.g. `CH0_CSR` |
| byte offset | from the *bank* base, not the system base |
| width in bits | usually the bus width; not always |
| access | RO / WO / RW at the register level |
| replication | is this one of N identical instances? what is the stride? |
| reset value | PSS cannot hold it; the operation model may need it |

### Find the arrays

Specs enumerate; PSS parameterizes. A table listing `CH0_CSR … CH30_CSR` at 0x20, 0x40, … is one
register replicated 31 times at stride 0x20, and writing 31 declarations is the wrong answer. Look
for:

- repeated blocks with a constant stride → a **bank** replicated (a group array or a per-instance
  group — that choice is `03-model-groups.md`)
- a single register replicated within a bank → a **register array** in the group, addressed by
  `get_offset_of_instance_array()`

Record the base and stride as named constants; they become `static const` in the top-level bank file
(`pss-coding-guidelines` rule 5.2).

### Separate build-time from run-time counts

"Up to 31 channels" is two different numbers:

- the **build-time** count the RTL was elaborated with — this sizes the static structure, so it is a
  compile-time constant in the register package (`WB_DMA_MAX_CH`);
- the **run-time** count a given scenario uses — a randomizable component attribute, constrained
  `<= MAX_CH`.

Conflating them either freezes the model to one configuration or makes the register structure
non-static. Both are wrong.

### Bound the region

Sum base + count × stride to get the span the register file occupies. That number becomes the size
of the non-allocatable address region in `04-bind-and-verify.md`.

---

## Pass 2 — the field layouts

For each register, record every field: bit range, name, access class, meaning, and reset. Then
record the **whole-register** facts the field table does not carry — read side effects, write side
effects, hardware-modified fields.

### Bit order runs the other way

Spec tables are written **MSB-first, descending**. PSS packed structs with the default
`LITTLE_ENDIAN` layout are **LSB-first**: the first-declared field occupies bit 0 and each
subsequent field stacks toward the MSB. **Declaration order is the bit numbering.**

So you transcribe the table bottom-up. This is the single most common transcription error; check it
by asserting that the last-declared field's high bit equals `SZ - 1`.

### Reserved fields are declared, not omitted

A gap in the layout is a bit position error for everything above it. Declare reserved regions
explicitly, named and commented (`reserved`, `reserved0`, `reserved1`). The only region you may omit
is a *trailing* one, because §21.14.1 makes `SZ - sizeof_s<R>::nbits` implicitly reserved — but
declaring it anyway makes the width self-evident and lets the reader check the arithmetic. Prefer
declaring it.

### The access-class column is where the information is

Datasheets use far more classes than PSS's three. Record the spec's class verbatim; step 2 maps it.
The classes that matter most are the ones with *side effects*, because they constrain callers:

| Spec class | Means |
|---|---|
| RO | read-only status |
| RW | plain read/write |
| WO | write-only; a write is an event, a read returns nothing meaningful |
| **ROC / RC** | **read-only, cleared by the read** — reading consumes the information |
| **W1C** | **write-one-to-clear** — writing back what you read clears bits |
| RW with HW-clear | software writes it, hardware also clears it (e.g. an enable cleared on done) |

The bolded ones change what the operation model may do (see `02-model-registers.md`, "the RMW
trap"). Never let them stay only in the spec.

---

## Spec hazards — this is the messy part

Real register specs are extracted from PDFs and contradict themselves. Treat every one of the
following as expected, not exceptional. Examples cited are genuine, from `docs/dma_doc.md`.

**PDF-to-text mangling.** Table headers, page footers and rotated column labels interleave with the
rows. In `docs/dma_doc.md` the string `sseccA` (a rotated "Access") appears mid-table, `Table 3: CSR
Register` heads what is actually Table 4's content, and the `Description` header lands several lines
below the rows it labels. **Read the field rows, ignore the surrounding furniture, and if the row
ordering looks impossible, go to the PDF or the RTL.**

**Prose contradicting the table.** §4.4.3 says the address registers "are 30 bits wide"; Table 8 says
`31:2 RW Address` — which is 30 bits, consistent. §4.4.4 says the address mask registers "are 28 bits
wide" and Table 9 says `31:4`, consistent — but the stated reset value is `FFFFFFFCh`, which has bits
3:2 set and therefore implies a 31:2 field. The table and the reset value cannot both be right.

**Counts that disagree.** §4.4 states "Each channel has 4 registers associated with it"; Figure 11
immediately below lists eight. The figure is right.

**Access columns that disagree with the described behaviour.** Table 5 marks every INT_SRC bit `RW`,
while §4.3's prose says the register reports interrupt sources and "some of the bits will be cleared
after a read" — and the RTL implements it as a read-only masked snapshot (`int_srca = int_maska_r &
ch_int`). Three sources, three answers.

### The resolution order

1. **RTL** — the register-file decode and the field assignments. It is what the DUT actually does.
2. **Prose** — the paragraph explaining the register's purpose, which usually survives editing better
   than the table.
3. **Tables** — most damaged by extraction, most likely to be stale.

Reset values, when stated, are a useful cross-check on all three (as with the address-mask case
above).

**Write the resolution into the source as a comment, with both sides.** A future reader who finds the
PSS disagreeing with the datasheet needs to know it was a decision, not an error — otherwise they
will "fix" it back.

---

## Inventory complete when

- every register in the map has a byte offset, width, register-level access, and replication factor
- every field has a bit range, name, access class and reset value
- for each register: does a read have a side effect? does a write? does hardware modify it?
- every array has a named base and stride, and the build-time count is distinguished from the
  run-time one
- every spec contradiction has a recorded resolution and a source that won

→ Continue to `02-model-registers.md`.
