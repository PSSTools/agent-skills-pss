# Worked example: OpenCores WISHBONE DMA §4 → `wb_dma_regs_pkg`

The finished artifact is `src/pss/wb_dma_regs_pkg/` in this repo. This page reconstructs how it got
there, showing the judgement calls rather than the result — the result is readable on its own.

Source: `docs/dma_doc.md` §4 (OpenCores WISHBONE DMA/Bridge Core, Rev 1.5, January 2002), cross-checked
against `src/spl/wb_dma_rf.svh` and `src/spl/wb_dma_spl_pkg.sv`.

---

## Step 0 — source of truth

No SystemRDL exists, and none is planned: the register description is a 2002 PDF. That is exception
(1) in `reference/00-source-of-truth.md` — the strongest case for hand-writing, since there is
nothing to generate from. Authoring SystemRDL first was considered and set aside as a separate
deliverable.

The price: every provenance and access fact must be carried in comments, and the model must be
verified against the RTL rather than against the document it was typed from.

---

## Step 1 — the map

Table 2 lists a global block at 0x00 and then `Channel 0 Registers` at 0x20, `Channel 1` at 0x40,
… through `Channel 30` at 0x3e0. The enumeration is the spec's; the model's job is to see the
parameterization:

```
0x00  CSR         global control
0x04  INT_MSK_A   per-channel routing mask, bank A
0x08  INT_MSK_B   per-channel routing mask, bank B
0x0c  INT_SRC_A   masked pending snapshot, bank A
0x10  INT_SRC_B   masked pending snapshot, bank B
0x20  channel 0 bank … stride 0x20, eight registers per bank
```

Two counts, not one. The spec allows up to 31 channels; the RTL is elaborated with a `ch_count`
parameter. So:

- `WB_DMA_MAX_CH = 4` — build-time, a `static const int`, sizing the static structure;
- `wb_dma_c.num_ch` — runtime, a randomizable attribute constrained `<= MAX_CH`.

Span: `WB_DMA_CH_BASE + MAX_CH * WB_DMA_CH_STRIDE`, expressed as a constant rather than a literal so
it tracks `MAX_CH`.

**First contradiction.** §4.4 states "Each channel has 4 registers associated with it." Figure 11,
immediately below, lists eight: `CHn_CSR, CHn_SZ, CHn_A0, CHn_AM0, CHn_A1, CHn_AM1, CHn_DESC,
CHn_SWPTR`. Eight × 4 bytes = 0x20, which is exactly the stride Table 2 shows. The figure and the
stride agree; the sentence is stale. **Resolution: eight.**

---

## Step 2 — the fields, and what PSS could not keep

### CSR (0x00) — a one-bit register

Table 3 gives `31:1 RO RESERVED` and `0 RW PAUSE`. Transcribed LSB-first:

```pss
struct wb_dma_gcsr_s : packed_s<> {
    rand bit      pause;        //  0    RW  pause all DMA transfers
    rand bit[31]  reserved;     // 31:1  RO
}
pure component wb_dma_gcsr_r : reg_c<wb_dma_gcsr_s, READWRITE, 32> {}
```

The reserved field is declared even though §21.14.1 would imply it from `SZ`, so the width is
self-evident. The RTL reads the register back as `{31'h0, paused}`, confirming both the position and
that reserved reads zero.

### INT_MSK / INT_SRC (0x04–0x10) — one value type, two register types

Both are a 31-bit per-channel vector with bit 31 reserved, so they share a value struct:

```pss
struct wb_dma_intvec_s : packed_s<> {
    rand bit[31]  ch;           // 30:0  per-channel bits, bit N = channel N
    rand bit      reserved;     // 31    RO
}
pure component wb_dma_intmsk_r : reg_c<wb_dma_intvec_s, READWRITE, 32> {}
pure component wb_dma_intsrc_r : reg_c<wb_dma_intvec_s, READONLY,  32> {}
```

**Second contradiction, and the important one.** Table 5 marks every INT_SRC bit `RW`. §4.3's prose
says the register reports interrupt sources and that "some of the bits will be cleared after a read".
The RTL does neither: `int_srca = int_maska_r & ch_int` — a combinational, read-only, side-effect-free
masked snapshot of the pending sources.

Three sources, three answers; the RTL wins (`01-read-the-spec.md`, resolution order). `ACC` is
`READONLY`.

That resolution turned out to matter far beyond the register model. Because INT_SRC has **no** read
side effect — unlike the channel CSR, below — it is the only completion condition the device offers
that can be polled repeatedly. And because it is ANDed with the routing mask, a channel that is not
routed never appears in it at all, which makes programming INT_MSK a hard prerequisite for every
end-to-end operation. Both facts are recorded as comments in `wb_dma_regs_c.pss` and both were handed
to the operation model.

### CHn_CSR (bank 0x00) — where PSS's three access values run out

Table 6 has 23 fields across seven distinct access classes. PSS gets one value for the register:
`READWRITE`. Everything else went into per-field comments:

```pss
rand bit      stop;          //  9     WO  abort pulse
rand bit      busy;          // 10     RO  currently being serviced
rand bit      done;          // 11     RO  transfer complete
rand bit      err;           // 12     ROC error status
…
rand bit      int_err;       // 20     ROC interrupt source: error
rand bit      int_done;      // 21     ROC interrupt source: done
rand bit      int_chk_done;  // 22     ROC interrupt source: chunk done
```

Four ROC fields. Per `02-model-registers.md` §2.4, that makes this register **hostile to
read-modify-write and to repeated reads**: any host read consumes `err` and all three interrupt
sources. The register type carries a comment block saying exactly that, and the operation model reads
the channel CSR *exactly once* per operation as a direct consequence.

Two more facts with no PSS home, both comments:

- `ch_en` is RW but hardware clears it on done/err — so a caller cannot infer "still armed" from
  having written it;
- `busy` means "this channel is the one the arbiter is currently servicing", **not** "this channel is
  armed" — it is not a completion indicator, and reading it as one is the obvious wrong move the
  comment exists to prevent.

### CHn_SZ (bank 0x04) — reserved holes in the middle

```pss
rand bit[12]  tot_sz;       // 11:0   RW
rand bit[4]   reserved0;    // 15:12  RO
rand bit[9]   chk_sz;       // 24:16  RW
rand bit[7]   reserved1;    // 31:25  RO
```

Two interior reserved regions, numbered rather than named, because omitting either would shift every
field above it. `12 + 4 + 9 + 7 = 32` — the check from `02-model-registers.md` §2.2.

Behavioural facts from the prose, kept as comments because they constrain callers: both counts are in
**words**, `chk_sz == 0` means "move the whole `tot_sz` in one chunk", and `chk_sz > tot_sz` yields
one truncated chunk rather than a hang (confirmed in `src/spl/wb_dma_de.svh`, where the chunk count is
`min(chk_sz, remaining)`).

### The address registers — where a value struct was declined

`CHn_A0`, `CHn_AM0`, `CHn_A1`, `CHn_AM1` and `CHn_DESC` all became one plain-word type:

```pss
pure component wb_dma_word_r : reg_c<bit[32], READWRITE, 32> {}
```

**Third contradiction, and why the struct was declined.** §4.4.4 says the address-mask registers "are
28 bits wide"; Table 9 says `31:4 RW Address Mask / 3:0 RO RESERVED` (28 bits, consistent) — but the
stated reset value is `FFFFFFFCh`, which has bits 3:2 set and therefore implies a `31:2` field, like
the address registers. The table and the reset value cannot both be right.

Rather than encode a boundary the document contradicts itself about, the model uses a bit-vector: no
field names to get wrong, and `read()`/`write()` are equivalent to `read_val()`/`write_val()`. The
alignment requirement (the low bits are reserved either way) moves to the operation model as a
constraint, where it is checkable. This is the trade in `02-model-registers.md` §2.1, taken
deliberately.

### CHn_SWPTR (bank 0x1c)

```pss
rand bit[31]  ptr;          // 30:0  RW  software pointer
rand bit      en;           // 31    RW  SWPTR_EN
```

Table 11 lists `31 RW SWPTR_EN`, `30:2 RW Software pointer`, `1:0 RO RESERVED`. The model folds the
low reserved bits into `ptr` as a 31-bit field — the same call as the address registers, and for the
same reason.

---

## Step 3 — group shape

The decision from `03-model-groups.md` §3.3: **shape B**, one top-level group per channel, not an
array inside a device-wide group.

The reason is structural, not cosmetic. The operation model has a per-channel component,
`wb_dma_ch_c`. With shape B, each instance owns a `wb_dma_ch_regs_c` and binds it to
`WB_DMA_CH_BASE + chan * WB_DMA_CH_STRIDE` in its `\init`, so the channel's identity lives in the
handle and **every register access in the operation code is index-free** — `comp.regs.csr…` rather
than `comp.regs.ch[m_chan].csr…`. The index is computed once at elaboration instead of being threaded
through every operation body.

The cost is that the register package no longer mirrors Table 2 in a single type. That is paid off by
the map comment at the top of `wb_dma_regs_c.pss`, which reproduces the layout, and by the header of
`wb_dma_ch_regs_c.pss`, which states the choice and why — so a reader who expects to find the channel
banks nested in the global group learns immediately that they are not, and why.

Both groups use the instance scheme, and both supply `get_offset_of_instance_array()` returning `-1`
with a comment explaining that the empty function is the scheme's second half rather than an
oversight (PSL021: never implement all three).

---

## Step 4 — what verification caught

The layout was cross-checked against `src/spl/wb_dma_rf.svh` and `src/spl/wb_dma_spl_pkg.sv`, which
is what settled all three contradictions above. Each resolution is recorded in the source with **both
sides stated**, so that a future reader comparing the PSS to the datasheet finds a decision rather
than an apparent error and does not "fix" it back.

Facts handed to the operation model, per `04-bind-and-verify.md` §4.3:

| Fact | Consequence downstream |
|---|---|
| channel CSR has four ROC fields | read it exactly once per operation |
| INT_SRC is side-effect-free | it is the preferred completion probe |
| INT_SRC is masked by INT_MSK | routing must be programmed before any operation can complete |
| hardware clears `ch_en` on done/err | "still armed" cannot be inferred from the write |
| `busy` ≠ armed | not a completion indicator |
| address registers modelled as words | alignment becomes an operation-model constraint |

Only the first column is register-model work. The second column is why it was worth doing carefully.
