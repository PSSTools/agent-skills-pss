# Domain: data — what values look like

Supporting domain. You are here because you need to know what a field may hold, how a literal
is written, or what an expression evaluates to.

The characteristic failures here are quiet: a width that silently truncates, an enum whose
default is not what you assumed, an aggregate that was copied when you expected a reference (or
the reverse). None of these produce a diagnostic; they produce a wrong test.

---

## Decide: which type?

| You need… | Use | Note |
|---|---|---|
| a signed integer | `int` | 32-bit by default |
| an unsigned integer / a field of known width | `bit[N]` | 1 bit by default — `bit x;` is a single bit, not a byte |
| a truth value | `bool` | `true`/`false`, defaults to `false` |
| a small named domain | `enum` | **default value is the first item declared**, not 0 |
| text | `string` | defaults to `""` |
| an opaque handle from foreign code | `chandle` | never `rand`; only `==`/`!=`, only against `0` |
| real numbers | `float32` / `float64` | never `rand` |
| a fixed-size group of values | `array<T,N>` or `T name[N]` | randomizable if `T` is |
| a growable sequence | `list<T>` | starts empty; mutate in an exec |
| a keyed lookup | `map<K,V>` | **not** randomizable; iteration order undefined |
| a membership set | `set<T>` | **not** randomizable; `foreach` needs an iterator, forbids an index |
| a plain-data aggregate | `struct` | deep-copy on assignment |
| a handle to an existing object | `ref <kind>` | locals, parameters, return types only — never a field of an action/struct/object |

### The three that surprise people

- **`bit` is one bit.** `bit[7:0]` or `bit[8]` for a byte. A too-narrow field truncates
  silently — tier 4.
- **Enum default is the first declared item.** Not zero, not the minimum value. If you need a
  meaningful default, declare it first.
- **Struct assignment is a deep copy; passing a struct to a native function is by handle.** So
  `s2 = s1;` cannot alias, but `f(s1)` can mutate `s1`. Mark the parameter `const` if it must
  not. (§20.3.2)

## Pages

| Page | Covers |
|---|---|
| `01-lexical-and-literals.md` | comments, identifiers, keywords, number formats, string literals (including 3.1 solve-context formatting), aggregate literals, triple-quoted strings (Clause 4) |
| `02-data-types.md` | scalars, `enum`, `struct`, `typedef`, reference types, casts, defaults, value domains (Clause 7) |
| `03-collections.md` | `array`, `list`, `map`, `set` and their full method inventory, sizing, randomizability (§7.9) |
| `04-expressions-operators.md` | precedence, numeric promotion and result widths, `in`, `inside`, ternary, bit-select and part-select, `sizeof`, type conversion rules (Clause 8) |
| `05-annotations.md` | `@annotation` syntax and the standard annotations (§7.13, §21.6) |

## See also

- `../constraints/README.md` — value domains stated as constraints rather than as declarations.
- `../platform/04-registers.md` — `packed_s` layout, which is where field widths stop being
  cosmetic.
- `../procedural/03-procedural-statements.md` — where collections actually get mutated.
