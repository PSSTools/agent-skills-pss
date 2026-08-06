# Playbook: constrain and randomize

*"Sizes must be a multiple of 4." "Never both at once." "Mostly small, occasionally huge."*

## Steps

**1. Separate rules from preferences.** This is the decision that matters most.

| The user said | Write |
|---|---|
| "must", "never", "always", "illegal" | a **hard** constraint |
| "usually", "prefer", "by default" | `soft` **3.1**, or a `default` value constraint |
| "mostly A, sometimes B" | `dist` |
| "the tool should pick" | nothing — leave it `rand` |

A hard constraint that isn't really a rule is how models become unsolvable. A `soft` constraint
you then rely on is how tests become silently wrong.

**2. Put the constraint where the rule lives.**

- inherent to the type → in the type body;
- true of this scenario → in the containing action;
- true of this traversal only → inline, `do a with { … };`.

**3. Write it.**

```pss
constraint {
    size in [4..4096];
    size % 4 == 0;
    wide -> size >= 512;                 // implication — bidirectional!
    if (mode == FAST) { chan == 0; } else { chan in [1..3]; }
    unique { a, b, c };
    foreach (e : payload [i]) { e != i; }
    forall (s : mem_seg_s) { s.addr % 64 == 0; }
}
constraint { soft size == 64; }
constraint { dist size in [64 := 8, 128..4096 :/ 2]; }
```

**4. Randomize procedurally only where declarative constraints cannot reach.**

```pss
exec post_solve {
    S2     v1;
    bit[4] v2;
    v1.f2.a = 100;                              // invariant
    randomize v1, v2 with { v1.f1.a < v2; };
}
```

Struct randomization is **solve-only**; target execs get scalar integers and `urandom()`.

## The five rules that cause the most confusion

1. **`->` and `if`/`else` constraints are bidirectional.** `mode == FAST -> len >= 512` also
   means `len < 512 -> mode != FAST`. This is correct and it is why "mode is never FAST".
2. **`soft` is not a guarantee.** It is dropped whenever a hard constraint or a higher-priority
   soft constraint contradicts it.
3. **`dist` is the lowest-priority soft constraint.** A hard constraint can push the value
   entirely outside the distribution list.
4. **A field is randomized only if the path to it is `rand`.** `S1 f;` (no `rand`) means `f.a`
   is never randomized, however `rand` it is declared inside `S1`.
5. **Nothing computed in `exec body` can feed a constraint** (§13.4.13), and there is **no
   backtracking across exec blocks** — a conflicting `post_solve` assignment is an error.

## Checks before you call it done

- [ ] Every hard constraint is a real rule, not a preference.
- [ ] No `soft` constraint is being relied on by later code.
- [ ] No implication whose antecedent can never be true (a silently vacuous constraint).
- [ ] `rand` appears on every step of the path to each randomized field.
- [ ] `rand list` sizes set in `pre_solve` — they cannot be constrained.
- [ ] No `rand` variable in a `dist` weight or range bound.
- [ ] Widths and signedness checked in constraint expressions
      (`../lang/data/04-expressions-operators.md`) — a shift silently truncates to the left
      operand's width.
- [ ] Nothing assigned in `pre_solve` to a `rand` scalar and expected to survive.

## Diagnosing a solve failure

1. **Is it really over-constrained, or is it structural?** "No solution" also comes from unbound
   pools, uninferable actions, and unsatisfiable resource claims. Check
   `10-diagnose.md` first.
2. **Bisect.** Comment out constraint blocks in halves. Start with implications and `forall` —
   they have the widest reach.
3. **Check bidirectionality.** Reread every `->` in the reverse direction.
4. **Check the solve/target boundary.** A constraint on a field assigned in `exec body` is
   likely the culprit.
5. **Check widths.** `bit[8] a; b == a << 4;` loses the top bits before the comparison.

## See also

- `../lang/constraints/01-algebraic-constraints.md` — every constraint form.
- `../lang/constraints/03-randomization.md` — solve order, lookahead, exec ordering.
- `../lang/constraints/02-scheduling-constraints.md` — ordering as a constraint.
- `../../examples/constraints.pss`.
