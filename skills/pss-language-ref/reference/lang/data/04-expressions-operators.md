# Expressions and operators

*Domain: data. LRM Clause 8.*

The rules here apply **everywhere** — constraints, activity statements, procedural code, on
both the solve and the target platform (§8.7). They are the source of a whole class of tier-4
bugs: expressions that are legal, that solve, and that silently produce the wrong width.

## When you are writing this

- You are combining values of different widths or signedness.
- An arithmetic result is wrong and you suspect truncation.
- You need to know whether an unqualified enum item will resolve.
- You are writing a bit-select or part-select.

## Decide

| You want… | Write |
|---|---|
| membership in a set of values or ranges | `x in [1, 2, 4..8]` |
| membership in a collection | `x in coll` |
| a conditional value | `c ? a : b` |
| a specific bit | `x[3]` |
| a bit range | `x[7:0]` |
| a substring | `s[2..5]` |
| to force a width or signedness | an explicit cast — `(bit[8])x`, `(int)y` |
| a guaranteed-wide result | **widen an operand first**; the result width is *not* taken from the destination in a way that helps you |

## Canonical form

```pss
struct s_s {
    rand bit[8]  a;
    rand bit[16] b;
    rand int     c;
    rand bool    f;
    rand mode_e  m;

    constraint {
        a in [1, 2, 4..8];               // set membership over ranges
        b == (a << 4);                   // shift: result type is the LHS type — bit[8]!
        b == ((bit[16])a << 4);          // ...so widen first
        c == (f ? 10 : 20);
        m != UNKNOWN;                    // unqualified: expected type is mode_e
        a[3] == 1;                       // bit-select
        b[7:0] == a;                     // part-select
    }
}
```

## Rules

### Precedence (§8.4.1), highest first

| Precedence | Operators | Assoc |
|---|---|---|
| 1 | `()` `[]` | left |
| 2 | cast, unary `-` `!` `~` `&` `\|` `^` | **right** |
| 3 | `**` | left |
| 4 | `*` `/` `%` | left |
| 5 | binary `+` `-` | left |
| 6 | `<<` `>>` | left |
| 7 | `<` `<=` `>` `>=` `in` | left |
| 8 | `==` `!=` | left |
| 9 | binary `&` | left |
| 10 | binary `^` | left |
| 11 | binary `\|` | left |
| 12 | `&&` | left |
| 13 | `\|\|` | left |
| 14 | `?:` | **right** |

All left-associative except the cast and conditional operators.

### Short-circuiting (§8.4.4)

`&&`, `||` and `?:` short-circuit — operands not needed to determine the result **are not
evaluated**. Never rely on a side effect in the right operand.

### Numeric expression types (§8.7.1)

This is the important table. A *self-determined* expression's type comes from itself; a
*context-determined* one also depends on where it is used.

| Operators | Result type | Propagation to operands |
|---|---|---|
| `+ - * / %`, and `?:` with two numeric operands | any float operand → `float64`; else bit size = **larger of the two**, signed only if **both** are signed | propagated to both operands; a float/integer mix converts the integer *after* self-determination |
| `**` | any float operand → `float64`; else **same as the left-hand operand** | propagated to the LHS; **RHS is self-determined** |
| `& \| ^` (binary) | bit size = larger of the two; signed only if both are | propagated to both |
| `<< >>` | **same as the left-hand operand** | propagated to LHS; **RHS is self-determined** |
| `== != < <= > >=` | `bool` | same propagation rules as binary arithmetic |
| `&& \|\| !` | `bool` | all operands **self-determined** |
| unary `+ - ~` | same as the operand | propagated to the operand |
| unary reduction `& \| ^` | `bit` | operand self-determined |
| `in` | `bool` | integer sides propagate to the larger/less-signed type; float/integer mixes convert the integer side |

Value conversion when a context-determined integer operand changes type: **sign-extend if the
propagated type is signed, zero-extend if unsigned**.

### Assignment-like contexts (§8.7.2)

These convert a source expression to a **target type**: the assignment operator, the cast
operator, function-call actual parameters (**not** generic parameters — those are
self-determined), `return`, value-list and map literal elements (when there is a context type),
template value parameters, and a typed `coverpoint` expression.

In such a context:

- a floating-point source is **self-determined**;
- a floating-point target makes the source **self-determined**;
- otherwise, if the target's bit size is **larger**, that size propagates to the source —
  **signedness does not**, it stays self-determined.

Conversion itself: integer→integer truncates or extends (sign-extend if the *source* is signed,
zero-extend if unsigned); integer→float converts the value; **float→integer treats the value as
signed and truncates the fraction**.

### Type inference / expected type (§8.4.3)

The *expected type* drives unqualified enum-item resolution and aggregate-literal
interpretation. It comes from: the LHS of an assignment (including initializers); a function's
formal parameter type (also for covergroup instantiation); a function's return type; the LHS of
`==`/`!=`; the expected type of a `?:`; the LHS of `in`; a coverpoint's declared type; a
coverpoint's type for its bin values; the target type of a cast.

For this purpose **all numeric types count as one type**.

### Aggregate literals in expressions (§8.4.2)

Usable as operands — initializers, constraints, foreign-function parameters, template value
parameters. **An aggregate literal may not be the target of an assignment.** In an assignment
or equality against a struct variable, unspecified fields take the element type's default.

### Primary expressions (§8.6)

- **Bit-select** `x[i]`, **part-select** `x[msb:lsb]`.
- **Indexing** `coll[i]` (see `03-collections.md`).
- **Sub-string** `s[a..b]`, `s[..b]`, `s[a..]`, `s[i]` — never an assignment target.

### Constant expressions (§8.2)

May use numeric and string literals, constant aggregate literals, named constants
(`static const`, template parameters), bit/part-selects of named constants, enum items, and
**`pure` function calls with constant arguments**.

### Assignment operators (§8.3)

`=` everywhere; `+= -= <<= >>= |= &=` in **procedural statements only**, never inside an
expression.

## Gotchas

**Shift result truncated to the left operand's width.** The single most common width bug.
```pss
bit[8] a; bit[16] b;
b = a << 4;              // WRONG: the shift is done in bit[8]; the top bits are gone
b = ((bit[16])a) << 4;   // RIGHT
```
*Tier 4.* Same shape for `**`: the RHS is self-determined and the result takes the LHS type.

**Mixed signedness silently going unsigned.**
```pss
int  s = -1;
bit[8] u = 1;
if (s < u) { ... }       // both operands become UNSIGNED — -1 compares as huge
```
*Tier 4.* Cast explicitly when signedness matters.

**Assuming the destination width widens the computation.** It does propagate a *larger* target
bit size to the source — but not signedness, and not through a self-determined sub-expression.
Widen the operand, not the result.
*Tier 4.*

**Unqualified enum item where no enum type is expected.**
```pss
enum color_e {RED, GREEN, ORANGE};
function void print_num(int n);
print_num((int)ORANGE);              // WRONG: expected type is int, ORANGE unresolved
print_num((int)color_e::ORANGE);     // RIGHT
```
*Tier 1* — reported as an unknown identifier.

**Ambiguous struct literal.** The literal's meaning comes from the expected type. In a scope
where two struct types both have an `a` field, the LHS decides — check it before assuming.
*Tier 4.*

**Side effect in a short-circuited operand.**
```pss
if (ptr != 0 && init(ptr)) { ... }   // init() may never run
```
*Tier 4.*

**Compound assignment inside an expression.**
```pss
x = (y += 1);        // WRONG: procedural statement only
```
*Tier 1.*

**Float → int silently truncating.** No warning, no rounding.
*Tier 4.*

**`&` as a reduction vs binary.** Unary `&x` reduces to a single `bit`; binary `a & b` is
bitwise. Precedence 2 vs 9 — parenthesize when mixing.
*Tier 4.*

## See also

- `02-data-types.md` — the types being combined, and cast rules.
- `03-collections.md` — indexing and `in` over collections.
- `01-lexical-and-literals.md` — aggregate literals.
- `../constraints/01-algebraic-constraints.md` — the same rules inside constraints.
- `../platform/04-registers.md` — where a width mistake becomes a wrong bus transaction.
