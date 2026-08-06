# Components

*Domain: structural. LRM §9.1.*

## When you are writing this

- The user described a piece of the system: "the DMA engine", "the UART", "the CPU", "our
  testbench agent".
- You need somewhere to put configuration data (base addresses, channel counts, feature flags).
- You need somewhere to put actions — every action lives in a component.
- You need somewhere to put a pool so actions can exchange objects.
- The user asked for two of something ("four DMA channels", "two UARTs").

## Decide

| The thing you are modeling… | Use |
|---|---|
| is an actor that performs behavior, or owns config | `component` |
| is data passed between actors | `struct` / flow object, not a component |
| is a register map or other realization-only structure | `pure component` |
| exists once per system | instantiate in `pss_top` |
| exists N times | `component_t insts[N];` — component arrays are legal and multidimensional |
| is config known before the test runs | plain component attribute |
| is state accumulated *during solving* | `mutable` attribute **3.1** |
| is a pointer to a component elsewhere in the tree | `ref component_t` field, or `instance ref` for full capability |

Component vs struct, when it isn't obvious: **can it own an action?** If yes, component. A
component is a position in the system, not a value; you never randomize one and never copy one.

## Canonical form

```pss
component dma_c {
    // configuration: set during elaboration, read-only afterwards
    bit[32]          base_addr;
    static const int NUM_CH = 4;          // reachable without `comp`, as dma_c::NUM_CH

    // instance function: dispatches on the context component
    function bit[32] ch_addr(int ch) { return base_addr + ch * 0x20; }

    // pool: makes objects available to this component's actions
    pool mem_seg_s seg_p;
    bind seg_p *;

    action xfer {
        rand int ch;
        constraint ch in [0..NUM_CH-1];
        exec body {
            poke(comp.ch_addr(ch), 1);    // component data reached through `comp`
        }
    }
}

component pss_top {
    dma_c dma0, dma1;
    dma_c dmas[2];                        // arrays, possibly multidimensional

    exec init_down {                      // parent before child
        dma0.base_addr = 0x1000;
        dma1.base_addr = 0x2000;
        foreach (d : dmas [i]) { d.base_addr = 0x3000 + i * 0x1000; }
    }
}
```

`pss_top` is the root, implicitly instantiated. There is exactly one root per scenario. (The
name is the default; a tool may allow another root to be selected.)

## Rules

- Component fields are **never `rand`** (§9.1.4.1a). Configuration is chosen by elaboration,
  not by the solver.
- **Component data is immutable once the tree is built** (§9.1.4.1e). Actions read it; they do
  not write it. The only writes happen in `exec init_down` / `exec init_up`.
  - Exception: fields declared **`mutable`** **3.1** may be modified during solve-time
    execution, including from solve execs and during activity solving (§9.1.6).
- A component type shall not be instantiated under its own sub-tree — no instantiation
  recursion (§9.1.4.1a).
- Plain-data fields may take a constant-expression initializer; an `init_down`/`init_up`
  assignment **overrides** it (§9.1.4.1d).
- `init_down` runs parent-before-child; `init_up` runs child-before-parent. **Sibling order is
  undefined** — never rely on it (§20.1.5).
- Actions reach their context component only through **`comp`**, which is assigned by the
  solver and may not be assigned by you (§9.1.5). Its static type is `ref <context component>`.
- **`comp` cannot access `static` members** (§9.1.4.1f) — use `Type::member`.
- A struct declared inside a component **may not reference non-static members** of that
  component (§9.1.4.1g).
- A compound action may only instantiate actions defined in its own component or in that
  component's instance sub-tree (§9.1.5.1). Same rule for monitors and cover statements.
- Component types are namespaces: `pkg::comp_type::nested_type` (§9.1.3).
- Components may contain data, functions, actions, monitors, pools, binds, execs, nested types
  and covergroups — but **not constraints** on their own data.

### `mutable` **3.1**

- Applies to solve-time-modifiable component data. Such fields shall **not** be modified,
  directly or indirectly, from target exec blocks (§9.1.6).
- The qualifier **propagates into aggregates**: a `mutable` struct field makes all its fields
  mutable.
- It shall not be applied to component *instance* fields or instance reference fields. On a
  non-instance reference field it applies to the reference itself (you may re-point it), not to
  the referenced component's fields.
- Solve-time exec execution is guaranteed atomic, so accumulating into a `mutable` field across
  repeated action executions is race-free.

### `pure component` (§9.1.7)

A storage/elaboration optimization for realization-only structure. The register model is the
canonical use.

Inside a `pure component` it is an **error** to declare action or monitor types, pool
instances, pool bind directives, non-static data attributes, instances of non-pure components,
exec blocks, or cover statements. A pure component may be instantiated under a non-pure one,
never the reverse. A pure component may not derive from a non-pure component.

## Gotchas

**Writing a component attribute from an action** — the single most common component error.

```pss
// WRONG
action cfg { exec post_solve { comp.base_addr = 0x2000; } }
// RIGHT — set it during elaboration
component pss_top { dma_c dma; exec init_up { dma.base_addr = 0x2000; } }
// or, if it genuinely must change during solving: declare it `mutable` (3.1)
```
*Tier 2* — a type-checking compiler rejects it; a parser accepts it silently.

**Reaching a `static const` through `comp`.**

```pss
constraint ch < comp.NUM_CH;   // WRONG: static member via comp
constraint ch < dma_c::NUM_CH; // RIGHT
```
*Tier 1–2* — usually a resolution error, but message quality varies.

**Relying on sibling init order.**

```pss
// WRONG: dma1.base_addr may not be set yet
exec init_up { dma0.base_addr = dma1.base_addr + 0x1000; }
```
*Tier 4* — nothing catches this; it works until the tool changes its traversal order. Compute
both from the same source instead.

**Traversing an action from a component that isn't in your sub-tree.**

```pss
component bus_c   { action write {} }
component graphics_c {
    action gr_a { activity { do bus_c::write; } }   // WRONG: bus_c not instantiated here
}
```
*Tier 3* — no legal component assignment exists. The diagnostic usually talks about the
component binding, not about this line.

**Expecting a component array to be randomizable.** It isn't — component fields are never
`rand`, and `comp` is assigned by the solver's component-assignment step (§13.4.5), which you
influence with constraints on `comp`, not by declaring anything `rand`.
*Tier 1.*

**Declaring an action inside a `pure component`.** Silently tempting when building a register
model that "should also do something".
*Tier 2.*

## See also

- `03-actions.md` — what lives inside a component.
- `06-pools-and-binding.md` — why a pool's position in the component tree decides which actions
  can use it.
- `../procedural/01-exec-blocks.md` — `init_down`/`init_up` in full.
- `../platform/04-registers.md` — `pure component` in its main application.
- `07-inheritance-extension-overrides.md` — deriving and extending components.
