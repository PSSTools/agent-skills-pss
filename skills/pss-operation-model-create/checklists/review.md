# Review checklist — operation model

A pre-flight pass before calling an operation model done. Each line has a stage that explains it.

## Sources (stage 0)

- [ ] Sources named, with versions, and stored with the model
- [ ] Anything assumed because a source was missing is written down as an assumption
- [ ] Findings list exists: every place two sources disagreed, and what was decided

## Interfaces (stages 1–2)

- [ ] Every RTL port group appears in the inventory, with its direction of initiation
- [ ] No initiator port has been turned into an API — it produced an address-space requirement instead
- [ ] Every interface has a tier (A / B / C) and an owning model (device / peer / testbench)
- [ ] **Platform-requirements list exists**: every Tier B item, phrased as something an integrator supplies
- [ ] No Tier C dependency anywhere in the device tree
- [ ] Interfaces that produced *no* operations are recorded as rows with reasons, not omitted silently
- [ ] Peer interfaces are named as gaps or handed to the peer's model — not absorbed

## Operations (stage 4)

- [ ] Every operation passes all four granularity tests
- [ ] No register-wrapper operations
- [ ] No test-shaped or intent-named operations
- [ ] No index argument where a component per subject would work
- [ ] No system addresses inside the device tree
- [ ] No operation returns a raw device status for the caller to decode
- [ ] Every register in the map is either programmed by some operation or recorded as unused

## Contracts (stages 5–6)

- [ ] Every operation is classified: configuration / end-to-end / environment entry point
- [ ] Every end-to-end operation states its completion condition, naming the register and bits
- [ ] **Destructiveness answered per bit**, from RTL or an access-class marker — not assumed silently
- [ ] Destructive ⇒ the in-progress guard is present, and claims before the first register write
- [ ] Guard violations report loudly and return PENDING, never ERROR
- [ ] Status enum is three-valued, with PENDING appended rather than inserted
- [ ] ERROR is decoded before DONE where both can be set

## API levels (stage 7)

- [ ] `start_<op>` and `check_<op>` exist for every end-to-end operation, ungated
- [ ] `<op>()` is two lines — no register access, no address arithmetic, no device decision
- [ ] `wait_<subject>()` contains no device access except through `probe`
- [ ] Gating covers exactly: `wait_*`, `<op>`, end-to-end actions, `notify_*` — and nothing else
- [ ] The capability flag is asserted in the scenario layer, not in the device tree
- [ ] Aborts claim no token and do not call `wait_<subject>()`
- [ ] Non-terminating operations are documented on `start_<op>`, where both levels' readers see it

## Notification (stage 8)

- [ ] Every event surface from stage 2 has a scheme, all nine fields filled in
- [ ] **No scheme has a guessed field 3.** Unestablished ⇒ it was raised as a question, not coded around
- [ ] No poll loop and no timed backoff was introduced without the user asking for it
- [ ] Wake objects are depth-1 channels, not flags
- [ ] Notifications post blind — nothing reads the event in order to route the event
- [ ] `notify_<event>` uses `try_put`, and its prunability is noted at its definition
- [ ] Field 6 recorded: which configuration operation enables the event
- [ ] **Correspondence table complete**: every event that can advance a subject wakes that subject

## Structure (stage 9)

- [ ] The device tree has no `pss_top` and elaborates on its own
- [ ] Subjects are component instances, not indices
- [ ] Each operation file states its completion contract and the decisions that shaped it
- [ ] Layout follows `pss-coding-guidelines`

## Verification (stage 10)

- [ ] Elaborates
- [ ] **The generated output was searched for the operations** — exit status alone was not accepted
- [ ] Correspondence table reviewed by a person
- [ ] Bus trace compared against a known-good sequence, if one exists — differences justified individually
- [ ] Non-blocking level elaborates, in CI
- [ ] When reporting results, what the regression does *not* cover was stated
