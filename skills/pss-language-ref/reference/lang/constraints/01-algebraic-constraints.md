# Algebraic constraints

*Domain: constraints. LRM §13.1.*

## When you are writing this

- The user stated a rule about legal values: "must be aligned", "never zero", "at most 4K".
- The user stated a relationship: "the length must fit in the buffer".
- The user stated a preference rather than a rule: "usually small, occasionally huge".
- You want a distribution rather than a uniform choice.

## Decide

| The requirement | Write |
|---|---|
| always true of this type | `constraint { ... }` in the type body |
| true of this one traversal | `do a with { ... };` |
| "if P then Q" | `P -> Q;` |
| "P and Q go together, otherwise R" | `if (P) { Q } else { R }` |
| "one of these values" | `x in [1, 2, 4..8];` |
| "all different" | `unique { a, b, c };` or `unique arr;` |
| "true of every element" | `foreach (e : coll [i]) { ... }` |
| "true of every instance of type T below here" | `forall (x : T [in path]) { ... }` |
| a value unless overridden statically | `default x == 4;` / `default disable x;` |
| a preference that yields to hard rules | `soft x == 4;` **3.1** |
| a weighted spread of values | `dist x in [1 := 5, 2..8 :/ 5];` |
| a constraint enabled by a condition at traversal | `dynamic constraint` |

### `soft` vs `default` vs `dist`

All three express "prefer this", and they differ in what can override them:

| | Overridden by | Priority |
|---|---|---|
| `default x == c;` | `default disable x;` from a containing type — **static** | same as a hard constraint |
| `soft x == c;` | any higher-priority soft constraint, and any hard constraint — **dynamic** | see the ordering rules below |
| `dist x in [...];` | everything — it is a soft constraint | **lower than all other soft constraints** |

Use `default` when the override is a static decision made by the model's assembler. Use `soft`
when the override is a condition inside the model. Use `dist` when you care about the shape of
the distribution rather than any single value.

**A `soft` constraint is not a guarantee.** Never write code that assumes it held.

## Canonical form

```pss
struct cfg_s {
    rand bit[16] len;
    rand bit[32] addr;
    rand bool    wide;
    rand bit[8]  chans[4];

    constraint {                                // unnamed member constraint
        len > 0 && len <= 4096;
        addr % 4 == 0;
        wide -> len >= 512;                     // implication — BIDIRECTIONAL
        if (len > 1024) { addr % 64 == 0; } else { addr % 4 == 0; }
        unique { chans };
        foreach (c : chans [i]) { c != i; }
    }

    constraint c_soft { soft len == 64; }       // named; a preference
    constraint { dist len in [64 := 8, 128..4096 :/ 2]; }
    constraint { default wide == false; }
}

action xfer {
    rand cfg_s cfg;
    // applies to every mem_seg_s instance in this action's subtree
    constraint { forall (s : mem_seg_s) { s.size > 0; } }
}

action test {
    xfer x;
    activity {
        x with { cfg.len == 128; soft cfg.wide == true; };   // inline: highest soft priority
    }
}
```

## Rules

### Member constraints (§13.1.1)

- `constraint [name] { ... }` in a struct, action, flow/resource object, or component-nested
  type. **Components themselves may not have constraints on their own data.**
- Multiple constraint blocks in one type all apply — they conjoin.
- Constraint expressions follow the usual expression typing rules (§8.7), including width and
  signedness propagation. See `../data/04-expressions-operators.md`.

### Inheritance (§13.1.2)

Constraints are inherited. A same-named constraint in a derived type **replaces** the base's;
an unnamed one adds to it. This is the constraint analogue of exec shadowing.

### Inline constraints (§13.1.3)

`do A with { ... };` or `a1 with { ... };` — applies only to that traversal. Inside, the
traversed action's fields are unqualified; the containing action's fields are reachable too.

### Implication and if-else (§13.1.5, §13.1.6)

- `expr -> constraint_set;`
- `if (expr) constraint_set [else constraint_set]`
- **Both are bidirectional.** `a == 0 -> b == 1;` also constrains `a` whenever `b != 1`. This
  is the single most misunderstood constraint behaviour in PSS — it is a logical relation, not
  a procedural test.

### `foreach` constraints (§13.1.7)

`foreach ([iter :] expr [[index]]) constraint_set` — iterates a collection. Same
iterator/index rules as elsewhere: read-only, implicitly declared, scoped to the loop.

### `forall` constraints (§13.1.8)

`forall (iter : type_id [in ref_path]) constraint_set` — applies to **every instance of that
type** in the constraint's application scope. `type_id` may be an action, struct, stream,
buffer, state, or resource type. Without `ref_path`, the scope is the subtree of the enclosing
scope — for a type-level member constraint that means all the context type's fields, and for a
compound action also its sub-actions.

This is the tool for "every memory segment in this scenario must be aligned" without touching
every declaration.

### `unique` constraints (§13.1.9)

Two forms:

- `unique arr;` or `unique arr[lo..hi];` — the array/list element values shall be unique. Slice
  indices may themselves be random. If the slice is empty (left > right, left ≥ size, or right
  negative) the constraint is **satisfied vacuously**.
- `unique { a, b, c };` — those attributes' values shall be unique.

### Default value constraints (§13.1.10)

- `default hierarchical_id == constant_expression;`
- `default disable hierarchical_id;`
- Semantics are those of the corresponding equality constraint **unless disabled** from a
  direct or indirect containing type. **The right-hand side must be a constant expression.**
- **Active defaults have the same priority as hard constraints** — a soft constraint that
  contradicts an active default is discarded.
- Multiple defaults / `default disable`s in the same type scope are order-sensitive (§17.2.5).

### Soft constraints **3.1** (§13.1.11)

`soft expression;`

- Express a **prioritized preference**. Lower-priority soft constraints are discarded when
  contradicted by higher-priority ones. **Any soft constraint contradicting a hard constraint
  (or an active default) is discarded.**
- Priority order, highest first:
  1. soft constraints in an **inline** (`with`) block;
  2. within one construct, **later declarations beat earlier** ones;
  3. constraints in the containing scope beat those in **sub-attributes**; among sub-attributes,
     later-declared attributes beat earlier ones;
  4. soft constraints on flow-object **outputs** beat those on **inputs**;
  5. a **derived** type beats its base; a **type extension** beats the initial declaration but
     loses to a derived type; among extensions, **later-applied** beats earlier;
  6. within an iterative constraint, **later iterations** beat earlier ones;
  7. a `forall` behaves as if expanded in-line at its location.

### Distribution directive (§13.1.12)

`dist expression in [ item [:= w | :/ w], … ];`

- A `dist` **is a soft constraint with lower priority than every other soft constraint**.
- The left-hand expression shall be **scalar and contain at least one `rand` variable**. Ranges
  are allowed only for numeric or enumeration types.
- **`rand` variables may not appear in weights or range bounds.**
- Default weight is `:= 1`. `:=` gives the weight to **each value** in a range; `:/` **divides**
  the weight across the range's values. Total weight for a value is the sum of all weights
  applied to it.
- Hard constraints take priority and **may force the value outside the `dist_list` entirely**.
- With multiple `dist` directives acting on common expression elements with different weights,
  **the resulting distribution is undefined**.
- Integer typing follows the `in`-with-range-list rules of §8.7.1.

## Gotchas

**Reading `->` as procedural.**
```pss
constraint { mode == FAST -> len >= 512; }
// Also implies: len < 512 -> mode != FAST.
```
*Tier 4.* This is correct and intended, and it routinely produces "why is `mode` never FAST?".

**Assuming `soft` held.**
```pss
constraint { soft len == 64; }
exec body { assume_64_byte_dma(); }   // WRONG: len may be anything legal
```
*Tier 4.*

**Vacuous implication.** `false -> anything` is always satisfied, so a condition that is never
true silently disables the whole constraint. If a constraint seems to have no effect, check
whether its antecedent is reachable.
*Tier 4.*

**Vacuous `unique` on an empty slice.** Satisfied regardless of values (§13.1.9). Easy to hit
when the slice bounds are themselves random.
*Tier 4.*

**`rand` in a `dist` weight or range.**
```pss
constraint { dist x in [1 := w]; }    // WRONG if w is rand
```
*Tier 2.*

**Expecting `dist` to be honoured against a hard constraint.** It is the lowest-priority soft
constraint; a hard constraint wins and may push the value entirely outside the list.
*Tier 4.*

**Two `dist` directives on overlapping expressions.** The result is explicitly **undefined**.
*Tier 4.*

**Non-constant right-hand side in a `default`.**
```pss
constraint { default len == other_field; }   // WRONG: must be a constant expression
```
*Tier 2.*

**Same-named constraint in a derived type silently replacing the base's.** Name it differently
if you meant to add.
*Tier 4.*

**Constraining across the solve/target boundary.** A field assigned in `exec body` cannot appear
meaningfully in a constraint (§13.4.13), and **no backtracking happens across exec blocks** —
an assignment in `post_solve` that contradicts a constraint is an error, not a re-solve.
*Tier 3.*

**Over-constraining until nothing is left.** Symptom: "no solution", with no indication which
constraint is at fault. Bisect by commenting out constraint blocks; start with implications and
`forall`.
*Tier 3.*

## See also

- `02-scheduling-constraints.md` — ordering as a constraint.
- `03-randomization.md` — the solve process, ordering, and lookahead.
- `../data/04-expressions-operators.md` — expression typing inside constraints.
- `../structural/07-inheritance-extension-overrides.md` — constraint inheritance and extension
  ordering.
- `../../playbooks/05-constrain-and-randomize.md` — task-first.
