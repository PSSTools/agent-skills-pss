# Pre-flight review checklist

Run this **before** declaring PSS done, and **after** any tool check. The items here are
weighted toward tier 3 and tier 4 — the rules no tool will tell you about
(`../reference/tooling.md`).

Report which tiers you actually reached. "It parses" is not "it is correct".

---

## 1. Structure

- [ ] Every `input` / `output` / `lock` / `share` has a **pool of that exact type**, with a
      `bind`. Declaring a pool does not bind it.
- [ ] Pool **placement** gives the intended sharing — per instance vs system-wide.
- [ ] Resource pool sizes are the real counts; array claims fit within them.
- [ ] Every non-abstract action is in a component scope; every compound action only traverses
      actions in its own component or its sub-tree.
- [ ] No action has both an `activity` and an `exec body`.
- [ ] Flow-object kind matches the timing requirement: `buffer` = consumer after producer
      completes; `stream` = exactly one of each, starting together; `state` = one object per pool.
- [ ] Nothing is modelled as a flow object that is really exclusion (or vice versa).

## 2. Ordering

- [ ] Every sequential activity block has a **reason** — otherwise it should be a flow object.
- [ ] `parallel` only where a synchronized **start** is genuinely required.
- [ ] You know which actions **inference** will add, and either want them or used `atomic { }`.
- [ ] Scheduling constraints don't conflict with flow-object or resource requirements, and
      aren't applied to handles traversed in a loop.
- [ ] No reliance on `join_none`/`join_first` implying completion.

## 3. Constraints and randomization

- [ ] Hard constraints are **rules**; preferences are `soft` or `default`; shapes are `dist`.
- [ ] No code relies on a `soft` constraint having held.
- [ ] Every `->` re-read **backwards** — implications are bidirectional.
- [ ] No vacuous constraint (an antecedent that can never be true; a `unique` over an empty
      slice).
- [ ] `rand` appears on every step of the path to each randomized field.
- [ ] `rand list` sizes set in `pre_solve` — they cannot be constrained.
- [ ] No `rand` variable in a `dist` weight or range bound.
- [ ] Nothing written to a `rand` scalar in `pre_solve` and expected to survive.

## 4. Realization

- [ ] Every function called from `body`/`run_start`/`run_end` has a **target** definition; every
      function called from a solve exec has a **solve** definition.
- [ ] `comp.<field>` is never assigned outside `init_down`/`init_up` (unless `mutable`, 3.1).
- [ ] No `rand` declarations in procedural scope.
- [ ] Native functions declare **no** parameter directions; aggregates the callee must not
      mutate are `const`; aggregate-literal and `static const` arguments land on `const`
      parameters.
- [ ] Every `match` has a `default`, or provably covers its domain; arms don't overlap.
- [ ] `foreach` bodies don't write the collection, the index, or the iterator.
- [ ] `pure` only on side-effect-free, non-`void`, output-free functions — **and it is actually
      pure**, because the tool may cache it.
- [ ] Non-`void` calls used as statements are discarded with `(void)f();`.
- [ ] Derived `exec body` / `activity` includes `super;` where the base behaviour must persist.
- [ ] `message()` gets solve-time-known verbosity, format string, and string arguments, and no
      argument with a side effect.
- [ ] Every target polling loop contains a `yield;`.

## 5. Data

- [ ] Widths are deliberate — `bit` is **one bit**.
- [ ] Shifts and `**` widened before the operation, not after (the result takes the left
      operand's type).
- [ ] Mixed-signedness comparisons cast explicitly.
- [ ] Enum defaults are the **first declared** item, and that is the item you wanted.
- [ ] Struct assignment (deep copy) vs native parameter passing (by handle) is understood
      where it matters.
- [ ] Array literals have the exact element count.

## 6. Platform

- [ ] Register groups implement **exactly one** offset scheme.
- [ ] `set_handle()` called once, on the **top-level** group, from an init exec.
- [ ] Every register-group element is covered by the offset function — no silent `-1`.
- [ ] MMIO windows added with `add_nonallocatable_region()`.
- [ ] Region-add and `set_handle` calls only in `init_down`/`init_up`; register and memory access
      only in target execs; `addr_value_solve`/`addr_value_abs` only in `pre_body`.
- [ ] Packed structs contain only packable types; enums in them have a **base type**; endianness
      stated if the target is big-endian; no fields added by extension.
- [ ] No read on a `WRITEONLY` register; no write or read-modify-write on a `READONLY` one.
- [ ] `write_field`/`write_fields`: string literals, top-level non-aggregate names, unique.
- [ ] At most one executor claim anywhere under an action or object.

## 7. Coverage

- [ ] Explicit `bins` on every non-enum coverpoint (auto bins default to 64).
- [ ] Sampled values are solve-resolved, not `exec body` results.
- [ ] Crosses reference coverpoints, not expressions.
- [ ] `illegal_bins` is a check, not a constraint — add the constraint too if it must never be
      generated.
- [ ] Monitors are constrained enough to be meaningful, and you have not assumed a monitor
      generates anything.

## 8. Portability

- [ ] No reliance on anything the standard leaves **unspecified**:
      extension order · sibling `init_down`/`init_up` order · sibling solve-exec order ·
      order among parallel actions exchanging no flow objects · `map`/`set` iteration order ·
      monitor first-match realization selection · float bit-exactness across platforms ·
      reserved register bits beyond the value type.
- [ ] 3.1-only constructs are known and deliberate (`../reference/3.1-deltas.md`) if the target
      tool may be older.
- [ ] Untagged `header`/`declaration` templates that would duplicate are tagged (3.1) or the
      duplication is acceptable.

## 9. Reporting

- [ ] You ran whatever check the environment provides, and you say **which tier** it reached.
- [ ] Any tool rejection of PSS this reference says is legal is **reported**, not worked around.
- [ ] Anything left unverified is stated explicitly.
