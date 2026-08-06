# Playbook: connect to C / C++ / SystemVerilog

*"Call my C driver function." "Emit this SystemVerilog task call." "The testbench needs to kick
off a transfer."*

## Choose the mechanism

Work down; use the first that fits.

| The need | Mechanism |
|---|---|
| pure computation | **native PSS function** — portable, checkable, no binding |
| call an existing function and get a value back | **imported function** |
| emit text with no callable equivalent — assembly, `#include`s, globals | **target template** |
| foreign code needs to request PSS stimulus | **exported action** |
| foreign code needs to call one PSS function | **exported function** |

The ordering is deliberate: a native function is type-checked, an import has typed parameters, a
template is untyped text. Drop a level only when the one above cannot express it.

## Steps — imported function

**1. Declare the PSS-side signature, in a package.**

```pss
package external_functions_pkg {
    function bit[31:0] alloc_addr(bit[31:0] size);
    function void      transfer_mem(bit[31:0] src, bit[31:0] dst, bit[31:0] size);
}
```

**2. Import with the platform and the language.**

```pss
package pregen_tests_pkg {
    import solve  function external_functions_pkg::alloc_addr;
    import target function external_functions_pkg::transfer_mem;
}
package known_c_functions {
    import C function generic_functions::compute_expected_value;
}
```

**3. Check the types.** Allowed: `bit`/`int` ≤ 64 bits, `bool`, `enum`, `string`, `chandle`,
`struct`, arrays of those; lists of those **except** `string` and `chandle`. **No template
types.**

**4. Get values back with directions.** `input` (default) changes are **not** reflected back —
use `output` or `inout`, which only imported functions may declare.

## Steps — target template

```pss
component top {
    action A {
        rand bit[1:0] func_id;
        rand bit[3:0] a;

        exec header C = """ #include "dut.h" """;
        exec body   C = """
            func_{{func_id}}({{a}});   {#} a mustache may appear inside an identifier
        """;
    }
}
```

- Only **scalars** (not `chandle`) may be referenced, and references are **read-only**.
- Expansion happens **after `pre_body`**.
- `{# … #}` and `{#} …` comments never reach the target.
- **3.1:** tag `header` / `declaration` / `run_start` / `run_end` / `exec file` blocks to have
  the tool deduplicate identical generated text; untagged blocks match nothing and are emitted
  per instance.

## Steps — exported action

```pss
component comp_c {
    action A1 { rand bit mode; rand bit[31:0] val; }
}
package pkg { export target comp_c::A1(bit mode); }
```

- Parameters are matched **by name** to the action's fields; the tool picks the rest.
- **Each call infers an independent action tree.** Constraints and resource allocation are **not
  considered across the boundary** — two calls will not agree about anything.

## Reading DUT state back into the scenario

Legal, and useful:

```pss
component my_ip_c {
    import target C function int sample_DUT_state();
    action check_state {
        int curr_val;
        exec body { curr_val = comp.sample_DUT_state(); }
    }
    action my_test {
        check_state cs;
        activity {
            repeat { cs; if (cs.curr_val % 2 == 0) { do A; } else { do B; } }
            while (cs.curr_val < 10);
        }
    }
}
```

The value steers a **later** activity decision. It cannot feed a constraint on the same action
(§13.4.13), and there is no backtracking.

## Checks before you call it done

- [ ] Platform qualifier correct on every import.
- [ ] No instance function imported; a component's static function imported only in **that same**
      component type.
- [ ] All parameter and return types within the imported-function type set.
- [ ] Direction modifiers only on imports — never on native or target-template functions.
- [ ] Target-template function returns `void`.
- [ ] No assignment to a mustache reference.
- [ ] `super;` not used in a target template.
- [ ] `header`/`declaration` blocks tagged if duplication matters.
- [ ] Exported actions: no assumption that constraints hold across calls.

## See also

- `../lang/procedural/04-foreign-interface.md` — the rules.
- `../lang/procedural/02-functions.md` — declaration, qualifiers, parameters.
- `../lang/procedural/01-exec-blocks.md` — exec kinds and exec tags.
- `../lang/platform/01-executors.md` — target execution units decide which file the emitted code
  lands in.
