# Checker rules: unchecked hazards (heuristics)

Proposed checker `name = "hazards"`. **Tier 4** — these are rules nothing else will catch, but
none of them is a decision procedure. Every rule here:

- ships at **`warning`** severity, never `error`;
- must be **individually disableable**;
- must have a documented suppression idiom, so a deliberate exception is expressible.

A false positive on a stylistic rule costs more trust than the rule is worth. If a rule cannot
be made quiet on correct code, do not ship it.

Reference page for all of these: the *Gotchas* sections tagged *Tier 4* across `../reference/lang/`.

---

## PSL041 — `match` with no `default` arm

| | |
|---|---|
| **Rule** | Exactly one `match` arm must be found. More than one is an error; none, with no `default`, is an error — at runtime. |
| **LRM clause** | §20.7.9 |
| **Tier** | 4 |

**Marker**

```python
MarkerDef(
    id="PSL041",
    severity="warning",
    summary="match statement has no default arm",
    detail=(
        "If no arm matches at runtime and there is no `default`, it is an error -- "
        "and nothing detects it statically. Unless the arms provably cover the "
        "expression's entire domain, add a default arm, even one that only calls "
        "error().\n\n"
        "Suppress by adding a default, or disable this rule if your arms are "
        "exhaustive by construction."
    ),
)
```

**Detection**

For each procedural and activity `match` statement without a `default` arm, attempt to prove
coverage of the selector's domain:

- **enum selector** — union the arms' enum item lists; quiet if every item of the enum (initial
  definition **plus all extensions**) is covered;
- **integer selector with a declared value domain** (`bit[4] in [0..9]`) — union the arms'
  ranges and compare;
- **integer selector with only a width** — compare against `0 .. 2^W-1`; realistically this
  will almost never be provably covered, which is the point;
- **string selector** — never provable; always warn.

Otherwise report.

**False-positive risk**

- **Extensible enums.** An enum covered exhaustively today stops being covered the moment a
  package extends it. That is a real hazard, not a false positive — but it means "exhaustive
  enum" should be quiet only when no extension of that enum exists in the elaborated model.
- Constraints that narrow the value are **not** visible to this rule and cannot be relied on;
  a `match` inside `exec body` may see values the solver never chose.

---

## PSL042 — derived `exec body` does not call `super;`

| | |
|---|---|
| **Rule** | exec blocks are virtual: a derived type's same-kind exec **replaces** the base's. `super;` splices the base behaviour back in. |
| **LRM clause** | §17.1, §20.1.4.2 |
| **Tier** | 4 |

**Marker**

```python
MarkerDef(
    id="PSL042",
    severity="warning",
    summary="Derived exec block replaces the base's without calling super",
    detail=(
        "A derived type's exec block of the same kind fully REPLACES the base "
        "type's -- the base implementation silently stops running. If that is not "
        "what you meant, add `super;` at the point the base behaviour should "
        "occur.\n\n"
        "This is the most damaging inheritance mistake in PSS, because the model "
        "stays legal and the generated test quietly does less."
    ),
)
```

**Detection**

For each type `D` deriving from `B`, for each exec kind `K` where **both** `D` and `B` define a
`K` exec: report if `D`'s exec contains no `super;` statement.

Apply to procedural execs only. **Target-template execs cannot contain `super;`** (§20.5) — skip
them entirely rather than emitting an unfixable warning.

**False-positive risk**

- **Deliberate replacement is legitimate** and common. This rule's value is entirely in the
  cases where it was accidental, and it cannot tell them apart. Hence `warning`, and hence the
  need for a suppression idiom — recommend a recognized comment marker, e.g.
  `// replaces-super`, on the derived exec.
- **Extension execs are additive, not replacing** (§17.2). Do not report `extend`-introduced
  execs.

---

## PSL043 — side effect in a `message()` argument

| | |
|---|---|
| **Rule** | If expressions with side effects, such as non-`pure` function calls, are passed as parameters to `message()`, their evaluation is not guaranteed, because the verbosity level may determine whether they are evaluated. |
| **LRM clause** | §21.1.3 |
| **Tier** | 4 |

**Marker**

```python
MarkerDef(
    id="PSL043",
    severity="warning",
    summary="Possibly side-effecting expression passed to message()",
    detail=(
        "message() arguments may not be evaluated at all: if the run's verbosity "
        "excludes this message, the tool may elide the whole call. An argument "
        "whose evaluation matters will then silently not happen.\n\n"
        "Compute the value into a local first, then pass the local."
    ),
)
```

**Detection**

For each call to `std_pkg::message()`, inspect each argument expression. Report when it contains
a call to a function that is **not** declared `pure`.

Extend the same check to `error()` and `fatal()` only if their arguments are likewise elidable —
they are not verbosity-gated, so the recommendation is to check `message()` only.

**False-positive risk**

- A **non-`pure` function that happens to be side-effect-free** is the common case, and this
  rule cannot know. This is the weakest rule in the set; consider shipping it off by default.
- Core-library query functions (`sizeof_s` members, `addr_value`) — exempt an explicit allowlist.

**Additional related check (same marker family, higher confidence):** `message()`'s verbosity,
format string and **string** arguments must be solve-time known when called from a target exec.
A string argument that is a local assigned from a `target` function call in the same exec is
detectable and is a genuine error, not a heuristic. Consider that a separate `error`-severity
marker rather than folding it in here.

---

## PSL044 — wide coverpoint with no explicit bins

| | |
|---|---|
| **Rule** | If a coverage point defines no bins, the tool creates `min(2^M, auto_bin_max)` bins, where `auto_bin_max` defaults to 64. |
| **LRM clause** | §15.3.4, §15.5 |
| **Tier** | 4 |

**Marker**

```python
MarkerDef(
    id="PSL044",
    severity="warning",
    summary="Coverpoint over a wide value domain has no explicit bins",
    detail=(
        "With no bins, the tool distributes 2**M values uniformly over "
        "auto_bin_max bins (64 by default). For a 32-bit coverpoint that is 64 "
        "bins of ~67 million values each: the report will reach 100% and mean "
        "nothing.\n\n"
        "Declare bins that match the intent, or narrow the field's value domain so "
        "that automatic binning is meaningful."
    ),
)
```

**Detection**

For each `coverpoint` with an empty bins body, determine the effective bit width `M` of its
expression type. Report when `2^M` substantially exceeds the effective `auto_bin_max`
(the covergroup's or coverpoint's option value, defaulting to 64). A threshold of `M > 8` is a
reasonable starting point.

**False-positive risk**

- **Enum coverpoints** — automatic bins are exactly the enumeration, which is correct and
  idiomatic. Never report those.
- **Narrow integer fields** (`bit[3]`) — 8 auto bins is fine.
- **Fields with a declared value domain** (`bit[16] in [0..15]`) — use the *domain* size, not
  the width.
- An explicit `option.auto_bin_max` raising the limit is a deliberate choice; honour it.

---

## Rules deliberately not specified here

These were considered and rejected as checker rules, with the reason:

| Candidate | Why not |
|---|---|
| "sequential activity block where a flow object belonged" | requires knowing the user's intent; unfixable false-positive rate |
| "`soft` constraint relied upon" | "relied upon" is not expressible in the AST |
| "vacuous implication" | requires a solver — this is tier 3, and belongs in the generation tool, not a static checker |
| "over-constrained model" | tier 3, same reason |
| "pool in the wrong scope" | the correct scope is a modelling decision, not a property of the code |
| "mislabelled `pure`" | requires proving purity of arbitrary code, including imported functions |
| "reliance on unspecified ordering" | detectable only for the narrow case of two same-kind execs in different extensions; consider that alone as a future rule |
