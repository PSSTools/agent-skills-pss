# Data coverage: `covergroup`

*Domain: coverage. LRM Clause 15.*

Answers "which **values** did we hit?".

## When you are writing this

- The user said "make sure we cover all the sizes / modes / combinations".
- The user wants evidence that a randomized model actually explored its space.
- The user wants a value flagged as *never legal* — `illegal_bins`.
- A coverage report is at 100% and you suspect it means nothing.

## Decide

| You want… | Write |
|---|---|
| coverage of one attribute, here only | in-line `covergroup { coverpoint x; } cg;` |
| the same coverage model reused in several places | named `covergroup cg_t(port …) { … }` + instantiation |
| combinations of two or more values | `cross` |
| specific meaningful value groups | explicit `bins` |
| values excluded from the metric | `ignore_bins` |
| values that must never occur | `illegal_bins` — a **runtime error** if hit |
| coverage only under a condition | `iff (expr)` |
| separate results per component/pool instance | `option.per_instance = true;` |

**A reusable covergroup type must take formal parameters and must not reference fields of the
scope it is declared in.** An in-line covergroup may reference the enclosing scope. That
requirement is the practical dividing line between the two forms.

**Explicit bins are almost always required.** Auto bins for a `bit[32]` coverpoint mean nothing
— see the rules below.

## Canonical form

```pss
enum mode_e { M0, M1, M2 }

// reusable: parameterized, references nothing from its declaring scope
covergroup mode_cg(mode_e m, bit[16] len) {
    option.at_least = 2;

    md : coverpoint m;                      // enum: auto bins are fine here
    ln : coverpoint len {
        bins small[]  = [1..64];            // one bin per value
        bins medium   = [65..1023];         // one bin for the range
        bins large[4] = [1024..4096];       // four bins spanning the range
        ignore_bins   unused = [0];
        illegal_bins  bad    = [4097..];
    }
    md_x_ln : cross md, ln;
}

action xfer {
    rand mode_e  mode;
    rand bit[16] len;

    mode_cg cg(.m(mode), .len(len)) with { option.comment = "per-xfer"; };

    // in-line form: may reference the enclosing scope directly
    covergroup {
        option.per_instance = true;
        coverpoint len iff (mode != M0) {
            bins aligned = [4, 8, 16, 32, 64];
        }
    } inline_cg;
}
```

## Rules

### Declaration and instantiation (§15.1, §15.2)

- Two forms:
  - **explicit type** — declarable in a package, component, action, monitor, or struct.
    **To be reusable it shall specify formal parameters and shall not reference fields in its
    declaring scope.** Instantiable in an action, monitor, or struct.
  - **in-line** — declarable in an action, monitor, or struct; **may** reference fields of that
    scope; produces an anonymous type and a single instance.
- A covergroup contains coverpoints, crosses, and options.
- Instantiation binds ports by name (`.m(mode)`) or positionally, and may set instance options
  with `with { … }`.

### Coverpoints (§15.3)

- `[[data_type] label :] coverpoint expression [iff (expr)] { … }`
- The expression must be **integer or enum**.
- The coverpoint expression **and its `iff` condition are evaluated when the covergroup is
  sampled**.
- A labelled coverpoint creates a hierarchical scope; the label is what a `cross` refers to.

### Bins (§15.3.3)

```
(bins | ignore_bins | illegal_bins) name [ [ [count] ] ] = range_list [with (expr)] ;
```

- `bins name = [a..b];` — **one bin** for the whole range.
- `bins name[] = [a..b];` — **one bin per value**.
- `bins name[N] = [a..b];` — a fixed **N** bins spanning the values.
- `bins name = default;` — everything not otherwise covered.
- `with (expr)` filters the values, and may also derive bins from another coverpoint.

### Automatic bins (§15.3.4)

If a coverpoint defines no bins, the tool creates **N** bins:

- **enum** — N is the cardinality of the enumeration (good).
- **integer** — N is `min(2^M, auto_bin_max)` where M is the coverpoint's bit width, and
  `auto_bin_max` **defaults to 64**.

If N < 2^M, the values are distributed uniformly, with the **last bin taking the remainder**.

So a `bit[32]` coverpoint with no bins gets 64 bins of ~67 million values each. It will read
100% covered and tell you nothing.

### `ignore_bins` / `illegal_bins` (§15.3.5, §15.3.6)

- Both **remove their values from every other bin**, and the removal happens **after**
  distribution into bins. A bin left with no values is excluded from coverage.
- **`illegal_bins` takes precedence over all other bins** and raises a **runtime error** if hit
  — even when the value also appears in another bin.

### Value resolution (§15.3.7)

- Without an explicit coverpoint type, the coverpoint expression's effective type is
  **self-determined**; with one, it is the declared coverpoint type.
- Bin expressions are **statically cast** to the coverpoint's effective type; implementations
  warn on the lossy cases.

### Cross coverage (§15.4)

- `label : cross cp1, cp2 [, …] [iff (expr)] …`
- **A cross involves only coverpoints.** Crossing a *variable* implicitly creates
  `coverpoint V;` for it. **Expressions may not be used directly in a cross** — define the
  coverpoint first.
- Cross bins may be declared explicitly (§15.4.3).

### Options (§15.5)

Instance-specific, settable per covergroup / coverpoint / cross. A covergroup-level option
applies to all its items unless overridden. **Specifying the same option twice in one scope is
an error.**

| Option | Default | Meaning |
|---|---|---|
| `weight` | 1 | relative weight in the enclosing coverage computation |
| `goal` | 100 | target goal |
| `name` | tool-generated | instance name |
| `comment` | `""` | saved in the database and report |
| `at_least` | 1 | minimum hits before a bin counts as covered |
| `detect_overlap` | false | warn when two bins' ranges overlap |
| `auto_bin_max` | **64** | maximum automatically created bins |
| `per_instance` | false | collect separately per instance (§15.7) |

### Sampling (§15.6)

- **Coverage credit is taken once the action containing the covergroup instance completes.** By
  default, every covergroup instance created by an action traversal is sampled at that action's
  completion.
- Sampling in monitors is different — see `02-behavioral-coverage.md` §16.5.1.

### Per-type and per-instance collection (§15.7)

- With `option.per_instance = true` on a covergroup in a **flow or resource object**, coverage
  is collected per **pool** — all executions exchanging objects through that pool land in one
  collection associated with the pool.
- Per-instance coverage in actions is collected per component instance (§15.7.2).

## Gotchas

**No bins on a wide integer coverpoint.**
```pss
coverpoint addr;            // bit[32]: 64 auto bins, each ~67M values — meaningless
coverpoint addr { bins low = [0..0xFFFF]; bins high[8] = [0x1_0000..]; }   // RIGHT
```
*Tier 4* — the headline number is the lie.

**Sampling a value that isn't resolved yet.** Anything computed in `exec body` is invisible to
the solve and to sampling (§13.4.13). Cover solved attributes.
*Tier 4.*

**Using an expression directly in a `cross`.**
```pss
cross len, (addr % 64);       // WRONG
a64 : coverpoint addr % 64;  cross len, a64;   // RIGHT
```
*Tier 1–2.*

**A reusable covergroup referencing its declaring scope.** Not allowed for the reusable form —
parameterize it.
*Tier 2.*

**`illegal_bins` used as a constraint.** It does not prevent the value; it errors **at
runtime** if it occurs. If the value must never be generated, that is a constraint. Use both if
you want the constraint *and* a check that it held.
*Tier 4.*

**`ignore_bins` overlapping a bin you care about.** Ignored values are removed from *every*
bin, after distribution — so an `ignore_bins` can silently empty a named bin, which is then
excluded from coverage entirely.
*Tier 4.*

**Overlapping bins counted twice.** Turn on `option.detect_overlap` while developing.
*Tier 4.*

**Expecting `at_least` to be per-value.** It is a per-**bin** hit threshold.
*Tier 4.*

**Setting the same option twice in one scope.** An error (§15.5), including when instantiating.
*Tier 2.*

## See also

- `02-behavioral-coverage.md` — covering *scenarios* instead of values.
- `../constraints/01-algebraic-constraints.md` — producing the values you want to cover.
- `../data/04-expressions-operators.md` — coverpoint expression typing and the cast in value
  resolution.
- `../structural/06-pools-and-binding.md` — pools, which are the unit of per-instance flow-object
  coverage.
- `../../playbooks/08-add-coverage.md` — task-first.
