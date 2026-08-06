# Playbook: access registers and memory

*"Program the control register." "DMA into a 4K buffer." "The MMIO window is at 0xA0000000."*

## Steps — registers

**1. Describe the register's layout as a packed struct.**

```pss
package my_ip_regs_pkg {
    import addr_reg_pkg::*;
    struct CR : packed_s<> {       // LITTLE_ENDIAN by default — state it if not
        bit     en;
        bit[11] pad;
        bit[4]  mode;
        bit[16] coeff;
    }
}
```

First-declared field is at the **lowest address**. Only numeric types, `bool`, **based** enums,
packed structs, and arrays of those are allowed.

**2. Declare the register type.**

```pss
    pure component cr_r  : reg_c<CR> {}                    // READWRITE, SZ = 32
    pure component sts_r : reg_c<bit[32], READONLY> {}
```

**3. Declare the group and exactly one offset scheme.**

```pss
    pure component regs_c : reg_group_c {
        cr_r  cr;
        sts_r sts;
        cr_r  aux[4];
        function bit[64] get_offset_of_instance(string name) {
            match (name) { ["cr"]: return 0x0; ["sts"]: return 0x4; default: return -1; }
        }
        function bit[64] get_offset_of_instance_array(string name, int index) {
            match (name) { ["aux"]: return 0x10 + index*4; default: return -1; }
        }
    }
```

Either the instance pair **or** `get_offset_of_path()` — **never all three**.

**4. Bind the top-level group to an address region, once, in an init exec.**

```pss
component dma_c {
    my_ip_regs_pkg::regs_c     regs;
    transparent_addr_space_c<> sys_mem;

    exec init_up {
        transparent_addr_region_s<> mmio;
        addr_handle_t h;
        mmio.size = 1024;
        mmio.addr = 0xA000_0000;
        h = sys_mem.add_nonallocatable_region(mmio);   // MMIO: NOT allocatable
        regs.set_handle(h);
    }
}
```

**5. Access it from a target exec.**

```pss
    action cfg {
        rand bit[4] mode;
        exec body {
            comp.regs.cr.write_field("en", 1);
            comp.regs.cr.write_masked({.mode=~0}, {.mode=mode});
            bit[32] s = comp.regs.sts.read_val();
        }
    }
```

Mask idiom: `~0` sets all bits of a field; omitted fields default to 0 and are excluded.

## Steps — memory

**1. Add an allocatable region during elaboration.**

```pss
exec init_up {
    transparent_addr_region_s<> dram;
    dram.size = 0x1000_0000;
    dram.addr = 0x8000_0000;
    dram.tag  = "dram";
    h = sys_mem.add_region(dram);
}
```

**2. Claim from an action or object.**

```pss
action dma_write {
    rand transparent_addr_claim_s<> dst;
    constraint dst.size == 4096;
    constraint dst.alignment == 64;
    exec body {
        addr_handle_t h = make_handle_from_claim(dst);
        write32(h, 0xdead_beef);
        write32(make_handle_from_handle(h, 4), 0);
    }
}
```

Use `addr_claim_s` (opaque) when the tool should pick the address; `transparent_addr_claim_s`
in a transparent space when you must constrain `addr` at solve time.

## Checks before you call it done

- [ ] Exactly **one** offset scheme per group.
- [ ] `set_handle()` called once, on the **top-level** group, from an init exec.
- [ ] Register access only from `body` / `run_start` / `run_end`.
- [ ] Region add functions only from `init_down` / `init_up`.
- [ ] MMIO added with `add_nonallocatable_region()`.
- [ ] Packed struct contains only packable types; enums have a base type.
- [ ] Endianness stated if the target is big-endian.
- [ ] No `extend` on `reg_c` / `reg_group_c`, and no fields added to a `packed_s`.
- [ ] No read on a `WRITEONLY` register; no write or read-modify-write on a `READONLY` one
      (`write_field` and `write_masked` count as reads).
- [ ] `write_field`/`write_fields`: string **literals**, top-level non-aggregate names, unique.
- [ ] Every element covered by the offset function — a stray `default: return -1;` produces a
      wrong address, not an error.
- [ ] `addr_value_solve()` / `addr_value_abs()` called only from `pre_body`.

## Common failures

| Symptom | Cause |
|---|---|
| access goes to the wrong address | an element missing from the offset function; or nested `set_handle()` |
| tool rejects a register call | it is a `target` function in a solve exec |
| register layout wrong | field order, or `packed_s<>` defaulting to LITTLE_ENDIAN on a big-endian target |
| allocator hands out MMIO addresses | region added with `add_region()` instead of the non-allocatable form |
| `addr` can't be constrained | opaque claim — use a transparent claim in a transparent space |
| undefined address at solve time | `addr_value_solve()` called outside `pre_body` |

## See also

- `../lang/platform/04-registers.md` — the full register model, including symbolic names (3.1).
- `../lang/platform/03-address-spaces.md` — spaces, regions, claims, handles, access operations.
- `../lang/structural/02-components.md` — `pure component` restrictions.
- `../../examples/regs_and_mem.pss`.
