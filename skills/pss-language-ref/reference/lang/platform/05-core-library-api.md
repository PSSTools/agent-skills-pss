# Core library: `std_pkg`

*Domain: platform. LRM §21.1–21.6.*

The core library is three packages:

| Package | Covers | Page |
|---|---|---|
| `std_pkg` | formatting, output, messages, files, errors, randomization, floating point, standard annotations | **this page** |
| `executor_pkg` | execution contexts and assignment | `01-executors.md` |
| `sync_pkg` | target-time channels | `02-sync-and-communication.md` |
| `addr_reg_pkg` | address spaces, allocation, memory access, registers | `03-address-spaces.md`, `04-registers.md` |

The interfaces are specified in PSS terms; the implementations are the tool's.

## When you are writing this

- You need to print, log, or report an error.
- You need a random value at runtime.
- You need to read or write a file during generation.
- You are doing floating-point arithmetic.

## Decide

| You need… | Use | Platform |
|---|---|---|
| a formatted string during generation | `format(fmt, …)` | **solve** (`pure`) |
| to print during generation | `print(fmt, …)` | **solve** |
| a log line from the generated test | `message(vrb, fmt, …)` | **both** **3.1** |
| to report a problem | `error(fmt, …)` | both |
| to abort | `fatal(status, fmt, …)` | both |
| a random 32-bit value | `urandom()` / `urandom_range(min,max)` | both |
| to read/write a file | `file_*` | **solve** |
| float arithmetic | `float32`/`float64` + the computation functions | both |
| a bit-exact float layout | `float32_s` / `float64_s` / `float_base_s<Wm,We,E>` | both |
| documentation metadata | `@doc` / `@code_doc` | — |

**`format()` vs `message()`** is the decision that goes wrong: `format()` and `print()` are
**solve-platform only** — they cannot appear in `exec body`. `message()` is the target-side (and,
in 3.1, also solve-side) logging call.

## Canonical form

```pss
import std_pkg::*;

component c_c {
    target function int my_func();

    action a {
        rand int x;

        exec post_solve {
            print("solving x=%d\n", x);                 // solve only
            string s = format("x is %d", x);            // solve only, pure
        }

        exec body {
            int y = comp.my_func();
            message(LOW, "x=%d y=%d", x, y);            // format string known at solve time
            if (y > 1000) { error("y too large: %d", y); }
            bit[32] r = urandom_range(0, 15);
        }
    }
}
```

## Rules

### String formatting and output (§21.1.1, §21.1.2)

```pss
solve pure function string format(string format_str, type... args);
solve      function void   print (string format_str, type... args);
```

Specifier: `%[flags][width][.precision]fmt`; `%%` is a literal `%`.

- **Flags** — `-` left justify; `+` force sign; *space* leading space for non-negative numbers;
  `#` prefix `0`/`0x`/`0X`/`0b`/`0B` for `o x X b B`, or force a decimal point for floats;
  `0` zero-pad numerics.
- **width** — minimum characters; **never truncates**.
- **precision** — minimum digits for integer formats (zero-padded; `.0` prints nothing for the
  value 0); digits after the point for `e E f`; maximum significant digits for `g G`; **maximum
  characters** for `s` and `n` (truncated from the right). An empty precision (`%.d`) means 0.

| fmt | Meaning |
|---|---|
| `d` | signed decimal |
| `u` | unsigned decimal |
| `x` / `X` | unsigned hex, lower / upper |
| `o` | unsigned octal |
| `b` / `B` | unsigned binary |
| `f` | float decimal |
| `e` / `E` | float scientific |
| `g` / `G` | float, shortest of the two |
| `n` | enum item **name**, or `"false"`/`"true"` |
| `s` | string |
| `p` | `chandle` pointer in hex, including `0x` |

Errors: an invalid specifier; a mismatch between specifier count and argument count; a type with
no applicable implicit conversion. Implicit conversions **are** applied (`%d` on unsigned, `%f`
on an integer, `%d` on a float) — **except that unsigned formats (`%u %x %X %o %b %B`) are
illegal for floating-point values**.

### Message logging (§21.1.3)

```pss
package std_pkg {
    enum message_verbosity_e { NONE, LOW, MEDIUM, HIGH, FULL };
    function void message(message_verbosity_e vrb_level, string format_str, type... args);
}
```

- **In 3.1 `message()` is unqualified — available on both the solve and target platforms.**
  **3.1**
- A message is issued only if its level is at or below the run's verbosity. `NONE` is critical
  and always issued; `FULL` is issued only in a `FULL` run.
- **In restricted target environments, restrictions may apply to `vrb_level` and `format_str`**
  when called from a target exec — target memory requirements for string operations. In
  practice: keep the verbosity, the format string, and any **string** arguments **solve-time
  known**; numeric arguments may be runtime values.
- **If expressions with side effects (non-`pure` calls) are passed, their evaluation is not
  guaranteed** — verbosity gating may elide them. **Never pass an argument with a side effect.**

### File operations (§21.2) — solve platform

```pss
package std_pkg {
    typedef chandle file_handle_t;
    static const file_handle_t nullfilehandle = /* implementation-specific */;
    enum file_option_e { TRUNCATE, APPEND, READ };

    solve function file_handle_t file_open(string filename, file_option_e opt);
    solve function void          file_close(file_handle_t h);
    solve function bool          file_exists(string filename);
    solve function void          file_write(file_handle_t h, string fmt, type... args);
    solve function string        file_read(file_handle_t h, int size = -1);

    solve function void         file_write_lines(string filename, list<string> lines,
                                                 file_option_e opt);
    solve function list<string> file_read_lines(string filename);
}
```

- `TRUNCATE` — discard existing content, allow writes. `APPEND` — allow writes, appending.
  `READ` — allow reads.
- `file_open`/`file_write`/`file_read`/`file_close` **trigger an error if the operation cannot
  be performed**.
- `file_write_lines` adds a newline after each string; `opt` must be `TRUNCATE` or `APPEND`, and
  with `APPEND` a newline is inserted before the new content unless the file already ends with
  one.

### Error reporting (§21.3)

```pss
function void error(string format_str, type... args);
function void fatal(int status, string format_str, type... args);
```

- Both insert the formatted text plus a newline into the solving or execution log.
- **`format_str` shall be a string expression whose value is known at solve time**, as for
  `message()`.
- `fatal()` terminates the solve or the run at the nearest possible point, returning `status`.
  `error()` may or may not terminate, per tool or session policy.

### Randomization (§21.4)

```pss
function bit[32] urandom();
function bit[32] urandom_range(bit[32] min, bit[32] max);
```

Available on both platforms — with scalar-integer `randomize`, the only randomization usable
inside a target exec.

### Floating point (§21.5)

**Storage types** (§21.5.1) — packed layouts, for memory images and foreign interfaces:

```pss
struct float_base_s <int Wm, int We, endianness_e E = LITTLE_ENDIAN> : packed_s<E> {
    rand bit[Wm] mantissa;
    rand bit[We] exponent;
    rand bit     sign;
}
typedef float_base_s<23, 8>  float32_s;
typedef float_base_s<52, 11> float64_s;
```

**Computation functions** (§21.5.2) — `log`, `log10`, `exp`, `sqrt`, `pow`, `round`, `floor`,
`ceil`, `sin`, `cos`, and the rest of the C math library set. **All take and return `float64`**,
and behave as the C standard function of the same name.

- **Floating-point functions may not be used in constraints.**
- **Arithmetic is done on the computation types `float32`/`float64` only** — convert a storage
  value before computing (§21.5.3 covers extraction and composition).
- `float32`/`float64` are never `rand` and results are not guaranteed identical across platforms
  (§7.3.2).

### Standard annotations (§21.6)

```pss
package std_pkg {
    annotation code_doc { string text; }   // implementation-level; may become a target comment
    annotation doc      { string text; }   // model-level; extracted by tools
}
```

See `../data/05-annotations.md`.

## Gotchas

**`format()` or `print()` in `exec body`.** Both are `solve` functions.
```pss
exec body { print("x=%d\n", x); }               // WRONG
exec body { message(LOW, "x=%d", x); }          // RIGHT
```
*Tier 2.*

**A target-computed string passed to `message()`.**
```pss
exec body { string s = get_name(); message(LOW, "%s", s); }   // WRONG if s isn't solve-known
```
*Tier 2–4*, depending on the target environment. Numbers are fine; strings must be solve-known.

**A side-effecting argument to `message()`.**
```pss
message(FULL, "count=%d", next_count());   // may never be evaluated
```
*Tier 4.*

**Unsigned format on a float.** `%x` on a `float64` is an error, unlike the other implicit
conversions.
*Tier 2.*

**Specifier/argument count mismatch.** An error, but one a shallow tool will not catch.
*Tier 2–4.*

**Expecting `%s` precision to pad.** For `s` and `n`, precision is a **maximum**, truncating
from the right — the opposite of the integer behaviour.
*Tier 4.*

**A float function in a constraint.** Not permitted (§21.5.2).
*Tier 2.*

**Arithmetic on a storage type.** `float32_s` is a packed struct of mantissa/exponent/sign, not
a number. Convert to `float32`/`float64` first.
*Tier 2.*

**`error()` assumed to abort.** It may or may not, per tool policy. Use `fatal()` when you need
the run to stop.
*Tier 4.*

**File operations in a target exec.** All `solve` functions.
*Tier 2.*

**`file_read`/`file_open` failures ignored.** They raise an error rather than returning a
sentinel — do not write recovery code around them expecting a `null` handle.
*Tier 4.*

## See also

- `../data/01-lexical-and-literals.md` — mustache interpolation, the other formatting mechanism.
- `../data/05-annotations.md` — `doc` and `code_doc`.
- `../data/02-data-types.md` — `float32`/`float64`, `chandle`.
- `../procedural/01-exec-blocks.md` — which exec kinds these are legal in.
- `04-registers.md` — `packed_s`, which the float storage types build on.
