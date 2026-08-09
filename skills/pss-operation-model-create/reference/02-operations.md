# Stage 4 — identify the operations

You have the control surface (stage 2) and a register model (stage 3). Now: what are the operations?

This is the hardest judgement in the procedure, because both failure directions feel natural while
you are making them. Too fine and you have written a register model with longer names; too coarse
and you have written one test.

## Where candidates come from

| Source | What to pull |
|---|---|
| **Spec** | The verbs in the prose. "The channel is started by…", "to use external descriptors…, then…". A spec's *procedure* paragraphs are operation descriptions written in English |
| **Testbench / driver** | Its **sequences**, not its tasks. A task is often one register write; a sequence is usually closer to an intent |
| **Register map** | Only as a cross-check at the end: is there a register nothing programs? Either an operation is missing or the register is not used |

Do not start from the register map. It produces one operation per register, every time.

## The four tests

Apply in order to every candidate.

**1. Would a driver author name a function this?**

`transfer_single` yes. `set_csr` no — that is a register wrapper. `copy_and_check` no — that is a
test.

**2. Does it leave the device in a state a consumer can reason about?**

If the operation returns with the device half-programmed — armed but not enabled, configured but
with a mode bit still unset — it is a *fragment*. Fragments must be merged into whatever completes
them. The test is whether you could hand the device to another caller at that moment and describe
its state in one sentence.

**3. Is it named for the device's capability, or for one test's intent?**

Intent-named operations do not transfer, and that is the whole failure mode this procedure exists to
prevent. `transfer_single` is a capability. `warm_up_the_fifo_before_the_error_test` is an intent.
If the name contains a *reason*, it is a scenario.

**4. Would two consumers with different goals both call it?**

If only one would, it is a scenario built out of operations, not an operation.

## Anti-patterns

| Anti-pattern | Looks like | Repair |
|---|---|---|
| **Register wrapper** | `set_ch_en()`, `write_control(v)`, one per field | Merge into the operation that has a reason to set it. If no operation wants it, you have found a register nothing uses — a finding |
| **Test-shaped operation** | `test_mem_to_mem()`, `run_error_case()` | That is a scenario. Split into the operations it performs; the scenario stays in the test layer |
| **Index argument** | `transfer(int chan, …)` on a device with N identical channels | Make the channel a **component instance**, so every register access inside the body is index-free. See `06-structure.md` |
| **System address baked in** | An operation that knows where the device sits, or where RAM is | Those are the *system's* facts. They belong to the environment's assembly, passed in at elaboration |
| **Absorbed peer operation** | An operation that drives an interface this device responds to | It belongs to the peer's operation model (`01-interfaces.md`) |
| **Operation returning device internals** | Returning a raw status word for the caller to decode | Decode it. A consumer must not need the register map — that is property 2 of an operation model |

## Arguments

An operation's arguments are the things a *caller* legitimately varies. Two rules:

- **Group related arguments into a config struct** once there are more than about three, and name it
  for the thing being configured. A struct also gives constraints somewhere to live.
- **An argument that always takes the same value is not an argument.** It is a decision the model
  should make. Ask why the caller would ever change it; if there is no answer, remove it.

Addresses passed in as arguments are normal and correct — *system* addresses (where the device is,
where RAM starts) are not arguments, they are elaboration-time facts.

## Naming

Keep the name the specification gives the capability. Where a spec name is genuinely bad or
ambiguous, rename — and record it as a finding, so a reader with the spec open can follow.

Prefer symmetry across an operation family: if you have `transfer_single`, the list form is
`transfer_list`, not `run_descriptor_chain`. Symmetric names make the family visible in a directory
listing, which is most of how someone navigates a model they did not write.

## Output of this stage

A flat list of candidate operations with, for each, one sentence: *what the device is being asked to
do*. No PSS yet, no arguments finalised, no split into start/check.

Resist writing code here. The next two stages will change several of these entries, and one of them
usually deletes one.

→ Next: `03-classify.md`
