# Stages 1–2 — the interface inventory

The load-bearing stage. Everything downstream is shaped by what you conclude here, and mistakes made
here do not look like interface mistakes later — they look like an operation that mysteriously does
not work on someone else's platform.

Two passes: **what exists** (stage 1), then **what survives integration** (stage 2).

---

## Stage 1 — physical inventory

Enumerate from the **RTL port list**, because it is the only source that can be complete.

For each port group record four things:

| Column | Note |
|---|---|
| Name | The group, not the pin. `wb slave (cfg)`, not `wb_cfg_adr_i` |
| Protocol | WISHBONE, AXI, APB, pin-level, level-sensitive line |
| **Direction of initiation** | Does the device *initiate* transactions on this interface, or *respond* to them? |
| Peer | Who is at the other end — and is it the CPU running the test, memory, or another device? |

**Direction of initiation is the column that does the work.** It sorts every port into exactly three
roles, and those roles are what an operation model is made of:

| Device is… | Role | Becomes |
|---|---|---|
| **responder** — a register/config slave | **control surface** | The operation model's primary surface: the register model, and every access inside an operation body |
| **initiator** — a data master | **consequence surface** | **Not callable.** Becomes an *address-space requirement* ("the device must be able to reach these buffers") and a *check* surface |
| **out-of-band** — an interrupt line, handshake pins, a status output | **event surface** | The input to a notification scheme (stage 8): what a blocked caller waits on, and who wakes it |

### The error this prevents

Treating an initiator port as an operation surface. *"The DMA can write memory"* is not an
operation — it is what the transfer operation **causes**. There is no API on that port, because the
system does not drive it; the device does.

What the model needs from an initiator port is the **address-space claim**: which spaces the device
can reach, and therefore which buffers a caller may legally hand it. That claim is a constraint on
the operation's arguments, not a function.

Clock and reset are not interfaces for this purpose. Note them and move on.

### Template

```
| Port group | Protocol | Device… | Peer | Role |
|---|---|---|---|---|
|            |          | responds / initiates / drives | | control / consequence / event |
```

---

## Stage 2 — logical projection

Now ask, of every interface: **can the software that will call this model reach it, on every target
the model claims to support?**

Three answers, and the answer decides where the interface's consequences may appear.

| Tier | Meaning | Where it may appear |
|---|---|---|
| **A — universal** | Reachable by any caller in any integration: MMIO through the register port; memory in an address space shared with the device | Freely. **Operation bodies are made of Tier A and nothing else.** |
| **B — contracted** | Reachable only if the platform supplies something: an interrupt routed to the calling core, a DMA-reachable buffer allocator, a peer that answers a handshake | Only behind an explicit, named contract — a foreign-function prototype, a notification entry point, a documented platform requirement. **Every Tier B item goes in the model's "what an integrator must provide" list.** |
| **C — simulation-only** | Backdoor memory access, `force`, a monitor's internal state, a config-db lookup, a hierarchical reference | Not in the device model. These belong one level up (below) |

Tier B is the tier that needs discipline. It is not a warning label — plenty of good models depend on
Tier B interfaces — but an undeclared Tier B dependency is exactly the thing that works in the
environment it was written in and nowhere else. The declaration is what makes it portable: an
integrator who reads the requirements list can satisfy it or reject the model, and either is better
than discovering it at bring-up.

## There is more than one operation model

The tiering does not sort interfaces into "real" and "not real". It sorts them by **which operation
model owns them**:

| Operation model | Covers | Built from |
|---|---|---|
| **Device** | one device — the deliverable an integrator picks up | its Tier A control surface, plus its own declared Tier B contracts |
| **Peer element** | another element on a shared interface: a peripheral answering a handshake, a companion IP | that element's own surfaces |
| **Testbench** | the assembled environment | **composes** the device models of every element, and adds the Tier C surfaces only it has |

So a Tier C interface is not a mistake to exclude — it is a surface belonging to a model one level
up, where it is entirely legitimate. The same holds for a peer's interface: it belongs to the peer's
model, and if that model does not exist yet, **name the gap rather than absorbing the content**. A
device model that grows its peer's operations is the single most common way a "device" model turns
out to be a testbench.

This is also what makes the device/environment split a derivation rather than a judgement call. Each
interface goes to whichever model owns it, and the device model is what remains once the peer and
testbench surfaces have been assigned elsewhere.

### Template

```
| Interface | Tier | Reachable how | Owning model |
|---|---|---|---|
|           | A/B/C |              | device / peer <name> / testbench |
```

## Two outputs to carry forward

1. **The platform-requirements list** — every Tier B item, phrased as something an integrator
   supplies. This is a deliverable, not a note; it is the contract the model ships with.
2. **The event surfaces** — every interface whose role is "event". Each one needs a notification
   scheme in stage 8, and stage 8 will refuse to proceed on any that cannot be established.

## Interfaces that turn out to be dead ends

Recording a *negative* result is worth as much as recording an operation, and it is cheap — one row.
Two shapes recur:

- **Tier B with no satisfiable contract.** A pass-through or bridge path that only means anything
  when there is a target on the far side. If nothing in any planned integration provides it, the
  operations behind it are **omitted**, with the reason written down.
- **A surface whose peer is the initiator.** Whatever is on the other end drives it; this device
  responds. Those operations belong to the peer's model.

Both look like missing functionality to a later reader unless the reason is recorded. Write the row.

→ Next: stage 3 hands off to **`pss-register-model-create`**, then `02-operations.md`.
