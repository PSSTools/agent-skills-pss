# Address spaces, allocation, and memory access

*Domain: platform. LRM §21.10–21.13. All types from `addr_reg_pkg`.*

An **address space** models storage: system memory, SRAM, disk, MMIO windows, routing tables.
It is composed of **regions**, characterized by user-defined **traits**. Actions and objects
make **claims** on a space; the tool allocates addresses satisfying the claim's constraints.
An **address handle** is an opaque reference to a location, resolved on the target platform.

## When you are writing this

- The user said "allocate a buffer", "DMA to memory", "the descriptor lives at 0x…".
- You need an MMIO window for a register group.
- You need two actions to use non-overlapping memory — or deliberately overlapping memory.
- You need to read or write raw bytes on the target.

## Decide

| You need… | Use |
|---|---|
| memory the tool allocates for you | `rand addr_claim_s<> claim;` in an action or object |
| an address you can constrain **at solve time** | `transparent_addr_claim_s<>` in a **transparent** space |
| a fixed window at a known address (MMIO) | `add_nonallocatable_region()` in an init exec |
| allocatable memory | `add_region()` in an init exec |
| several kinds of memory, distinguished | a **trait** struct + constraints on `claim.trait` |
| two claims to share addresses | `alloc_mode.sharing = OVERLAP` / `SAME_ADDRESS` |
| the concrete address at runtime | `addr_value(h)` — **target** |
| the concrete address at solve time | `addr_value_solve(h)` — **`pre_body` only** |
| to know which region a handle came from | `get_tag(h)` |
| to read/write raw memory | `read8/16/32/64`, `write*`, `read_bytes`, `read_struct`, … |
| a device register map | `04-registers.md`, which is built on all of this |

**Opaque vs transparent** is the decision that shapes everything else:

- **opaque** (`addr_claim_s` in `contiguous_addr_space_c`) — the tool allocates; **the absolute
  address is not known at solve time**. This is the default and the right choice for buffers.
- **transparent** (`transparent_addr_claim_s` in `transparent_addr_space_c`) — the region's
  start address is known to the tool, so you can constrain `claim.addr` directly. Required for
  fixed addresses, MMIO, and anything the solve must reason about numerically.

## Canonical form

```pss
package ip_pkg {
    import addr_reg_pkg::*;

    struct mem_trait_s : addr_trait_s {
        rand mem_kind_e kind;                 // DRAM / SRAM / ...
    }
}

component pss_top {
    import addr_reg_pkg::*;
    import ip_pkg::*;

    my_ip_c ip;
    transparent_addr_space_c<mem_trait_s> sys_mem;

    exec init_up {                            // regions are added ONLY in init execs
        transparent_addr_region_s<mem_trait_s> dram;
        addr_handle_t h;

        dram.size      = 0x1000_0000;
        dram.addr      = 0x8000_0000;
        dram.tag       = "dram";
        dram.trait.kind = DRAM;
        h = sys_mem.add_region(dram);         // allocatable

        transparent_addr_region_s<> mmio;
        mmio.size = 1024;
        mmio.addr = 0xA000_0000;
        h = sys_mem.add_nonallocatable_region(mmio);   // MMIO: never allocated from
    }
}

component my_ip_c {
    action dma_write {
        rand transparent_addr_claim_s<ip_pkg::mem_trait_s> dst;

        constraint dst.size      == 4096;
        constraint dst.alignment == 64;
        constraint dst.trait.kind == DRAM;    // pick a matching region
        constraint dst.addr % 0x1000 == 0;    // only possible for a TRANSPARENT claim

        exec body {
            addr_handle_t h  = make_handle_from_claim(dst);
            addr_handle_t h2 = make_handle_from_handle(h, sizeof_s<int>::nbytes);
            write32(h, 0xdead_beef);
            write32(h2, 0);
            bit[32] v = read32(h);
        }
    }
}
```

## Rules

### Address space components (§21.10.1)

```pss
component addr_space_base_c {};                          // not instantiable directly

component contiguous_addr_space_c <struct TRAIT : addr_trait_s = empty_addr_trait_s>
    : addr_space_base_c {
    solve function addr_handle_t add_region(addr_region_s<TRAIT> r);
    solve function addr_handle_t add_nonallocatable_region(addr_region_s<> r);
    bool byte_addressable = true;
}

component transparent_addr_space_c <struct TRAIT : addr_trait_s = empty_addr_trait_s>
    : contiguous_addr_space_c<TRAIT> {};
```

- Address spaces are **components**, instantiated in `pss_top` or below.
- A **contiguous** space has non-negative integer addresses and contiguously addressed atoms.
- A **byte-addressable** space is a contiguous space whose atom is a byte;
  `contiguous_addr_space_c` is byte-addressable unless `byte_addressable` is set false.
- **`add_region` and `add_nonallocatable_region` may only be called in `exec init_down` /
  `init_up`.** Both return a handle to the region's start.
- **Non-allocatable regions are never used by the allocator** — this is how MMIO is modelled.
- **Only transparent regions may be added to a transparent space** via `add_region()`. The
  converse is fine: transparent regions may be added to a non-transparent space.
- Other space kinds may be derived from the base types; PSS does not standardize them.

### Traits and regions (§21.10.2, §21.10.3)

```pss
struct addr_trait_s {};
struct empty_addr_trait_s : addr_trait_s {};

struct addr_region_base_s { bit[64] size; string tag; }
struct addr_region_s <struct TRAIT : addr_trait_s = empty_addr_trait_s>
    : addr_region_base_s { TRAIT trait; }
struct transparent_addr_region_s<...> : addr_region_s<...> { bit[64] addr; }
```

- **All regions of a space share a trait *type*; each region has its own trait *value*.**
- `size` is **required**; `tag` is optional and retrievable with `get_tag()`.
- A transparent region's `addr` is its start; its end is `addr + size - 1`.
- Regions are part of the **static component hierarchy**.

### Claims (§21.11)

```pss
struct addr_claim_base_s {
    rand bit[64] size;
    rand bool    permanent;
    constraint default permanent == false;
}
struct addr_claim_s <TRAIT = empty_addr_trait_s, ALLOC_MODE = alloc_base_mode_s>
    : addr_claim_base_s {
    rand TRAIT      trait;
    rand bit[64]    alignment;      // domain: powers of two, 2**0 … 2**63
    rand ALLOC_MODE alloc_mode;
}
struct transparent_addr_claim_s<...> : addr_claim_s<...> { rand bit[64] addr; }
```

- A claim struct may be instantiated **under an action, a flow or resource object, or any of
  their nested structs**. Declaring it **causes allocation** when the object is instantiated or
  the action is traversed.
- **A contiguous claim is always a contiguous chunk**, potentially spanning adjacent regions.
- **Constraints on `claim.trait` must be satisfied by the allocated addresses** — allocation
  comes from regions whose trait values satisfy them (§21.11.5).
- **Matching a claim to a space** (§21.11.7): the space must match the claim's **trait type**,
  be instantiated in a **containing component** of the scenario entity, and be the **nearest**
  such going up to the root. **More than one match at that level is an error.**
- **A transparent claim associated with a non-transparent space is an error** (§21.11.4).
- The standard does **not** define how a tool resolves claims or generates runtime allocation.

### Allocation mode (§21.11.3)

```pss
enum alloc_access_mode_e { EXCLUSIVE, SHARED };
enum alloc_share_mode_e  { RANDOM, OVERLAP, SAME_ADDRESS };
enum alloc_skip_mode_e   { DONT_SKIP, SKIP };
struct alloc_base_mode_s {
    rand alloc_access_mode_e access;   constraint default access   == EXCLUSIVE;
    rand alloc_share_mode_e  sharing;  constraint default sharing  == RANDOM;
    rand alloc_skip_mode_e   skipping; constraint default skipping == DONT_SKIP;
    rand int                 tag;      constraint default tag      == -1;
}
```

By default **every claim is exclusive** and gets its own addresses. Override to share a start
address, overlap, or skip allocation entirely.

### Allocation consistency (§21.11.6)

Two claim instances **shall resolve to mutually exclusive address sets** if both are from the
same space **and** an action with access to one may **overlap in execution time** with an action
with access to the other. This is the guarantee that makes concurrent DMA modelling safe — and
it is why claim placement (which action can see it) matters as much as its constraints.

### Address space groups (§21.12)

```pss
component addr_space_group_c { function void add_addr_space(ref addr_space_base_c s); }
```

The union of several spaces sharing common storage, so IP models with different views of the
same memory can be integrated.

### Handles (§21.13.3, §21.13.4)

```pss
typedef chandle addr_handle_t;
const addr_handle_t nullhandle = /* implementation-specific */;
struct sized_addr_handle_s <int SZ, int lsb = 0, endianness_e e = LITTLE_ENDIAN>
    : packed_s<e> { addr_handle_t hndl; }

function addr_handle_t make_handle_from_claim(addr_claim_base_s claim,
                                              bit[64] offset = 0, bool sub = false);
function addr_handle_t make_handle_from_handle(addr_handle_t handle, bit[64] offset);
```

- **A handle resolves to a concrete address on the target platform. Its concrete value cannot
  be obtained during the solve process.**
- `nullhandle` represents address 0 in the target space, regardless of region mapping.
- **A field of type `addr_handle_t` may not be declared directly in a packed struct** — use
  `sized_addr_handle_s`, which is what gives the field a width.
- Handles also come from `add_region()` / `add_nonallocatable_region()`.

### Address value functions (§21.13.5–21.13.8)

| Function | Platform | Callable from |
|---|---|---|
| `target function bit[64] addr_value(h, desc = {})` | target | `body`, `run_start`, `run_end`, and functions called from them |
| `solve function bit[64] addr_value_solve(h, desc = {})` | solve | **`pre_body` only** — elsewhere the return value is **undefined** |
| `solve function bool addr_value_abs(h, desc = {})` | solve | **`pre_body` only** |
| `function string get_tag(h)` | either | `pre_body`, `body`, `run_start`, `run_end`, and functions called from them |

`addr_value_solve()` returns an **absolute address** if the handle is in a transparent region;
in an opaque region it may return an absolute address **or an offset**, depending on
tool-specific metadata. `addr_value_abs()` tells you which.

### Access operations (§21.13.9)

All **`target`** functions, callable from `body` / `run_start` / `run_end` and functions reached
from them.

```pss
struct mem_access_desc_s {}    // extensible: tool/user metadata per access

target function bit[8]  read8 (addr_handle_t h, mem_access_desc_s d = {});   // …16, 32, 64
target function void    write8(addr_handle_t h, bit[8] data, mem_access_desc_s d = {});

target function void read_bytes (addr_handle_t h, list<bit[8]> data, int size);
target function void write_bytes(addr_handle_t h, list<bit[8]> data);        // size = list size

target function void read_struct (addr_handle_t h, struct packed_struct);
target function void write_struct(addr_handle_t h, struct packed_struct);
```

- Primitive reads: the first byte becomes bits `[7:0]`, the next `[15:8]`, and so on. Writes
  mirror that.
- `read_bytes` **resizes the list and overwrites its contents**; index 0 is the byte at the
  handle address.
- `read_struct`/`write_struct` require a **`packed_s` subtype**. A struct of 8/16/32/64 bits at
  a correspondingly aligned address is implemented as a single primitive access; otherwise the
  tool may split it into any mix of primitives, or a single `read_bytes`/`write_bytes`.
- **`mem_access_desc_s` is an extensible descriptor** (`extend struct mem_access_desc_s { … }`)
  for passing tool- or user-defined metadata to an access.
- **Executor-based customization** (§21.13.9.5): primitive read/write, byte-list read/write, and
  address-resolution calls are **delegated to identically-prototyped functions on the executor
  instance** assigned to the evaluating action or object. Overriding `addr_value()` in an
  executor changes effective-address computation for every access on it.

## Gotchas

**Adding a region outside an init exec.**
```pss
exec body { sys_mem.add_region(r); }   // WRONG: solve function, init execs only
```
*Tier 2.*

**Constraining `addr` on an opaque claim.**
```pss
rand addr_claim_s<> c;
constraint c.addr == 0x1000;   // WRONG: addr_claim_s has no addr; it isn't known at solve
```
*Tier 1–2.* Use `transparent_addr_claim_s` in a `transparent_addr_space_c`.

**A transparent claim landing in a non-transparent space.** An error (§21.11.4) — and the
association is by *nearest matching trait type*, so it can happen without you naming the space
at all.
*Tier 2–3.*

**Two matching spaces at the same component level.** An error (§21.11.7c). Distinguish them by
trait type.
*Tier 2–3.*

**Allocating from an MMIO window.** Add MMIO with `add_nonallocatable_region()`, or the
allocator will hand out register addresses as buffers.
*Tier 4* — a working model that corrupts the DUT.

**Calling `addr_value_solve()` outside `pre_body`.** The return value is **undefined** — not an
error.
*Tier 4*, and one of the nastiest on this page.

**Expecting a handle's numeric value at solve time.** Not available (§21.13.3.1) — that is the
definition of opaque. Constrain the claim, not the address.
*Tier 2–4.*

**`addr_handle_t` directly in a packed struct.** Not permitted; use `sized_addr_handle_s<SZ>`.
*Tier 2.*

**Assuming exclusivity between claims that never overlap in time.** The guarantee applies to
claims whose accessing actions **may overlap**. Sequential actions may legitimately be given the
same addresses.
*Tier 4* — usually fine, occasionally the cause of a "why did my data disappear".

**Alignment not a power of two.** `alignment`'s domain is `2**0 … 2**63`; anything else is
unsatisfiable.
*Tier 3.*

**Forgetting `size`.** Required on every region (§21.10.3.1).
*Tier 3.*

**`read_bytes` into a list you expected to keep.** It resizes and overwrites.
*Tier 4.*

## See also

- `04-registers.md` — built directly on regions, handles, and these access functions.
- `01-executors.md` — where custom read/write/`addr_value` implementations live.
- `../structural/02-components.md` — address spaces are components; placement decides matching.
- `../procedural/01-exec-blocks.md` — which exec kind each function is legal in.
- `../../playbooks/06-access-registers-and-memory.md` — task-first.
