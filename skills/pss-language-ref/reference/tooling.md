# Checking PSS: what tools catch, and what they don't

You will have *some* PSS tool available — a parser, a linter, a full compiler, or a
generation-capable tool. Which one is an environment question: discover it the normal way.
This page is about something more durable — **which classes of error any tool can possibly
catch**, so you know where to spend care.

---

## Check tiers

PSS violations fall into four tiers by the depth of processing needed to detect them. Tools
differ in how far up the stack they reach; the tiers themselves are a property of the language.

| Tier | Detected by | Typical violations |
|---|---|---|
| **1 — parse & name resolution** | any PSS front end | syntax errors; unknown type / identifier / method; duplicate declarations; `extend` of an unknown type; `rand` in a procedural scope (the grammar has no production for it) |
| **2 — semantic elaboration** | a type-checking compiler | solve/target platform misuse; type mismatches; writes to component attributes; `pure` violations; conflicting register offset schemes; adding fields to a `packed_s`; parameter directions on native functions |
| **3 — solve & generation** | a generation-capable tool | unsatisfiable or over-constrained solves; unresolvable action inference; unbound pools; unschedulable activities; resource over-subscription |
| **4 — unchecked** | nothing, statically | `match` arms that don't cover the domain at runtime; mislabelled `pure` (results silently cached); `message()` arguments with side effects; models that are legal but mean the wrong thing |

Every **Gotchas** entry in `lang/` carries its tier. Use it:

- **Tier 1** — cheap. Write, check, iterate. The tool teaches these faster than prose does.
- **Tier 2** and **Tier 3** — caught only if the environment happens to have a deep enough
  tool. Read the rule *before* writing if you only have a parser.
- **Tier 4** — caught by nothing. These are the reason this reference exists. They also make up
  most of `../checklists/review.md`.

### Tier 1 is the floor, not the bar

> A clean parse means the names resolve and the braces match.

Never report "the PSS checks clean" as "the PSS is correct". Say which tier you reached. If all
you have is a parser, say so and note that tiers 2–4 were reviewed by hand (and then actually
review them — `../checklists/review.md`).

---

## Cross-tool realities

These hold regardless of which tool you picked up.

### Syntax errors cascade — fix the first one only

One unparseable construct routinely produces a long tail of spurious follow-on errors. A single
unsupported construct has been measured producing ten errors across ten lines, nine of them
meaningless (`unexpected keyword 'action'`, `unexpected '}'` — all artifacts of the parser
being lost, not real problems).

> **Rule: fix the first diagnostic, re-run, repeat.** Never treat the error tail as a work list,
> and never "fix" the later lines it points at.

Name-resolution errors (tier 1, but post-parse) generally do *not* cascade this way and can be
read as a set.

### Tools lag the standard

A 3.1 construct may be rejected by a tool implementing 3.0, or an earlier 3.1 draft. That is a
**false positive on legal PSS**.

- Rules that are new in 3.1 are tagged **3.1** inline throughout `lang/`, and collected in
  `3.1-deltas.md`. When you write one, you know you are exposed.
- If the tool rejects a **3.1**-tagged construct, that is expected. Report it; offer the 3.0
  workaround from `3.1-deltas.md` if the user needs one. Do not silently rewrite.

### Tools also have plain grammar gaps

Independently of version, a front end may reject a legal construct its grammar never covered —
including long-standing ones. Same rule: **verify against the LRM clause cited on the page
before changing anything.** If the clause says it is legal, the tool is wrong.

Distinguishing a gap from your own mistake is easy in practice: reduce to the smallest snippet
that reproduces it and compare it to the page's *Canonical form* section.

### Core-library availability varies

Some tools bundle `std_pkg` / `executor_pkg` / `addr_reg_pkg` / `sync_pkg`; others require them
to be supplied on the command line. If core-library names fail to resolve, that is a
tool-invocation problem, not a model problem — do not start declaring your own `addr_handle_t`.

### Solver failures are not always your constraints

A tier-3 "no solution" can come from a constraint contradiction, an unbound pool, an
uninferable action, or a resource that cannot be claimed. Those have very different fixes.
`playbooks/10-diagnose.md` separates them.

---

## What to do with a diagnostic

1. **Is it the first one?** If not, fix the first and re-run (see cascading, above).
2. **Which tier?** Match the message *shape* against the table in `playbooks/10-diagnose.md`.
3. **Does the cited rule actually exist?** Follow the page link, read the clause citation. If
   the construct is legal, you have a tool gap or a version lag — say so, don't rewrite.
4. **Fix the cause, not the symptom.** `unknown type 'Foo'` is usually a missing `import`, not
   a reason to declare `Foo`.

## What to do when there is no diagnostic

That is the normal case for tiers 3 and 4, and it is where models go wrong quietly. Run
`../checklists/review.md`. The items there are exactly the rules nothing else will tell you about.
