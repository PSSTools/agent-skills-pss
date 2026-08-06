# Checker rules: structural

Proposed checker `name = "structural"`. Tier 2, except PSL034 which is tier 3-adjacent but
decidable statically.

Reference pages: `../reference/lang/structural/03-actions.md`,
`../reference/lang/structural/06-pools-and-binding.md`,
`../reference/lang/structural/02-components.md`.

---

## PSL031 — action has both an activity and an exec body

| | |
|---|---|
| **Rule** | The `activity_declaration` and `body` exec block action body items are mutually exclusive. An atomic action may specify `body` execs; a compound action shall not. |
| **LRM clause** | §9.2.1 a |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL031",
    severity="error",
    summary="Action declares both an activity and an exec body",
    detail=(
        "An action is either atomic -- it has an implementation, given by one or "
        "more `exec body` blocks -- or compound: it composes other actions in an "
        "activity. It cannot be both.\n\n"
        "Move the body into a new atomic action and traverse it from the activity."
    ),
)
```

**Detection**

For each action type, collect its body items across the initial definition, all extensions, and
all inherited definitions. Report when at least one `activity` and at least one `exec body`
(procedural or target-template) are present.

**False-positive risk**

- **Inheritance.** A derived action's activity *shadows* the base's, and a derived `exec body`
  *replaces* the base's — but a derived action that adds an activity to a base that has an
  `exec body` still ends up with both, and is a violation. Consider the merged view.
- **`compile if`.** Only elaborated branches count.

**Triggering example**

```pss
component c {
    action sub { }
    action bad {
        activity { do sub; }
        exec body { }                    // PSL031 here
    }
}
component pss_top { c c0; }
```

---

## PSL032 — object reference field with no bound pool

| | |
|---|---|
| **Rule** | Flow object exchange is always mediated by a pool, and resource claims come from a pool. Static `bind` directives determine which pools are accessible to an action's object references. |
| **LRM clause** | Clause 12, §12.3 |
| **Tier** | 2 (structural), catches a tier-3 failure |

**Marker**

```python
MarkerDef(
    id="PSL032",
    severity="error",
    summary="Object reference field has no pool bound to it",
    detail=(
        "Every input/output/lock/share field must resolve to a pool of the same "
        "type, bound to the action's context component. Declaring a pool is NOT "
        "enough -- it must also be bound, with an explicit bind or a wildcard "
        "default bind.\n\n"
        "Without a binding the action can never be scheduled, which surfaces much "
        "later as 'no legal scenario' with nothing pointing back here."
    ),
)
```

**Detection**

For each action type, for each `input`/`output`/`lock`/`share` field (and each element of an
object-reference array), resolve the binding by the §12.3 rules:

1. an explicit bind naming this component path, action type and field wins;
2. otherwise the default (`*`) bind of the matching type visible from the context component,
   resolved **top-down** — the top-most component instance's directive wins.

Report when no binding is found for **any** context component the action could be associated
with.

**False-positive risk**

- **Actions in a component type that is never instantiated.** They cannot participate in a
  scenario at all; report at `warning` or skip.
- **Abstract actions.** Not traversable; their fields need no binding until a concrete subtype
  exists. Check the concrete subtypes instead.
- **Array elements bound individually.** Explicit binds may cover elements one at a time; check
  per element, not per field.
- **Multiple candidate context components.** An action may be associated with several component
  instances. Report only when *no* instance yields a binding — a partial binding is a tier-3
  concern, not this rule.

**Triggering example**

```pss
package p { buffer b_s { rand bit[8] v; } }
component c {
    import p::*;
    pool b_s bp;                     // declared but NOT bound
    action a { input b_s i; }        // PSL032 here
}
component pss_top { c c0; }
```

**Near-miss example** — as above, with `bind bp *;` added.

---

## PSL033 — pool bound to a related but non-identical type

| | |
|---|---|
| **Rule** | When binding object reference fields to a pool, the object and the pool must be of the exact same type. It shall be illegal to bind an object of a derived type to a pool of its base type, or vice versa. |
| **LRM clause** | §12.3 g |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL033",
    severity="error",
    summary="Pool type does not exactly match the object reference type",
    detail=(
        "Pool binding requires an exact type match. A derived-type object may not "
        "be bound to a base-type pool, nor the reverse -- the usual "
        "substitutability of inheritance does not apply here.\n\n"
        "Declare a pool of the exact object type."
    ),
)
```

**Detection**

For every binding resolved by PSL032's algorithm, compare the pool's declared type with the
object reference field's declared type. Report when they are not identical, but *are* related
by inheritance — an unrelated type is a plain type error the front end already reports, and
reporting it twice is noise.

For template types, compare the **instantiated** types: `pool_t<A>` and `pool_t<B>` are
different types.

---

## PSL034 — resource pool smaller than an array claim

| | |
|---|---|
| **Rule** | When claiming an array of resource objects, the pool size must be at least as large as the array, with all dimensions, to accommodate all distinct resource claims. |
| **LRM clause** | §9.4.2 d |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL034",
    severity="error",
    summary="Resource pool is smaller than an array claim on it",
    detail=(
        "Every element of a resource-object array is a distinct claim, and all "
        "elements bind to the same pool, so the pool must hold at least as many "
        "objects as the array has elements across all dimensions.\n\n"
        "This is otherwise reported as an unsatisfiable scenario, with no "
        "indication that the pool size is the cause."
    ),
)
```

**Detection**

For each `lock`/`share` field that is an array, compute the total element count (the product of
all dimensions — all constant expressions). Resolve the bound pool and read its size expression.
Report when the pool size is a constant strictly less than the element count.

**False-positive risk**

- A **non-constant** pool size or array dimension — skip rather than guess.
- A pool size omitted defaults to **1** (§12.1); that is a real size, not "unknown".
- **All elements of a resource array must bind to the same pool** (§9.4.2 c), so there is one
  pool to check — but verify that rule holds before relying on it, and report §9.4.2 c
  separately if it does not.

**Triggering example**

```pss
package p { resource r_s { } }
component c {
    import p::*;
    pool [2] r_s rp; bind rp *;
    action a { lock r_s chans[4]; }        // PSL034 here
}
component pss_top { c c0; }
```

---

## PSL035 — illegal declaration in a `pure component`

| | |
|---|---|
| **Rule** | In the scope of a pure component, it shall be an error to declare action and monitor types, pool instances, pool binding directives, non-static data attributes, instances of non-pure component types, exec blocks, or cover statements. A non-pure component may not be instantiated under a pure one, and a pure component may not derive from a non-pure one. |
| **LRM clause** | §9.1.7 |
| **Tier** | 2 |

**Marker**

```python
MarkerDef(
    id="PSL035",
    severity="error",
    summary="Illegal declaration in a pure component",
    detail=(
        "A `pure component` exists so a tool can represent large realization-only "
        "structures cheaply -- the register model is the canonical case. It may "
        "therefore contain no scenario-model features.\n\n"
        "Forbidden in its scope: action and monitor types, pool instances, pool "
        "bind directives, non-static data attributes, instances of non-pure "
        "components, exec blocks, and cover statements. A pure component may be "
        "instantiated under a non-pure one, never the reverse."
    ),
)
```

**Detection**

For each component type declared `pure` (including via inheritance from a pure component),
report each of:

- an `action_declaration`, `abstract_action_declaration`, or `monitor_declaration`;
- a `component_pool_declaration` or `object_bind_stmt`;
- a data field that is not `static const`;
- an instance of a component type that is not pure;
- any `exec_block`;
- any `cover_stmt`.

Separately report a pure component deriving from a non-pure component, and a non-pure component
instantiated under a pure one.

**False-positive risk**

- **Function declarations and definitions are legal** in a pure component — that is what
  register types are made of.
- **Nested type declarations** (structs, enums, typedefs) are legal.
- `static const` data is legal; only *non-static* data attributes are forbidden.
- Purity is inherited: a component deriving from `reg_c` or `reg_group_c` is pure even without
  the keyword. Resolve the base chain.

**Triggering example**

```pss
package p {
    import addr_reg_pkg::*;
    pure component g_c : reg_group_c {
        int counter;                       // PSL035: non-static data
        action a { }                       // PSL035: action in a pure component
        exec init_up { }                   // PSL035: exec block
    }
}
component pss_top { }
```

**Near-miss example**

```pss
package p {
    import addr_reg_pkg::*;
    pure component g_c : reg_group_c {
        static const int N = 4;            // legal
        function bit[64] get_offset_of_instance(string n) { return 0; }
        function bit[64] get_offset_of_instance_array(string n, int i) { return 0; }
    }
}
component pss_top { }
```
