# Lexical conventions and literals

*Domain: data. LRM Clause 4.*

## When you are writing this

- You need to write a number in a specific base or width.
- You need a multi-line string — a target template, a generated file, a formatted message.
- You are writing an initializer for a struct, array, list, or map.
- A literal isn't being accepted and you need the exact rule.

## Decide

| You need… | Write |
|---|---|
| a plain number | `42`, `0xdead_beef`, `0755`, `0b1010` |
| a number of a specific width | sized form: `8'hFF`, `4'b1010`, `32'd100` |
| a short single-line string | `"quoted"` |
| a multi-line string, or one containing quotes | `"""triple-quoted"""` |
| a string with values interpolated | triple-quoted + `{{expr}}` mustache **3.1 as a string expression** |
| a string built at solve time from a format | `std_pkg::format("...", args)` |
| a struct initializer | `{.a=1, .b=2}` |
| an array/list/set initializer | `{1, 2, 3}` |
| a map initializer | `{1:true, 2:false}` |
| an empty collection | `{}` |

**`format()` vs mustache**: `format()` is a function call with printf semantics and full
argument checking; mustache is textual interpolation inside a literal, with fixed per-type
formatting. Use `format()` for messages, mustache for emitted target code and for
templated multi-line text.

## Canonical form

```pss
// comments
// line comment
/* block comment */

// numbers — underscores are allowed anywhere in the digits
int  a = 42;              // decimal
bit[32] h = 0xdead_beef;  // hex
bit[9]  o = 0755;         // octal (leading 0)
bit[4]  b = 0b1010;       // binary
bit[8]  s = 8'hFF;        // sized: <width>'<base><digits>

// strings
string one = "a line, with \"escapes\" and \n";
string many = """
    line one
    line two — may contain " and ' freely
""";

// triple-quoted with interpolation and control flow
string report = """
    {# a comment that does not appear in the result #}
    size = {{size}}
    {% foreach (e : elems [i]) %}
    elem[{{i}}] = {{e}}
    {%%}
""";

// aggregate literals
struct s_s { int a, b, c, d; }
struct t_s {
    int           arr[4]  = {1, 2, 3, 4};       // exact size required
    s_s           s1      = {.a=1, .b=2};       // unlisted fields take the type default
    list<s_s>     l       = { {.a=1}, {.b=2} }; // literals nest
    map<int,bool> m       = {1:true, 2:false};
    set<int>      e       = {};                 // empty: variable-size collections only
}
```

## Rules

### Comments and identifiers (§4.1–4.3)

- `//` to end of line; `/* ... */` block, non-nesting.
- Identifiers: letter or `_`, then letters, digits, `_`. Case-sensitive.
- Escaped identifiers start with `\` and end at whitespace, allowing otherwise-illegal
  characters.
- The 113 reserved keywords are listed in §4.4 and enumerated in `../../INDEX.md`.

### Numbers (§4.6)

- **Unsized decimal** — digits `1`–`9` then `0`–`9`.
- **Unsized hex** — `0x` / `0X` prefix.
- **Unsized octal** — leading `0`.
- **Unsized binary** — `0b` / `0B` prefix.
- **Sized** — `<width>'<base><digits>`, base one of `b B o O d D h H`.
- `_` may be used freely as a digit separator.
- Floating-point constants follow the usual `1.0`, `1e-3`, `1.5e+10` forms (§4.6.2).

### String literals (§4.7)

- **Quoted** (`"..."`) — printable ASCII only (0x20–0x7E), **single line**, with escapes:
  `\a \b \f \n \r \t \v \\ \" \' \? \ddd` (three octal digits). An escape followed by anything
  else is illegal. `\'` and `\?` are just the bare character.
- **Triple-quoted** (`"""..."""`) — **any** ASCII character, printing or not; no escape
  character; may span lines and contain single and double quotes (but not three consecutive
  `"`).
- Both may be used anywhere a string literal is wanted, **except**: a triple-quoted string whose
  special elements depend on non-constant expressions cannot be used where a *constant* string
  is expected.
- The empty literal `""` is the empty string. `string` variables are arbitrary-length.

### Special elements in triple-quoted strings (§4.7.1)

- **Mustache** `{{expression}}` — expanded when the string is evaluated. The expression must be
  of **scalar** type and may reference variables visible at the point of use; any function it
  calls must be **`pure`**.
- **Control-flow directives** `{% ... %}`, closed by `{%%}`:
  `if (expr)`, `else`, `else if (expr)`, `foreach ([it :] coll [[idx]])`, `repeat ([idx :] n)`.
  Expressions inside a directive are **not** wrapped in mustache. The directives themselves add
  no characters. `foreach` requires an iterator, an index, or both; for a `set` an index shall
  not be used; for a `map` the index is key-typed.
- **Comments** `{# ... #}` (multi-line) and `{#}` (to end of line) are removed from the result.
- Two usage contexts (§4.7.1.3):
  1. **target-template block** (target exec, target function, exec-file filename) — expanded
     **after the pre-body phase**;
  2. **string expression** **3.1** — expanded as part of evaluating the expression; anything
     referenceable in that context is referenceable in the mustache.
- A triple-quoted string referencing only constant expressions is itself a constant.
- **Mustache conversion formats** (§4.7.1.4): `int`→`%d`, `bit`→`%u`, `bool`→`"true"`/`"false"`,
  `enum`→the enumerator's identifier, `string`→`%s`, `chandle`→`%p`, `float32`/`float64`→`%f`.

### Aggregate literals (§4.8)

| Form | Syntax | Rules |
|---|---|---|
| Empty | `{}` | **variable-size collections only** (`list`, `set`, `map`) |
| Value list | `{e1, e2, …}` | arrays: **exact size required**; lists: sets the size; sets: duplicates counted once |
| Map | `{k1:v1, …}` | last value wins on a duplicate key |
| Struct | `{.a=1, .b=2}` | unspecified fields take the **type default**; order free; no duplicates |

- Elements need not be constant expressions.
- Literals nest.
- **An aggregate literal passed as an argument is a constant in the callee**, so the parameter
  must be declared `const`.

## Gotchas

**Array literal with the wrong element count.**
```pss
int c[4] = {1};        // WRONG: arrays require the exact size
list<int> l = {1};     // fine: sets the list size to 1
```
*Tier 2.*

**Aggregate literal argument against a non-`const` parameter.**
```pss
function void f(array<int,3> a);
f({1,2,3});            // WRONG: the literal is const
function void g(const array<int,3> a);
g({1,2,3});            // RIGHT
```
*Tier 2* — and the message is usually about parameter types, not constness.

**Struct literal silently defaulting a field.** `{.a=1}` leaves `b`, `c`, `d` at their **type**
defaults — which for an enum is *the first declared item*, not zero.
*Tier 4.*

**Leading zero making a decimal octal.**
```pss
bit[9] x = 0755;      // 493, not 755
```
*Tier 4.*

**Non-`pure` function in a mustache expression.** Illegal (§4.7.1.1) — and easy to hit, since
most helper functions are not marked `pure`.
*Tier 2.*

**Escaping inside a triple-quoted string.** There is no escape character; `\n` is a backslash
followed by `n`. That is usually what you want when emitting C, and a surprise otherwise.
*Tier 4.*

**Using a non-constant triple-quoted string where a constant is required** (e.g. a `static
const` initializer, an exec-file name that must be constant).
*Tier 2.*

**Expecting mustache to work in a quoted string.** It is a triple-quoted-string feature only.
*Tier 4* — the braces are emitted literally.

## See also

- `02-data-types.md` — what the literals are being assigned *to*, and type defaults.
- `03-collections.md` — sizing rules for `array` vs `list`.
- `../platform/05-core-library-api.md` — `format()`, `print()`, `message()` and printf
  specifiers.
- `../procedural/04-foreign-interface.md` — target templates, where mustache originated.
