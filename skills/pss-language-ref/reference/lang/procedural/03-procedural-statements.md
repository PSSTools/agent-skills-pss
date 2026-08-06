# Procedural statements

*Domain: procedural. LRM §20.7.*

Everything legal inside a procedural `exec` block and a native function body.

## When you are writing this

- You are filling in an `exec body`, an `init_up`, or a function.
- You need a loop, a branch, or a local variable.
- You need randomness inside procedural code.
- You need to yield to other execs on the same executor.

## Decide

| You need… | Write |
|---|---|
| a local | `int x;` / `int i = 0, j = 1;` — anywhere in the scope, before first use |
| a two-way branch | `if (cond) {…} else {…}` — condition must be `bool` |
| a multi-way branch | `match (e) { [ranges]: …; default: …; }` |
| a counted loop | `repeat (n) {…}` / `repeat (i : n) {…}` |
| a pre-tested loop | `while (cond) {…}` |
| a post-tested loop | `repeat {…} while (cond);` |
| iteration over a collection | `foreach (e : coll [i]) {…}` |
| early exit | `break;` / `continue;` |
| to return | `return expr;` / bare `return;` |
| randomness | `randomize v1, v2 with {…};` or `urandom()` |
| to let other execs run | `yield;` |
| an explicit block | `sequence { … }` — the keyword is optional documentation |

**`match` vs chained `if`.** `match` requires exactly one arm to match, so it documents the
intent that the arms are exhaustive and disjoint — but nothing checks it statically. Always add
a `default`.

## Canonical form

```pss
function int demo(array<int,8> a, int n) {
    int sum;                     // declare anywhere in the scope, before first use
    int i = 0, j = 1;
    // rand int bad;             // ERROR: no rand variables in a procedural context

    sequence { sum = 0; }        // `sequence` is optional documentation

    if (n > 0) { sum += n; } else { sum -= n; }

    repeat (4)        { sum += 1; }
    repeat (idx : 4)  { sum += idx; }            // index 0..count-1
    while (i < n)     { i += 1; }                // condition sampled before
    repeat { j += 1; } while (j < n);            // condition sampled after

    foreach (el : a)       { sum += el; }        // iterator alias
    foreach (a[k])         { sum += a[k]; }      // index only
    foreach (el : a [k])   { sum += el * k; }    // both
    foreach (el : a) {
        if (el == 0)  break;                     // innermost loop
        if (el == 42) continue;
    }

    match (n) {                                  // exactly one arm must match
        [0..3]:    sum = 1;
        [4..7]:    sum = 2;
        [8,16,32]: sum = 3;
        default:   sum = 4;                      // else it is an error
    }

    return sum;                                  // bare `return;` ends a void fn or exec
}
```

Procedural randomization:

```pss
struct S1 { rand bit[8] a, b; }
struct S2 { rand S1 f1; S1 f2; constraint f1.a < f2.a; }

action A {
    exec post_solve {
        S2     v1;
        bit[4] v2;
        v1.f2.a = 100;                              // an invariant of this randomize
        randomize v1, v2 with { v1.f1.a < v2; };    // v1.f1.a ends up in [0..14]
    }
}
```

## Rules

### Scoped blocks and variables (§20.7.1, §20.7.2)

- A block may be written `{ … }` or `sequence { … }`; the keyword is documentation.
- **Variables may be declared anywhere in the scope but referenced only after their
  declaration** (§18.2a). Initializers are allowed.
- **No `rand` variable declarations in a procedural context** (§20.7.2). The grammar has no
  production for it — this is a tier-1 error. Randomness comes from `randomize` or `urandom()`.

### Assignment (§20.7.3)

`=`, plus the compound forms `+= -= <<= >>= |= &=`. **Compound assignments exist in procedural
statements only, never inside an expression.** `a <<= b` ≡ `a = a << b`.

### Calls (§20.7.4)

- **`void` functions: standalone statements only.**
- A non-`void` call used as a statement should be discarded explicitly: `(void)f();`

### `return` (§20.7.5)

`return expr;` in a non-`void` function — the return type is the expected type of the
expression. Bare `return;` ends a `void` function or an exec block.

### `repeat` / `while` (§20.7.6, §20.7.7, §20.7.8)

- `repeat (count) stmt` — count is a **non-negative** `int`/`bit` expression.
- `repeat (index : count) stmt` — the index ranges `0 .. count-1`.
- `while (cond) stmt` — condition sampled **before** each iteration.
- `repeat stmt while (cond);` — condition sampled **after** each iteration.
- Conditions must be `bool`.

### `foreach` (§20.7.9)

- `foreach ([iterator :] collection [[index]]) stmt`
- **The iterator and index variables are implicitly declared, scoped to the loop, and
  read-only.**
- **Modifying the iterated collection inside the body is an error.**
- You may specify an iterator, an index, or both. **For a `set`, an iterator is required and an
  index is forbidden.** For a `map`, the index is **key-typed** and traversal order is
  **undefined**.

### `match` (§20.7.9 / §20.7.10)

- Arms take **`open_range_list`s** — integer ranges, enum lists, or lists of string **literals**
  (`"a".."b"` ranges are **not** allowed).
- **More than one matching arm is an error.**
- **No matching arm and no `default` is an error** — at runtime, with nothing checking it
  statically.

### `break` / `continue` (§20.7.11)

Only inside `repeat` / `while` / `foreach`, affecting the **innermost** loop.

### `randomize` (§20.7.12, §13.4.6)

- `randomize v1, v2 [with { … }];`
- **All target variables are solved together**, and are treated as random **whether or not
  declared `rand`**.
- Within a struct-typed target, `rand` sub-fields are random and **non-`rand` sub-fields are
  invariants** at their current values.
- Constraints declared in the target types apply, plus the inline constraints.
- On the solve platform, **solve-time exec blocks of the involved types are evaluated as part of
  the randomization**.
- **On the target platform only scalar integer randomization is supported.** Struct
  randomization is solve-only and may not be reached directly or indirectly from a target exec.

### `yield` (§20.7.14)

**Cooperatively suspends a target exec** so other execs on the same executor can run. **Target
execs and target functions only.** A no-op if nothing else is runnable.

### `compile if` in procedural scope (§19.2.1)

Legal in execs and functions — **except in target-template exec bodies**.

## Gotchas

**`rand` in a procedural scope.**
```pss
exec body { rand int x; }     // WRONG
```
*Tier 1.*

**`match` with no `default`.**
```pss
match (n) { [0..3]: x = 1; [4..7]: x = 2; }    // runtime error for n = 8
```
*Tier 4* — nothing checks the domain. Always add a `default`, even one that calls `error()`.

**Overlapping `match` arms.** More than one match is an error, and it is easy to create with
adjacent ranges.
*Tier 4.*

**String ranges in a `match` arm.** Lists of string literals are allowed; ranges are not.
*Tier 1–2.*

**Writing the iterated collection.**
```pss
foreach (e : l) { l.push_back(e); }    // WRONG
```
*Tier 4* on most tools.

**Assigning the iterator or index.** Read-only.
*Tier 1–2.*

**Index on a `set` `foreach`.** Forbidden; an iterator is required.
*Tier 1–2.*

**Relying on `map` iteration order.** Undefined.
*Tier 4.*

**Compound assignment inside an expression.**
```pss
y = (x += 1);      // WRONG
```
*Tier 1.*

**Struct `randomize` in a target exec.** Solve platform only.
*Tier 2.*

**Assuming `randomize` respects `rand`.** Targets are random regardless of the `rand` keyword;
non-`rand` *sub-fields* of a struct target are the invariants.
*Tier 4.*

**A polling loop with no `yield`.**
```pss
exec body { while (comp.done.read_val() == 0) { } }   // WRONG: starves the executor
```
*Tier 4* — see `../platform/02-sync-and-communication.md`.

**`yield` in a solve exec.** Target-only.
*Tier 2.*

**A variable used before its declaration.** The general "declare anywhere" rule does **not**
apply in procedural or activity blocks (§18.2a).
*Tier 1.*

## See also

- `01-exec-blocks.md` — where these statements live.
- `02-functions.md` — calling rules and parameter semantics.
- `../data/03-collections.md` — the methods `foreach` bodies call.
- `../data/04-expressions-operators.md` — expression typing, including compound assignment.
- `../constraints/03-randomization.md` — what `randomize` actually solves.
- `../platform/02-sync-and-communication.md` — `yield` and blocking calls.
