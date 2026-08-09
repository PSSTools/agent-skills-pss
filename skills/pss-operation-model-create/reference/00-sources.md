# Stage 0 — establish your sources

Before deriving anything, know what you are deriving *from* and what each source can be trusted for.
This takes five minutes and it prevents the two most expensive kinds of rework: building an
operation the device does not have, and absorbing the testbench's conveniences into the device.

## The rule

> **The spec proposes, the RTL disposes, the testbench witnesses.**

| Source | Authoritative for | Characteristic failure |
|---|---|---|
| **Specification** (datasheet, programming guide, register tables) | *Intent.* What operations are meant to exist, register semantics, legal programming order, completion contracts, what the device is **for** | Describes behaviour the RTL does not implement. Omits ordering it silently assumes. A field marked "reserved" that is actually load-bearing |
| **RTL** | *Existence.* Ports and their directions, registers, reset values, **which bits are destructive on read**, what is unimplemented or tied off | States what happens, never what was intended. An accident of implementation reads exactly like a contract |
| **Existing testbench / driver / firmware** | *Practice.* The init sequence that actually works, the undocumented wait, the write that must come second, the delay someone added for a reason | Encodes its own environment's conveniences — backdoors, hard-coded system addresses, hierarchical references. Those belong to the testbench operation model, not the device's |

Only the RTL can be **complete** about interfaces: a spec omits pins, and a testbench connects only
the ones it needed. Only the spec can tell you what an operation is *for*. Only the testbench can
prove any sequence works. You need all three for different stages, and none of them substitutes for
another.

## Record disagreements — do not silently resolve them

When two sources disagree, that is a **finding**, and it goes in a list you keep. It is not a
discrepancy to be settled in favour of whichever you read last.

Findings are how a model earns its review. Most of the interesting decisions in a mature operation
model started as a line in this list: an operation the spec describes that the RTL cannot do, a
register the driver programs that the spec never mentions, an ordering constraint nobody documented.

A finding is worth recording when it changes any of:

- whether an operation exists at all;
- what an operation's completion contract is;
- what a caller is allowed to do (poll twice? call from two threads?);
- which model owns an interface.

Everything else is noise — do not turn this into a spec-diff exercise.

## Working with fewer than three sources

You will rarely have all three. Each absence removes a specific capability, and the honest move is
to name what you have lost rather than to proceed as if it did not matter.

| Missing | What you lose | What to do instead |
|---|---|---|
| **RTL** | Destructive-read analysis (stage 6). You cannot tell a read-to-clear status bit from a level one | **Assume destructive and guard.** Say so in the source, so it can be relaxed when RTL appears. The cost of an unnecessary guard is small; the cost of a missing one is a status that vanishes |
| **Spec** | The anchor for operation granularity. Without it, operations drift toward register wrappers | Derive candidates from the testbench's *sequences*, not its tasks — a sequence is closer to an intent. Mark every operation provisional |
| **Testbench** | Any witness that a sequence works | Expect the first bring-up to change the model. Do not treat the first draft as reviewed |
| **Everything but a spec** | Nothing is checkable | This is still workable — most operation models start here. Every stage still runs; the findings list is just empty and the confidence is lower |

## Before moving on

Write down, in one short block that stays with the model:

- which sources you have, with versions (a spec revision, an RTL commit);
- which of the three roles above is unfilled;
- anything you have assumed because a source was missing.

The last line matters most. An assumption that is written down gets revisited; one that is not
becomes indistinguishable from a fact within a week.

→ Next: `01-interfaces.md`
