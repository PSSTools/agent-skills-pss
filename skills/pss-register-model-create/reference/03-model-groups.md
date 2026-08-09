# 3 — Shaping the groups

A `reg_group_c` is an **address decode**: a set of register instances plus the functions that place
them. The registers, their value structs, and the group go in one file named for the group
(`pss-coding-guidelines` rule 5.2) — nobody includes half a decode.

---

## 3.1 The group

```pss
pure component wb_dma_ch_regs_c : reg_group_c {
    wb_dma_ch_csr_r   csr;      // 0x00  control / status
    wb_dma_ch_sz_r    sz;       // 0x04  total + chunk size
    wb_dma_word_r     adr0;     // 0x08  source address
    // …

    function bit[64] get_offset_of_instance(string name) {
        match (name) {
            ["csr"]:  return 0x00;
            ["sz"]:   return 0x04;
            ["adr0"]: return 0x08;
            default:  return -1;
        }
    }

    function bit[64] get_offset_of_instance_array(string name, int index) {
        return -1;
    }
}
```

- **`pure component`**, deriving from `reg_group_c`. Never `extend` `reg_group_c` or `reg_c`
  themselves (PSL023) — derive.
- **Comment each instance with its offset.** The offset function is the truth, but a reader scanning
  the declarations should not have to jump.
- **The offset functions stay inline**, not in a `functions/` directory — they *are* the decode.
  This is the one documented exception to `pss-coding-guidelines` rule 4.
- A group may hold register instances, register arrays, and other groups.

---

## 3.2 Pick exactly one offset scheme

Two schemes exist, and implementing **all three** functions is an error (PSL021):

| Scheme | Functions | Use when |
|---|---|---|
| **instance** | `get_offset_of_instance()` **and** `get_offset_of_instance_array()` | default — a flat bank, arrays or not |
| **path** | `get_offset_of_path()` alone | the offset of a nested element depends on the whole path, e.g. an interleaved or computed layout |

Use the instance scheme unless you have a reason. Supply **both** of its functions even when the
group has no arrays — the pair is the scheme, and the array function then simply returns `-1`, with a
comment saying why it is empty:

```pss
// No register arrays in this group, but the scheme is "instance +
// instance_array" (not get_offset_of_path), so both are supplied.
function bit[64] get_offset_of_instance_array(string name, int index) {
    return -1;
}
```

Return `-1` from the `default` arm as the error case. The functions are `pure` — no side effects, and
no reliance on component state that could vary between calls.

Arrays are addressed arithmetically, not enumerated:

```pss
function bit[64] get_offset_of_instance_array(string name, int index) {
    match (name) {
        ["ch"]:  return WB_DMA_CH_BASE + index * WB_DMA_CH_STRIDE;
        default: return -1;
    }
}
```

The same one-of-two rule applies to the 3.1 `get_mnemonic_*` functions (§21.14.6.1), independently of
the offset choice.

---

## 3.3 The replication decision: array-in-one-group vs per-instance top-level group

When a device has N identical banks (channels, ports, lanes), there are two shapes. **This is the
main structural choice on this page, and it is decided by how the operation model is organized, not
by the register map.**

### Shape A — one device-wide group holding an array

```pss
pure component dev_regs_c : reg_group_c {
    dev_gcsr_r      csr;
    dev_ch_regs_c   ch[MAX_CH];     // nested group array
    // get_offset_of_instance_array("ch", i) -> BASE + i*STRIDE
}
```

- One `set_handle()` for the whole device; nested offsets compose automatically.
- Mirrors the address map exactly, so it reads like the datasheet.
- **But** every access from a channel-scoped operation carries an index:
  `comp.regs.ch[m_chan].csr.write_field("ch_en", 1)`, and the channel component must know its own
  index and reach up to the device's group.

### Shape B — one top-level group per instance

```pss
component wb_dma_ch_c {
    wb_dma_ch_regs_c  regs;         // its own top-level group

    solve function void \init (int chan, addr_handle_t base) {
        regs.set_handle(make_handle_from_handle(
            base, WB_DMA_CH_BASE + chan * WB_DMA_CH_STRIDE));
    }
}
```

- Each instance component owns its bank and binds it to its own region.
- **Every register access in the operation code is index-free**: `comp.regs.csr…`. The channel's
  identity lives in the handle, computed once at elaboration, instead of being threaded through every
  operation body.
- The base and stride move into the *binding*, not the decode.
- **But** the register package no longer mirrors the map in one type, so the address arithmetic has
  to be stated somewhere visible — hence the map comment at the top of the top-level bank file.

### Choosing

| Choose | When |
|---|---|
| **A** | the operation model is device-scoped and already carries an instance index; you want the register package to be a faithful transcription of the map |
| **B** | the operation model has a **per-instance component** (a channel component, a port component). Then B removes the index from every access and gives each component an independent handle. |

This project chose **B** for the WISHBONE DMA, because `wb_dma_ch_c` exists per channel; the choice
and its rationale are recorded in the header comment of `wb_dma_ch_regs_c.pss`. Whichever you pick,
**write down why** — the next reader will otherwise see only that the bank does not look like the
datasheet.

---

## 3.4 Address-map constants

Base, stride, build-time instance count and the total span go in the **top-level bank's file**
(`pss-coding-guidelines` rule 5.2) as `static const`, because they describe where the whole register
file sits:

```pss
static const int      WB_DMA_MAX_CH     = 4;    // build-time (RTL ch_count)
static const bit[64]  WB_DMA_CH_BASE    = 0x20;
static const bit[64]  WB_DMA_CH_STRIDE  = 0x20;
static const bit[64]  WB_DMA_REG_SPAN   =
    WB_DMA_CH_BASE + WB_DMA_MAX_CH * WB_DMA_CH_STRIDE;
```

`WB_DMA_MAX_CH` is compile-time because it sizes static structure; the number of instances a scenario
*uses* is a runtime component attribute constrained `<= MAX_CH` (see `01-read-the-spec.md`).

Constants that describe an *in-memory* layout the device also touches — descriptor size, field
offsets within a descriptor — belong here too. They are part of the same address contract even though
they are not registers.

---

## 3.5 File organization

Per `pss-coding-guidelines`:

```
src/pss/<dev>_regs_pkg/
    <dev>_regs_c.pss        <- top-level bank + address-map constants
    <dev>_ch_regs_c.pss     <- the per-instance bank
```

- One file per bank; the value structs and register types live in the file of the bank that uses
  them. A register type shared by two banks goes in whichever bank owns it more naturally, and the
  other file's `import` picks it up — but note the ordering constraint below.
- Each file opens the package explicitly (`package <dev>_regs_pkg { … }`) and carries its own
  `import std_pkg::*;` and `import addr_reg_pkg::*;`. Imports are per file; never inherit one from a
  sibling.
- **File order is dependency order.** `pssparser` resolves in presentation order, and a forward
  reference to a type in a later file of the same package is a hard crash, not a diagnostic. If two
  bank files have an order dependency, that is usually a sign the shared type belongs in the file that
  uses it — which is exactly how `wb_dma_word_r` ended up in the channel bank rather than the global
  one. Record the working order in `src/pss/README.md`.

→ Continue to `04-bind-and-verify.md`.
