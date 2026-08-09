---
name: pss-operation-model-create
description: Derive a PSS operation model from a device specification, RTL, and/or an existing
  testbench — inventory the physical interfaces and project them onto the logical interfaces a system
  will actually have once the device is integrated, identify the operations at the right granularity,
  classify them as configuration or end-to-end, determine each completion contract, decompose the
  end-to-end ones into an unconditional start/check API plus a gated blocking wrapper, and design a
  notification scheme for every event a blocking operation waits on. Use when starting a new PSS
  operation model, when deciding whether something is an operation, when deciding what belongs to
  the device versus the environment or the testbench, when working out what a blocked operation
  should wait on, or when reviewing an operation model's shape.
---

# Creating a PSS operation model

This skill answers **"what can this device be asked to do, and how do I find out?"**

It is a *derivation procedure*, not a language reference. Its inputs are things that are not PSS — a
datasheet, an RTL tree, an existing testbench — and its output is a component tree of operations
that a PSS scenario, a UVM sequence, a C driver and post-silicon test can all call.

| Skill | Answers |
|---|---|
| `pss-language-ref` | *What does this construct mean? Is this legal PSS?* |
| `pss-coding-guidelines` | *Which file does this element go in?* |
| `pss-register-model-create` | *What registers exist?* — the model this one programs against |
| **this skill** | ***What operations exist, and what is their contract?*** |

---

## What an operation model is

Not a testbench, and not a register model. It is the set of **operations a system can initiate
against a device**, as PSS functions on a component tree, with three properties:

1. **One operation is one thing the device can be asked to do.** Not one register write, and not a
   whole test. `transfer_single()` is an operation; "write CH0_CSR.CH_EN" is not, and "copy a buffer
   and check it" is not.
2. **The register model is private.** Nothing outside the component tree names a register. A
   consumer sees operations and data types.
3. **Every consumer gets the same object.** A PSS scenario, a UVM sequence, a C driver and
   post-silicon test all want "start a transfer and tell me when it finished". They differ only in
   what a register access means and what "wait" means.

Property 3 is the whole point, and **every step below exists because skipping it produces a model
that works for one consumer and silently fails to transfer.** When a judgement call is close, that
is the tie-breaker.

---

## The procedure

Each stage closes questions the next depends on. Work them in order.

```
   0. establish your sources             reference/00-sources.md
            │       ← what spec / RTL / testbench each are authoritative for
   1. physical interface inventory       reference/01-interfaces.md
   2. project onto logical interfaces    reference/01-interfaces.md
            │       ← tiers; which operation model owns each interface
   3. get a register model               → skill: pss-register-model-create
            │       ← and bring back the destructive-read facts
   4. identify candidate operations      reference/02-operations.md
            │       ← granularity, naming, anti-patterns
   5. classify each one                  reference/03-classify.md
   6. state each completion contract     reference/03-classify.md
            │       ← destructive? ⇒ the in-progress guard is mandatory
   7. split into the two API levels      reference/04-api-levels.md
            │       ← start_<op> + check_<op>, then the blocking wrapper
   8. design a notification scheme       reference/05-notification.md
            │       ← per event. THIS IS WHERE MODELS GO WRONG
   9. data types and component tree      reference/06-structure.md
  10. write, then verify                 reference/07-verify.md
            │       ← + pss-coding-guidelines for layout
  11. review                             checklists/review.md
```

A complete worked example — the OpenCores WISHBONE DMA specification turning into a real PSS model,
with every judgement call and both negative results shown — is in
**`examples/wb-dma-walkthrough.md`**.

---

## The three ideas that carry the rest

Read these now; the reference pages assume them.

### 1. Interfaces first, operations second

Almost every way an operation model fails to transfer is an interface mistake that has already been
made by the time anyone argues about operations: an operation callable only because the testbench
has a backdoor; one that waits on an interrupt in a system that never routed one; one belonging to a
*different* device, absorbed because the testbench drove both.

```
    physical interfaces      →   logical interfaces       →   operations
    (what the RTL has)           (what the integrated         (what the system can
                                  system can reach)            ask the device to do)
```

So stages 1–2 come before stage 4, and they ask one question of every interface: *will the system
executing this test still have this once the device is integrated?*

### 2. The API layering is fixed — it is not a per-device choice

Blocking versus polling is **not** something you decide per device. Every end-to-end operation has
both APIs, in this relationship:

```
    NON-BLOCKING  (unconditional — every profile, every target)
        start_<op>(args)          initiate: claim, program, arm
        check_<op>() -> status    one probe of the completion condition, decoded

    BLOCKING  (gated on a capability flag)
        <op>(args) {
            start_<op>(args);
            while (check_<op>() == PENDING) wait_related_event();
        }
```

Three consequences:

- **A target without a blocking runtime is not a degraded case.** It is the base case, consuming the
  level every target has. Bare-metal firmware, a boot ROM, an ISR — all of them get a complete API.
- **The blocking wrapper adds only the loop.** Any register access or device-specific decision in
  `<op>()` belongs in `start_<op>()`. This is what makes one simulation regression cover both: the
  simulator executes the non-blocking core *because it is the body of what the simulator runs*.
- **`wait_related_event()` is the only platform-dependent line in the model.** Everything else — the
  programming, the decode, the guard — is portable by construction.

So the real question a device poses is never "blocking or polling". It is *what does
`wait_related_event()` do here*, which is stage 8.

### 3. A missing event-delivery path is an error, not a design case

If you cannot establish how an event reaches a blocked caller, **stop and ask.** It means the event
routing is not yet understood, and the output for that event is a question, not code.

Never substitute on your own initiative:

- **not** a poll loop inside the model — a spin consumes zero simulation time, so it hangs the
  simulator rather than waiting in it;
- **not** a timed backoff — legitimate, but only when the user asks for it, because it silently
  changes the model's platform requirements.

Stopping is cheap: the non-blocking API is unaffected and completes in full. Only the blocking
wrapper for that one operation waits on the answer. See `reference/05-notification.md`.

---

## Naming

Use these names. They are what the procedure's shape is *for*, and consistency across devices is
most of a skill's value to someone reading a model they did not write.

| Element | Name |
|---|---|
| initiate half | `start_<op>` |
| public poll | `check_<op>`, or `check_completion` when one condition serves every operation |
| internal decode, no guard | `probe_<subject>` |
| blocking loop for a subject | `wait_<subject>`, or `wait_completion` |
| the one platform-dependent line | `wait_related_event` |
| notification entry point | `notify_<event>` |
| capability flag | `<DEV>_HAS_BLOCKING` |

`start_<op>` reads as half of a pair, which is what it is, and sorts next to `check_<op>`.

---

## After you have a model

Verify the **generated output**, not the exit status: an exit status reports whether a step ran, not
what it produced. A model can elaborate cleanly and still reach the output with operations missing.
`reference/07-verify.md` gives the tiers and what each one does and does not establish.
