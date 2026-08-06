# Collections: `array`, `list`, `map`, `set`

*Domain: data. LRM §7.9.*

## When you are writing this

- The user described several of something: "four descriptors", "a list of addresses".
- You need a lookup table.
- You need to accumulate values in an exec.
- You are about to `foreach` over something and need to know what the iterator can be.

## Decide

| You need… | Use | Randomizable | Ordered |
|---|---|---|---|
| a fixed number of elements, known at elaboration | `array<T,N>` / `T name[N]` | yes, if `T` is | yes |
| a sequence that grows and shrinks | `list<T>` | yes, if `T` is | yes |
| a keyed lookup | `map<K,V>` | **no** | **no** |
| membership testing | `set<T>` | **no** | **no** |

**The randomization question decides most cases.** If the solver must choose the contents, it
has to be an `array` or a `list`. `map` and `set` are exec-time structures: build them in
`pre_solve`/`init_up`, read them in constraints and code.

**Square form vs template form.** `T name[N]` and `array<T,N>` are the same for data types. The
template form is **required** wherever a *data type* is needed — return types, nested
collections (`list<array<int,4>>`). The square form is additionally used for arrays of **action
handles, monitor handles, components, and flow/resource object references**, which are not data
collections at all.

## Canonical form

```pss
component pss_top {
    array<bit[16],5>   fixed;
    list<bit[16]>      grown;
    map<string,bit[32]> by_name;
    set<bit[16]>       seen;

    exec init_up {
        fixed   = {1, 2, 3, 4, 4};        // exact size required
        fixed[0] = 5;

        grown.push_back(10);
        grown.push_back(20);

        by_name.insert("base", 0x1000);

        seen = fixed.to_set();            // 4 elements — the duplicate collapses
    }

    action a {
        rand array<bit[8],4> payload;     // randomizable
        rand list<bit[8]>    var_payload; // randomizable; size constrained separately
        constraint var_payload.size() in [1..8];
        constraint foreach (payload[i]) { payload[i] != 0; }
    }
}
```

## Rules

### Shared

| Operation | `array` | `list` | `map` | `set` |
|---|:-:|:-:|:-:|:-:|
| `[]` index | ✓ (int) | ✓ (int) | ✓ (key) | — |
| `=` copy | ✓ | ✓ | ✓ | ✓ |
| `==` / `!=` | ✓ (same type **and size**) | ✓ | ✓ | ✓ (unordered) |
| `in` membership | ✓ | ✓ | ✓ (keys) | ✓ |
| `foreach` | ✓ | ✓ | ✓ | ✓ (**iterator only**) |

- `list`, `map`, `set` start **empty** (equivalently `= {}`) and are mutated in exec blocks.
- `map` and `set` are unordered and **non-randomizable**.
- Collections nest.

### Arrays (§7.9.2)

Fixed size, known at elaboration. Methods:

| Method | Result |
|---|---|
| `int size()` | a **constant expression** — arrays are fixed size. Also valid on handle/reference arrays |
| `T sum()` | numeric arrays only; `int` for `int`/`bit`, `float64` for float |
| `string join(string connector)` | string arrays |
| `string str_from_chars()` | integer arrays |
| `list<T> to_list()` | |
| `set<T> to_set()` | |

The properties `a.size` / `a.sum` are **deprecated** spellings of `a.size()` / `a.sum()`.

### Lists (§7.9.3)

`int size()`, `void clear()`, `T delete(int index)`, `void insert(int index, T e)`,
`T pop_front()`, `void push_front(T)`, `T pop_back()`, `void push_back(T)`,
`string join(string)`, `string str_from_chars()`, `set<T> to_set()`, `void shuffle()`.

Out-of-bounds `delete`/`insert` is illegal. `insert` at `size()` is equivalent to `push_back`.

**List randomization** (§7.9.3.4): a `rand list` has its size and elements chosen by the solver;
constrain `size()` explicitly or you get an unconstrained size.

### Maps (§7.9.4)

`int size()`, `void clear()`, `V delete(K key)` (**illegal if absent**), `void insert(K, V)`
(**replaces** an existing key), `set<K> keys()`, `list<V> values()` (order unspecified).

### Sets (§7.9.5)

`int size()`, `void clear()`, `void delete(T e)` (**illegal if absent**), `void insert(T e)`
(no effect if present), `list<T> to_list()` (arbitrary order).

### `foreach` over collections

- `array`/`list` — index is `int`, `0 .. size()-1`, in order.
- `map` — the index variable is **key-typed**; traversal order is **undefined**.
- `set` — an **iterator is required and an index is forbidden**.
- Iterator and index variables are implicitly declared, scoped to the loop, and **read-only**.
- **Modifying the iterated collection inside the body is an error.**

## Gotchas

**Expecting to randomize a `map` or `set`.**
```pss
rand map<int,int> m;    // WRONG
```
*Tier 1–2.* Randomize a `list` of key/value structs and build the map in `post_solve`.

**Relying on `map` iteration order.**
```pss
foreach (v : m [k]) { addrs.push_back(v); }   // order is undefined
```
*Tier 4* — reproducible on one tool, different on another.

**Indexing a `set`.** There is no `[]` on a set, and `foreach` over one forbids an index.
*Tier 1.*

**`delete` on an absent key or element.** Illegal for both `map` and `set` — check with `in`
first.
*Tier 3–4* — a runtime error at best, undefined at worst.

**Comparing arrays of different size.** `==` requires the same type **and** size.
*Tier 2.*

**Mutating the collection you are iterating.**
```pss
foreach (e : l) { l.push_back(e); }   // WRONG
```
*Tier 4* on most tools.

**Assigning to a `foreach` iterator or index.** They are read-only.
*Tier 1–2.*

**Forgetting to constrain a `rand list`'s size.** You get an arbitrary size, often 0 or
enormous.
*Tier 4* — the model solves; the test is nonsense.

**Wrong array literal size.** Arrays require an exact-size literal; lists take their size from
one.
*Tier 2.*

**Using the square form where a data type is required.**
```pss
function int[4] f();               // WRONG
function array<int,4> f();         // RIGHT
list<int[4]> l;                    // WRONG
list<array<int,4>> l;              // RIGHT
```
*Tier 1.*

**Treating a handle array as a data collection.** `xfer x[4];` is an array of action handles:
indexable, `size()`-able, reference semantics — but the data methods do not apply.
*Tier 1–2.*

## See also

- `02-data-types.md` — element types and randomizability.
- `01-lexical-and-literals.md` — collection literals.
- `../procedural/03-procedural-statements.md` — `foreach` in procedural code.
- `../constraints/01-algebraic-constraints.md` — `foreach` constraints over collections.
- `../constraints/03-randomization.md` — randomization of lists.
- `../activity/01-activities.md` — action-handle arrays and their traversal.
