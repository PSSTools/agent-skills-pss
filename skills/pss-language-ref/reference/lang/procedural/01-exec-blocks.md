# Exec blocks

*Domain: procedural. LRM §20.1, §20.5.*

An `exec` block is where realization code lives. **Which kind you choose decides which platform
it runs on and what it may touch** — get that wrong and nothing else in the block matters.

## When you are writing this

- You have an atomic action and need to say what it actually does.
- You need to set component attributes during elaboration.
- You need to compute a derived value from solved values.
- You need `#include`s or globals in the generated file.
- You need to emit target-language text rather than call a function.

## Decide

| You need to… | Exec kind | Platform |
|---|---|---|
| set component attributes, parent first | `init_down` | solve |
| set component attributes, children first | `init_up` | solve |
| initialize non-`rand` fields the solve will read | `pre_solve` | solve |
| compute non-`rand` fields from solved values | `post_solve` | solve |
| use executor assignment or resolved addresses | `pre_body` | solve |
| implement the action | `body` (**actions only**) | target |
| bring the test up / tear it down, once | `run_start` / `run_end` | target |
| emit `#include`s or forward declarations | `header` (**template only**) | target |
| emit globals or helper definitions | `declaration` (**template only**) | target |
| write to a named generated file | `exec file "<name>" = """…"""` | target |

**Procedural vs target template.** `exec body { … }` is PSS code the tool compiles;
`exec body C = """…"""` is text the tool emits. Use the procedural form unless you genuinely
need to produce code the environment has no function for.

## Canonical form

```pss
component dma_c {
    bit[32] base_addr;

    exec init_up { base_addr = 0x1000; }        // elaboration; solve platform

    action xfer {
        rand bit[16] size;
        bit[32]      addr;                      // derived

        exec pre_solve  { addr = 0; }
        exec post_solve { addr = alloc_addr(size); }
        exec pre_body   { /* executor() and addr_value_solve() are legal here */ }
        exec body       { poke(addr, size); }   // target platform
    }

    action emit {
        rand bit[1:0] func_id;
        rand bit[3:0] a;
        exec header C = """ #include "dut.h" """;
        exec body   C = """
            func_{{func_id}}({{a}});   {#} mustache selects the C function by id
        """;
    }
}
```

## Rules

### Syntax (§20.1.1)

```
exec_block_stmt        ::= exec_block | target_code_exec_block | target_file_exec_block | ;
exec_block             ::= exec exec_kind { { exec_stmt } }
exec_kind              ::= pre_solve | post_solve | pre_body | body | header | declaration
                         | run_start | run_end | init_down | init_up | init
exec_stmt              ::= procedural_stmt | super ;
target_code_exec_block ::= exec exec_kind <language_identifier> = [tag :] "string" ;
target_file_exec_block ::= exec file <filename_string> = [tag :] "string" ;
```

- **A given exec block maps to at most one foreign language.**
- **Multiple same-kind exec blocks in one definition scope act as one block**, processed in
  source order.
- **`exec init` is a deprecated alias for `exec init_up`.** Use `init_up`.

### Kinds, in evaluation order (§20.1.2, §20.1.5)

| Kind | Scopes | Platform | Notes |
|---|---|---|---|
| `init_down` | component | solve | parent before children; runs **before the root action's `pre_solve`**; **may not call target-template functions** |
| `init_up` | component | solve | all children before parent |
| `pre_solve` | action, flow/resource object, struct | solve | initialize non-random fields; **handle-type fields are null here** |
| `post_solve` | action, flow/resource object, struct | solve | compute non-`rand` fields from solved values |
| `pre_body` | action, flow/resource object, struct | solve | after executor assignment and address allocation; may call solve functions plus `executor()`, `addr_value_solve()`, `addr_value_abs()` |
| `body` | **action only** | target | the runtime implementation. Bodies of actions with the same scheduling dependencies logically run at the same time |
| `run_start` / `run_end` | action, flow/resource object, struct | target | non-time-consuming; before any body / after all bodies. Pre-generation flow only |
| `header` | action, flow/resource object, struct | target | **target template only** |
| `declaration` | action, flow/resource object, struct | target | **target template only** |

**Sibling `init_down`/`init_up` order is undefined.** A legal interleaving is
`T.init_down, c1.init_down, c1.init_up, c2.init_down, c2.init_up, T.init_up`.

### Platform rules (§20.2.1.3)

- A **`solve function` shall not be called** — directly or transitively — **from `body`,
  `run_start`, `run_end`**.
- A **`target function` shall not be called from `init_down`, `init_up`, `pre_solve`,
  `post_solve`, `pre_body`**.
- An **unqualified** function is available in both.

### Inheritance, `super`, extension (§20.1.4)

- **exec blocks are virtual**: a derived type's same-kind exec **fully replaces** the base's.
- **`super;`** evaluates the base type's same-kind exec at that point. **Procedural execs only —
  illegal in a target template.**
- **Type extension is additive**: the initial definition's execs run first, then the extensions',
  in **tool-determined order among extensions**.

```pss
action A  { exec body { message(LOW, "A"); } }
action A1 : A { exec body { super; message(LOW, "A1"); } }   // A then A1
action A2 : A { exec body { message(LOW, "A2"); super; } }   // A2 then A
extend action A1 { exec body { message(LOW, "ext"); } }      // appended: A, A1, ext
```

### Target-template exec blocks (§20.5)

- `exec <kind> <LANG> = """ … """;` emits text into the generated test.
- `exec file "<name>" = """ … """;` emits into a named file. Untagged blocks targeting the same
  file are **concatenated in scenario flow order**.
- **Mustache** `{{expression}}` references variables visible in the declaring scope. **Only
  scalars (except `chandle`)** may be referenced. A reference may appear anywhere, including
  inside an identifier (`func_{{id}}({{a}});`), and **can never be assigned to**.
- Conversion formats: `int`→`%d`, `bit`→unsigned decimal, `bool`→`"true"`/`"false"`,
  `enum`→the item name, `string`→`%s`, `chandle`→`%p`, floats→`%f`.
- Control-flow directives `{% if %}`, `{% foreach %}`, `{% repeat %}`, closed by `{%%}` — see
  `../data/01-lexical-and-literals.md`.
- Comments `{# … #}` and `{#} …` do not reach the target code.
- **Expansion happens after the `pre_body` phase completes.**
- **`super;` is illegal in a target-template exec**, and so is `compile if` inside a
  target-template exec body.

### Exec block tags **3.1** (§20.5.4)

```
exec_block_tag ::= type_identifier [struct_literal]
```

A tag lets the tool **deduplicate generated code** across exec blocks that would otherwise emit
the same text from many objects. It affects **code generation only** — not traversal, solving,
or runtime execution.

- Permitted on target-template exec blocks of kind **`header`, `declaration`, `run_start`,
  `run_end`**, and on **`exec file`** blocks. **Not permitted** on native exec blocks, on `body`
  (which is per-traversal), or on any solve exec.
- The tag is a **struct type**, optionally with a struct literal. It is evaluated using a
  temporary instance constructed **after `exec pre_body`**, initialized from the literal or from
  field defaults. **The instance does not participate in randomization, and its own exec blocks
  are not evaluated.**
- **Matching** (§20.5.4.1) — two exec blocks match when they have the same `exec_kind`, the same
  language, the same tag struct **type**, and **equal** evaluated tag values (per §8.5.3). For
  `exec file` blocks: matching filename, tag type, and tag value.
  - **Tag values of different struct types never match.**
  - **An untagged exec block matches nothing — including other untagged blocks.**
  - Matching is **independent of declaration scope**: blocks in different actions or components
    may match.
- **Within one instantiated object, multiple matching blocks are concatenated in declaration
  order.**
- On generation: if a matching block from a **different** instantiated object was already
  generated, the new text is compared **character by character**. Identical ⇒ suppressed.
  **Not identical ⇒ an error is reported.**
- Tagged and untagged `exec file` contributions coexist; the final file is the concatenation of
  all contributions in source order.

## Gotchas

**Platform crossing.**
```pss
exec body       { addr = alloc_addr(size); }   // WRONG: solve function in a target exec
exec post_solve { poke(addr, size); }          // WRONG: target function in a solve exec
```
*Tier 2* — invisible to a parser, which is why it is rule 1 in `SKILL.md`.

**Writing a component attribute from an action's exec.** Only `init_down`/`init_up` may
(§9.1.6), unless the field is `mutable` **3.1**.
*Tier 2.*

**Forgetting `super;` in a derived exec.** The base's `exec body` is **replaced**, so its
behaviour silently disappears.
*Tier 4* — the most damaging exec gotcha in PSS.

**Relying on extension order.** Two extensions each adding an `exec body` produce a
tool-dependent sequence.
*Tier 4.*

**Relying on sibling init order.** Undefined (§20.1.5).
*Tier 4.*

**Accessing a handle field in `pre_solve`.** `input`/`output`, `lock`/`share`, and action
handles are **null** before randomization completes.
*Tier 2–3.*

**`exec body` on a compound action.** Mutually exclusive with `activity` (§9.2.1a).
*Tier 2.*

**`exec body` on a struct or object.** `body` is **actions only**.
*Tier 1–2.*

**Procedural statements in `header`/`declaration`.** Those are **target-template only**.
*Tier 1–2.*

**Assigning to a mustache reference.** Template references are read-only. If you need to write a
PSS variable from the target side, you need an imported function.
*Tier 2.*

**A non-scalar in a mustache expression.** Only scalars, and not `chandle`.
*Tier 2.*

**`super;` in a target template.** Illegal.
*Tier 1–2.*

**Expecting an untagged exec to be deduplicated.** Untagged blocks match nothing and are emitted
every time.
*Tier 4* — duplicate `#include`s and duplicate globals in the generated file.

**A tagged exec whose text differs between instances.** Matching tags with **non-identical**
generated text is an **error**, not a silent pick. If the text legitimately varies, the tag must
vary with it — put the varying values in the tag struct.
*Tier 3.*

**Using `exec init`.** Deprecated alias for `init_up`.
*Tier 4.*

## See also

- `02-functions.md` — platform qualifiers, and what may be called from where.
- `03-procedural-statements.md` — what may go inside a procedural exec.
- `04-foreign-interface.md` — target templates, imported and exported functions in full.
- `../data/01-lexical-and-literals.md` — mustache and triple-quoted strings.
- `../constraints/03-randomization.md` §13.4.12 — `pre_solve`/`post_solve` evaluation order.
- `../structural/02-components.md` — `init_down`/`init_up` and component mutability.
