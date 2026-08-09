# Worked example — the OpenCores WISHBONE DMA/Bridge

The procedure run end to end against a real specification (`dma_doc.md`, Rev. 1.5), with the
judgement calls shown. Three operations are worked in full; everything else is one row, because a
row is enough to show how the stage decided.

**Sources for this run:** specification only. No RTL, no existing testbench — which is the common
starting position, and stage 0 says what that costs.

---

## Stage 0 — sources

| Have | Missing | Consequence |
|---|---|---|
| Spec, Rev. 1.5 | RTL | Destructiveness must come from the spec's access-class column. It turns out to be there (stage 6) — but had it not been, the rule is *assume destructive and guard* |
| | Testbench | No witness that any sequence works. First bring-up may change the model |

## Stage 1 — physical inventory

| Port group | Protocol | Device… | Peer | Role |
|---|---|---|---|---|
| WB interface 0 — slave | WISHBONE B | responds | host / fabric | **control** (register file) |
| WB interface 0 — master | WISHBONE B | initiates | memory | **consequence** |
| WB interface 1 — slave | WISHBONE B | responds | host / fabric | control (bridge path) |
| WB interface 1 — master | WISHBONE B | initiates | memory | **consequence** |
| `inta_o`, `intb_o` | level | drives | interrupt controller | **event** |
| `dma_req_i`, `dma_ack_o`, `dma_nd_i`, `dma_rest_i` × ch | pins | responds | requesting peripheral | **event** (peer-initiated) |

Both WISHBONE interfaces are master- *and* slave-capable (§2.1), which is why each appears twice.
That is not pedantry: the slave halves and master halves get different tiers and end up in different
models.

## Stage 2 — logical projection

| Interface | Tier | Reachable how | Owning model |
|---|---|---|---|
| WB0 slave (registers) | A | MMIO load/store | **device** — the register model |
| WB0/WB1 master (data) | A\* | not callable | **device** — address-space requirement + check surface |
| `inta_o` / `intb_o` | B | environment observes and calls in | **device** — notification entry point at the seam |
| `dma_req_i` / `ack` / `nd` / `rest` | B | the requesting peripheral drives them | **peer's model** — not this device |
| WB1 slave → WB0 master (bridge, §1) | B | needs a WISHBONE target on the far interface | **omitted** — no satisfiable contract |

\* Tier A in that no platform *service* is needed, but it is not a callable surface at all. What it
yields is the claim *"the device must be able to reach the buffers a caller hands it"* — a constraint
on operation arguments, not a function. This is the row that stops "the DMA can write memory" from
becoming an operation.

**Two negative results, both from this stage:**

- **The hardware handshake goes to the peer.** The peripheral asserts `dma_req_i`; the DMA
  acknowledges. The initiator is the *requesting device*, so `request_chunk`,
  `skip_to_next_descriptor` and `restart_transfer` are operations of **that** device's model. Absorb
  them here and this stops being a DMA model and becomes a two-device testbench model.
- **The bridge path is omitted.** Pass-through only means something when a master on one interface
  targets a slave on the other. Nothing in the planned integration provides that, so the operations
  behind it do not exist. Recorded, not silently dropped.

**Platform-requirements list** (the Tier B contract this model ships with):

1. An interrupt observer on `inta_o`/`intb_o` that calls `notify_irq()`.
2. Buffers reachable by the device's WISHBONE master(s).
3. If the handshake is used, a peer model that drives it.

## Stage 3 — register model

Handed to **`pss-register-model-create`**, which produced `wb_dma_regs_pkg` from §4 of the spec:
engine-global bank at `+0x00` (CSR, INT_MSK_A/B, INT_SRC_A/B), per-channel banks at `+0x20 + n*0x20`
(CHn_CSR, SZ, A0, AM0, A1, AM1, DESC, SWPTR).

What comes back that this skill needs — the facts with no PSS construct to land in:

| CHn_CSR | Access | Matters because |
|---|---|---|
| 22, 21, 20 — interrupt sources (chunk / done / error) | **ROC** | read-to-clear |
| 12 — ERR | **ROC** | read-to-clear |
| 11 — DONE | RO | **survives a read** |
| 10 — BUSY | RO | survives |

## Stage 4 — candidate operations

From the spec's procedure prose (§3.2–§3.10), not from the register map:

`configure_channel`, `transfer_single`, `transfer_list`, `stop_channel`, `set_auto_restart`,
`set_software_pointer`, `pause_engine`, `configure_interrupt_routing`, `write_descriptor`,
`read_descriptor_residual`.

Granularity notes: "set CH_EN" did not survive test 1 — it is a register wrapper, and it merged into
`transfer_single`. Channel number is **not** an argument (test/anti-pattern: index argument); the
channel becomes a component, per stage 9.

## Stages 5–6 — classify and contract

| Operation | Kind | Completion condition |
|---|---|---|
| `transfer_single` | **end-to-end** | CHn_CSR DONE / ERR |
| `transfer_list` | **end-to-end** | same |
| `stop_channel` | **end-to-end**, abort shape | same |
| `configure_channel`, `set_auto_restart`, `set_software_pointer` | configuration | — |
| `pause_engine`, `configure_interrupt_routing`, `write_descriptor`, `read_descriptor_residual` | configuration | — |
| `notify_irq` | environment entry point | — |

One condition serves all three end-to-end operations, so there is one `probe_status()` and one
`wait_completion()` — named for the **subject** (the channel), not the operation.

**Destructiveness — the finding that shapes everything downstream.** The spec's §4 preamble says it
in one sentence that is easy to skim:

> *"A 'C' appended to RW or RO indicates that some or all of the bits are cleared after a read."*

CHn_CSR is **mixed**: ERR and the three interrupt-source bits are `ROC`; DONE and BUSY are plain
`RO`. So a second read after a failure sees ERR cleared and DONE still zero — and answers **PENDING
forever**. The guard is mandatory, and this is exactly the hazard `03-classify.md` describes.

**A §10.2 case, straight from the spec.** CHn_CSR bit 11: *"This bit will not be set unless the ARS
bit is cleared."* So `transfer_single` on an auto-restarting channel **never completes** — blocking,
it never returns; polling, it is a loop that never exits. The note belongs on `start_transfer_single`,
where both levels' readers will see it.

## Stage 7 — API levels

```
start_transfer_single(cfg)     unconditional
probe_status()                 unconditional   one CSR read -> wb_dma_status_e
check_completion()             unconditional   guard + probe
wait_completion()              gated           loop + guard release
transfer_single(cfg)           gated           start + wait; two lines
```

`stop_channel` takes the abort shape: it claims no token (the channel already holds one), and it
gets its own loop over `probe_status()` rather than calling `wait_completion()` — which would
release the *transfer's* token.

## Stage 8 — notification scheme

One event surface, so one scheme.

| # | | |
|---|---|---|
| 1 | Event | Channel done / error / chunk transferred |
| 2 | Origin | CHn_CSR 22:20, gated by INE_* (19:17), aggregated through INT_SRC_A/B and INT_MSK_A/B to `inta_o`/`intb_o` |
| 3 | Delivery | Environment's interrupt monitor calls `notify_irq()` — **established**, it is requirement 1 |
| 4 | Object | `channel_c<bit,1> wake`, one per channel |
| 5 | Routing | **Blind, to all channels.** INT_SRC_A is itself read-clear — routing by reading it would consume the state the waiters need |
| 6 | Enablement | **Two levels, both required:** per-channel INE_DONE/INE_ERR in CHn_CSR (`configure_channel`) *and* the channel's bit in INT_MSK_A/B (`configure_interrupt_routing`) |
| 7 | Lost wakeup | None — the channel is the registration; the loop probes before it waits |
| 8 | Gap | None; field 3 established |
| 9 | Signature | First end-to-end operation never returns ⇒ check INT_MSK_A/B **before** the device |

Field 6 is the payoff for asking. A configuration operation is now a hard precondition for a
blocking operation on a *different* component ever returning — a coupling that is invisible in both
operations' own code and would otherwise be discovered as a hang.

**Correspondence check:**

| Subject | Woken by | Can also be advanced by | Covered? |
|---|---|---|---|
| `ch[i]` | any interrupt, posted blind | done, error, chunk-done — all on the same aggregated line | ✅ |

Chunk-done makes most wakes spurious, which is why the loop is wake-and-recheck rather than a single
suspend (§10.4). It is free here, and it is *why* blind posting costs nothing.

## Stage 9 — structure

Component per channel, not a `chan` argument, so every access in an operation body is index-free —
`regs.csr.read()`. Each `wb_dma_ch_c` binds its own register group at `BASE + 0x20 + i*0x20`, and
holds its own `inflight` and `wake`. The device tree has no `pss_top`: the base address and system
RAM belong to the integration.

---

## Grading the run against `src/pss`

The model in `src/pss` was built independently. What the procedure reproduced:

✅ `notify_irq()` posting blind to all four channels, with the "never read the event to route the
event" reasoning · ✅ depth-1 `wake` per channel · ✅ the in-progress guard, from the read-clear
finding · ✅ one `probe_status` / `check_completion` shared by all three operations · ✅
`configure_interrupt_routing` as a precondition for any end-to-end operation to complete · ✅
`stop_channel` as an abort with its own loop · ✅ the handshake in the environment · ✅ the bridge
omitted · ✅ component-per-channel.

**Three differences, all of them the skill's convention rather than the model's error:**

| `src/pss` | This skill | Why |
|---|---|---|
| `transfer_single_start` | `start_transfer_single` | Prefix sorts and greps with `check_*`. Cosmetic; pick one and hold it |
| `wait_completion()` inlines `wake.get()` | a separate `wait_related_event()` | Makes the platform seam the single greppable thing an integrator reimplements |
| gated functions grouped in `blocking_ops.pss` | one file each | The grouping is defensible — they appear and disappear together — but it costs you finding `<op>` by looking for `<op>.pss` |

**One thing the spec-only run could not produce:** `read_descriptor_residual` depends on SZ_WB
write-back behaviour that the spec describes only in prose (§3.9). Stage 0 predicted this shape of
gap — without RTL or a testbench, an operation whose contract lives in prose stays provisional.
