# Stage 10 — verify, and claim only what you checked

A clean parse means the names resolve and the braces match. It does not mean the model is right, and
an operation model has specific ways of being wrong that no parser sees.

## The tiers

Work down. Each establishes something the one above does not.

| Tier | Establishes | Does **not** establish |
|---|---|---|
| 1. Elaborates | Names resolve; the tree builds | That any operation survived into the output |
| 2. **The generated output contains the operations** | The model was not silently dropped | That any of it does anything |
| 3. Correspondence table reviewed (stage 8) | No operation can block on something nothing wakes | That the environment actually delivers the notification |
| 4. Runs against the DUT | The sequences execute | That they match what the device expects |
| 5. **Bus trace matches a known-good sequence** | The model programs the device the way the reference does | Anything about the polling consumer's own loop |
| 6. Non-blocking level elaborates | The gating is consistent; the core has no reference into the blocking layer | Anything about behaviour |

## Tier 2 — the one people skip

> **An exit status reports whether a step ran, not what it produced.**

A model can elaborate cleanly and still reach the generated output with operations missing — dropped
as unreferenced, gated out by a flag you did not mean to set, or never generated at all. None of
those changes an exit status.

So look in the output. Search it for the operations that should be there. This is worth doing
against a perfect toolchain; it just happens to also catch an imperfect one.

## Tier 3 — a review step, and nothing can automate it

No tool knows which physical events can change a status register's value, so the correspondence
table from stage 8 has to be checked by a person.

It is worth the effort because its failure mode is the worst one available: a blocking operation
that never returns, in a model that passes tiers 1, 2 and 6. Pre-print the most common cause on the
table — **the event was never enabled**, because the device-side routing or mask register was not
programmed, so the environment had nothing to observe.

## Tier 5 — the check that closes the loop

If an existing testbench or driver was one of your sources, it is also your **reference**. Compare
the bus traffic your model produces against what the known-good sequence produces.

This is the only tier that verifies the chain from "the spec says" back to "the device agrees".
Everything above it verifies that the model is internally consistent with your reading of the spec —
which is exactly the thing that might be wrong.

Diff the transactions, not the waveform: address, direction, data, order. Expect differences you
must then justify one at a time; a masked write that reads first is not a discrepancy, and an extra
status read at the top of an operation is usually the stale-token probe doing its job.

## Tier 6 — cheap, and it stops the gating from rotting

Elaborating the non-blocking level needs no simulation. It is what catches a core that has quietly
grown a reference into the blocking layer, which is otherwise invisible until someone tries to build
for a target that has no scheduler.

Wire it into CI. It is the least expensive check in this list.

## What a blocking regression does *not* cover

State this honestly when reporting results, because the "one regression covers both levels" claim is
load-bearing and is not unconditional.

A blocking simulation exercises the non-blocking core's **device interaction** — the register
writes, their order, the completion decode, the guard transitions. It does **not** exercise:

- the polling consumer's own loop, or what it does between polls;
- any backoff, timeout or scheduling wrapped around `check_<op>()`;
- the non-blocking level's *build* — that is tier 6, and it is separate for a reason.

The first two are the consumer's concerns and belong to the consumer's own tests. Say so rather than
implying the model's regression covers them.

→ Finally: `../checklists/review.md`
