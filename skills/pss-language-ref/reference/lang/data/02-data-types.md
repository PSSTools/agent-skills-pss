# Data types

*Domain: data. LRM Clause 7 (§7.1–7.8, 7.10–7.12).*

## When you are writing this

- You are declaring a field and need to pick its type and width.
- You need a value domain ("size is 4, 8, 16 or 32").
- You are wondering whether something can be `rand`.
- An assignment or comparison isn't behaving — check the conversion rules below.

## Decide

See `README.md` for the type-selection table. The decisions this page settles:

| Question | Answer |
|---|---|
| "Can this be `rand`?" | all scalars **except** `chandle`, `float32`, `float64`; plus arrays and lists of randomizable types. `map` and `set` **cannot**. |
| "Width or domain?" | they are independent — a field holds the **intersection**. Use width for layout, domain for legality. |
| "Struct or component?" | struct = a value, deep-copied. Component = a position in the tree. |
| "Value or handle?" | scalars and structs are values; `ref` types are handles and may be `null`. |

### Terminology, because the LRM leans on it

- **scalar** — one `bit`, `int`, `bool`, `enum`, `string`, `float32`, `float64`, `chandle` (or a
  typedef thereof). A struct or collection is *not* a scalar.
- **aggregate** — a struct or a collection, nestable. Actions, components, monitors, and
  flow/resource objects are *not* aggregates.
- **plain-data type** — a scalar, or an aggregate of plain-data types.

## Canonical form

```pss
struct config_s {
    // integers: width and domain are separate concerns
    rand int              count;              // signed, 32 bits
    rand bit[5]           small;              // unsigned, 5 bits
    rand bit[5] in [0..31] bounded;
    rand bit[5] in [1,2,4] powers;
    rand bit[5] in [..10]  atmost10;          // 0..10
    rand bit[5] in [10..]  atleast10;         // 10..31

    rand bool             enabled;
    rand mode_e           mode;
    string                name;               // defaults to ""
    float64               ratio;              // never rand

    static const int      MAX = 4096;
}

enum mode_e { UNKNOWN, MODE_A = 10, MODE_B = 20, MODE_C = 35 }

typedef bit[31:0] uint32_t;

struct outer_s {
    rand config_s cfg;                        // rand propagates into the struct
    config_s      fixed;                      // not randomized
}
```

## Rules

### Integers (§7.2)

| Type | Default width | Default domain | Signedness |
|---|---|---|---|
| `int` | 32 bits | -2³¹ .. 2³¹-1 | signed |
| `bit` | **1 bit** | 0..1 | unsigned |

- Syntax: `(int|bit) [ [width [: 0]] ] [ in [domain] ]`.
- **No 4-state values.** X/Z arriving through the foreign interface become 0. Default value 0.
- The dual-bound form `int[4:0]` is **deprecated**; write `int[5]`.
- Width and value domain are independent; the variable holds the intersection.
- Open ranges are allowed in domains: `[..10]`, `[10..]`.

### Floating point (§7.3)

`float32` (IEEE binary32), `float64` (IEEE binary64). **May not be `rand`** and may not be a
`randomize` target. Results are **not guaranteed identical across solve and target platforms**
(§7.3.2). `std_pkg` storage types must be converted to a computation type before arithmetic —
see `../platform/05-core-library-api.md`.

### bool (§7.4)

`true` (1) / `false` (0). Default `false`.

### Enumerations (§7.5)

- `enum ID [: integer_type] { item [= const], … }`. The optional base type fixes width and
  signedness and bounds the legal item values; it shall have **no** value domain.
- First unassigned item is 0; each later unassigned item is previous + 1. Values need not be
  contiguous or ascending; negatives are allowed with a signed base; **all values must be
  distinct**.
- **The default value of an uninitialized enum field is the first item declared** — not 0, not
  the minimum.
- Items are static constants: `mode_e::MODE_A`, or unqualified where the expected type is the
  enum.
- Enums are extensible (`extend enum`). An enum may be declared empty and populated by
  extensions, but **declaring a variable of a still-empty enum is illegal**. Item names must be
  unique across the type and all its extensions.

### Strings (§7.6)

- Default `""`. Domains are **lists of literals**; **ranges of string literals are not
  permitted**.
- Sub-string operator `s[a..b]`, `s[..b]`, `s[a..]`, `s[i]` — **never on the left of an
  assignment**, and not randomizable.
- Methods: `size()`, `find(sub, first_pos=0)`, `find_last(sub, first_pos=-1)`, `find_all(sub)`,
  `lower()`, `upper()`, `split(sep)` (`sep` may not be empty), `chars()`.
- In restricted embedded target environments, string operators and methods may be unusable in
  target execs when argument values are not solve-time known.

### chandle (§7.7)

Opaque handle to a foreign pointer. **Never `rand`**; only `==`/`!=`, and only against the
literal `0` (foreign null). Default 0.

### Structs (§7.8)

- `struct_kind ::= struct | buffer | stream | state | resource` — the flow/resource kinds share
  the struct grammar.
- Plain-data fields only. A struct may contain constraints, covergroups, and exec blocks of
  **any kind except `init_down`, `init_up`, `body`**.
- Single inheritance with `:`.
- **Assignment is a deep copy** of all data attributes, nested structs included. Assigning a
  derived value to a base variable copies **only the base fields**.

### Reference types (§7.10)

- `ref (action|monitor|component|flow_object|resource_object)_type`.
- Allowed for **local variables, function parameters, function return types**, and — for
  **component** reference types only — fields in component scopes. Collections thereof, in the
  same places.
- **Not** allowed for fields of actions, monitors, flow/resource objects, or structs; never for
  `static const`.
- Default `null`; dereferencing `null` is an error.
- Assignment target may be a ref of the same or a derived type, an instance path to such a
  component, or `null`. After assignment the LHS **aliases** the same entity.
- Solver-managed reference fields you never assign: `comp`, sub-action handles, action
  `input`/`output` fields, resource claim fields.

### typedef (§7.11)

`typedef bit[31:0] uint32_t;` — a typedef of a scalar is a scalar, of an aggregate an
aggregate.

### Conversion and casts (§7.12)

- `(casting_type) expression`, where the casting type is an integer, bool, enum, float,
  reference type, or a type identifier.
- Numeric/bool/enum values convert only among themselves; reference values only to compatible
  reference types.
- Any non-zero → `bool` is `true`; `false`→0, `true`→1.
- **A cast to `bit` must state the width.**
- No explicit cast needed for `int` ↔ `bit`, `float32` ↔ `float64`, or float ↔ integer
  (**float → int truncates**).
- Cast to an enum: the value must correspond to a declared item's numeric value.
- **Upcast** to a supertype ref is implicit and yields the same reference. **Downcast** to a
  subtype ref yields the same reference if the dynamic type matches, otherwise **`null`**.

### Field declarations

```
attr_field ::= [ public | protected | private ] [ rand | static const ] data_declaration
```

`const` fields may be read but never assigned; a `const` aggregate has `const` elements.

## Gotchas

**`bit` is one bit.**
```pss
bit    flags;      // 1 bit — almost never what you meant
bit[8] flags;      // a byte
```
*Tier 4* — assignments silently truncate.

**Enum default is the first item, not zero.**
```pss
enum st_e { RUNNING, IDLE }     // default is RUNNING
enum st_e { IDLE, RUNNING }     // default is IDLE — declare the sane one first
```
*Tier 4.*

**Declaring `rand` on a non-randomizable type.**
```pss
rand float64 r;      // WRONG
rand chandle c;      // WRONG
rand map<int,int> m; // WRONG
```
*Tier 1–2.*

**Deprecated dual-bound integer form.** `int[4:0]` still parses on most tools; use `int[5]`.
*Tier 4.*

**Expecting derived-struct fields to survive a base-typed assignment.**
```pss
struct b_s { int x; }
struct d_s : b_s { int y; }
b_s b; d_s d;
b = d;      // copies x only; y is gone
```
*Tier 4.*

**Downcast returning `null` instead of failing.** A `ref` downcast to a non-matching type is
`null`, not an error. Check before dereferencing.
*Tier 4.*

**A `ref` field on a struct or action.** Not allowed (§7.10) — only locals, parameters, return
types, and component-typed fields in components.
*Tier 1–2.*

**String literal *ranges* in a domain.**
```pss
string in ["a".."z"] s;    // WRONG
string in ["a","b"]  s;    // RIGHT
```
*Tier 1–2.*

**Float results differing between solve and target.** Not a bug — the standard does not
guarantee identical results (§7.3.2). Do not build a constraint that depends on bit-exact float
behaviour on both sides.
*Tier 4.*

**Declaring a variable of an enum that only extensions populate.** Illegal if the enum is still
empty at that point.
*Tier 1–2.*

## See also

- `03-collections.md` — `array`, `list`, `map`, `set` in full.
- `04-expressions-operators.md` — how these types combine, and result widths.
- `01-lexical-and-literals.md` — literals and defaults.
- `../constraints/01-algebraic-constraints.md` — domains expressed as constraints.
- `../platform/04-registers.md` — `packed_s`, where widths become memory layout.
