# Foreign interface: imports, exports, target templates

*Domain: procedural. LRM §20.4, §20.5, §20.6, §20.9, §20.10.*

Four ways to connect PSS to code that isn't PSS.

## When you are writing this

- The user said "call my C function", "drive the BFM", "emit this SystemVerilog".
- You need `#include`s, globals, or assembly in the generated test.
- Foreign code needs to request PSS-generated stimulus.
- You need to read a value back from the DUT into the scenario.

## Decide

| The need | Mechanism | Clause |
|---|---|---|
| portable computation, reusable everywhere | **native PSS function** | §20.3 |
| call an existing C/C++/SV API and get a value back | **imported function** | §20.4 |
| emit code the environment has no function for — assembly, globals, `#include`s | **target template** exec or function | §20.5, §20.6 |
| let foreign code request PSS stimulus | **exported action** | §20.10 |
| let foreign code call a PSS function | **exported function** | §20.4.2 |

The ordering is a preference ordering. A native function is portable and checkable; an import is
a real call with typed parameters; a template is untyped text. **Drop down only when the level
above cannot express it.**

## Canonical form

```pss
// --- imported functions ------------------------------------------------
package external_functions_pkg {
    function bit[31:0] alloc_addr(bit[31:0] size);
    function void      transfer_mem(bit[31:0] src, bit[31:0] dst, bit[31:0] size);
}
package pregen_tests_pkg {
    import solve  function external_functions_pkg::alloc_addr;
    import target function external_functions_pkg::transfer_mem;
}
package known_c_functions {
    import C function generic_functions::compute_expected_value;
}

// --- reading DUT state back into the scenario ---------------------------
component my_ip_c {
    import target C function int sample_DUT_state();

    action check_state {
        int curr_val;
        exec body { curr_val = comp.sample_DUT_state(); }
    }
    action A {} action B {}
    action my_test {
        check_state cs;
        activity {
            repeat {
                cs;
                if (cs.curr_val % 2 == 0) { do A; } else { do B; }
            } while (cs.curr_val < 10);
        }
    }
}

// --- target templates ----------------------------------------------------
component top {
    action A {
        rand bit[1:0] func_id;
        rand bit[3:0] a;
        exec header C = """ #include "dut.h" """;
        exec body   C = """
            func_{{func_id}}({{a}});   {#} chooses the C function by id
        """;
    }
}

package thread_ops_asm_pkg {
    target ASM function void do_stw(bit[31:0] val, bit[31:0] vaddr) = """
        loadi RA {{val}}
        store RA {{vaddr}}
    """;
}

// --- exported action -----------------------------------------------------
component comp_c {
    action A1 {
        rand bit       mode;
        rand bit[31:0] val;
        constraint { if (mode != 0) { val in [0..10]; } else { val in [10..100]; } }
    }
}
package pkg { export target comp_c::A1(bit mode); }
```

## Rules

### Imported functions (§20.4.1)

```
import_function ::= import [target|solve] [language_id] function type_identifier ;
                  | import [target|solve] [language_id] [static] function function_prototype ;
```

- The first form requires a **separate declaration**. Reserved language identifiers: **`C`,
  `CPP`, `SV`**.
- **Instance functions cannot be imported.** A static function declared in a component may only
  be imported **in that same component type** — not a derived or unrelated one. **Functions
  declared in a template component may not be imported.**
- **Allowed parameter and return types**: `bit`/`int` **≤ 64 bits**, `bool`, `enum`, `string`,
  `chandle`, `struct`, arrays of any of those (including sub-arrays), and lists of those
  **except `string` and `chandle`**. **Template types are not allowed** (§10.5).
- **Directions** (§20.2.2), in the declaration or the import: `input` — values changed by the
  foreign side are **not** reflected back; `output` — unknown on entry, must be set by the
  foreign side; `inout` — passed in and reflected back. **Default is `input`.**
- With the prototype form, the import prototype must match the declaration **exactly**: `static`
  qualifier, parameter count, parameter names, types, directions, and return type.

### Imported classes (§20.4.3)

`import_class` declarations bind a foreign class; instances may be declared in components.

### Exported functions (§20.4.2)

`export [target|solve] function ...` makes a PSS function callable from the foreign language.

### Target-template exec blocks (§20.5)

- `exec <kind> <LANG> = """ … """;` emits text into the generated test.
- `exec file "<name>" = """ … """;` emits into a named file; untagged blocks with the same target
  from different actions/objects are **concatenated in scenario flow order**.
- **Mustache** `{{expression}}` references variables visible in the declaring scope. **Only
  scalars, and not `chandle`.** A reference may appear anywhere — including inside an identifier
  (`func_{{id}}({{a}});`) — and **can never be assigned to**.
- Conversion: `int`→`%d`, `bit`→unsigned decimal, `bool`→`"true"`/`"false"`, `enum`→item name,
  `string`→`%s`, `chandle`→`%p`, floats→`%f`.
- Comments `{# … #}` and `{#} …` never reach the target code.
- **`super;` is illegal in a target-template exec.**
- Expansion happens **after the `pre_body` phase**.
- **Exec block tags** **3.1** control generation-time deduplication — see `01-exec-blocks.md`.

### Target-template functions (§20.6)

```
target_template_function ::= target <language_id> [static] function function_prototype = "string" ;
```

- **Always a target implementation. `void` return only. No parameter directions.**
- Mustache references in **expression positions only**.
- An instance function's template may reference instance attributes, optionally via `this`.
- The prototype must match any separate declaration in parameter count, names, types, and return
  type.

### Exported actions (§20.10)

```
export_action ::= export [target|solve] action_type_identifier function_parameter_list_prototype ;
```

- Exposes an action as a foreign-language function. **Parameters are matched by name** to the
  action's fields; the tool picks values for the rest. Unqualified ⇒ available in all phases.
- **Each call infers an independent tree of actions, components, and resources. Constraints and
  resource allocation are not considered across the boundary.**
- Binding: a `namespace comp { void A1(unsigned char mode); }` in C++, a package in
  SystemVerilog (§20.10.3).

### Comparison of mapping mechanisms (§20.9)

| Need | Use |
|---|---|
| portable computation, reusable across platforms | native PSS function |
| call an existing C/C++/SV API and get a value back | imported function |
| emit code with no callable equivalent (assembly, globals, `#include`s) | target template exec or function |
| let foreign code request PSS-generated stimulus | exported action |

## Gotchas

**Importing an instance function.** Not permitted — imports are static only.
*Tier 2.*

**Importing a static function into a derived component.** Must be the **same** component type
that declared it.
*Tier 2.*

**An import parameter wider than 64 bits, or a `list<string>`.** Outside the allowed type set.
*Tier 2.*

**A template type across the import boundary.** Not permitted (§10.5).
*Tier 2.*

**Expecting an `input` parameter's changes to come back.** They do not — that is what `inout` is
for. Default is `input`.
*Tier 4* — the foreign side "works" and PSS never sees the result.

**Assigning to a mustache reference.**
```pss
exec body C = """ {{x}} = compute(); """;    // WRONG: references are read-only
```
*Tier 2.* Use an imported function to get a value back into PSS.

**A non-scalar or a `chandle` in a mustache expression.** Not permitted.
*Tier 2.*

**A non-`void` target-template function.** `void` only.
*Tier 2.*

**Parameter directions on a target-template function.** Not permitted.
*Tier 2.*

**Expecting constraints to hold across an exported action call.** Each call infers an
**independent** tree — constraints and resource allocation do not cross the boundary. Two calls
that "should" agree will not.
*Tier 4* — a legal model producing an inconsistent test.

**Reading DUT state back and constraining it.** The pattern in the canonical form works — the
value is read in `exec body` and then influences a *later* activity decision. But it cannot feed
a constraint on the *same* action (§13.4.13).
*Tier 3–4.*

**Duplicate `#include`s from an untagged `header` template.** Untagged blocks match nothing and
are emitted per instance. Tag them (**3.1**), or accept the duplication.
*Tier 4.*

**`super;` in a target template.** Illegal.
*Tier 1–2.*

## See also

- `01-exec-blocks.md` — exec kinds, template expansion timing, and exec tags.
- `02-functions.md` — declaration, qualifiers, parameter rules.
- `../data/01-lexical-and-literals.md` — triple-quoted strings, mustache, control-flow
  directives.
- `../platform/01-executors.md` — `get_context()` and target execution units, which decide where
  the emitted code lands.
- `../../playbooks/07-connect-to-c-cpp-sv.md` — task-first.
