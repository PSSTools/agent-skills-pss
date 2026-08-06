# Executors and target execution units

*Domain: platform. LRM §21.7, §21.8. Types from `executor_pkg`.*

An **executor** is the agent that actually runs an action's target code: an embedded core, a
BFM on an interconnect, a testbench transactor. Executors let you say *which* agent runs what,
and let you give different agents different implementations of the same portable operation.

**Representing executors is optional.** With none declared, the tool picks execution contexts by
its own defaults. Reach for them when the answer matters.

## When you are writing this

- The user said "this runs on core 1", "drive this from the SystemVerilog transactor",
  "the DSP does that part".
- The same operation must be implemented differently per agent.
- You need generated code split into per-core files with different compilers.
- Actions must not share an execution agent concurrently.

## Decide

| You need… | Use |
|---|---|
| to represent an execution agent | `executor_c<TRAIT>` instance |
| a set of interchangeable agents | `executor_group_c<TRAIT>` + `add_executor()` |
| an action to run on one of a group | `rand executor_claim_s<TRAIT> claim;` in the action |
| to pick by property (cluster, id, kind) | constrain `claim.trait.*` |
| **exclusive** use of an agent | a `resource` **derived from `executor_claim_s`**, claimed `lock` |
| non-exclusive but agent-correlated use | the same resource, claimed `share` |
| an operation implemented per agent | a function on `executor_base_c`, overridden per subtype, dispatched via `executor()` |
| a component's target execs on a given agent | `set_executor()` in an init exec |
| generated code split per compiler/language | `target_execution_unit_c` + `set_target_execution_unit()` |

**Executor claim vs resource.** A plain `executor_claim_s` assigns the action to an executor
but **does not make that assignment exclusive** and says nothing about scheduling. If
concurrent actions must not share an agent, derive a **resource** from `executor_claim_s` — a
`lock`/`share` reference to it then functions as the action's executor claim *and* carries the
scheduling exclusion.

## Canonical form

```pss
package my_exec_pkg {
    import executor_pkg::*;

    struct core_trait_s : executor_trait_s {
        rand int cluster;
        rand int core_id;
    }
}

component my_soc_c {
    import executor_pkg::*;
    import my_exec_pkg::*;

    executor_c<core_trait_s>       cores[8];
    executor_group_c<core_trait_s> core_grp;

    exec init_up {
        foreach (c : cores [i]) {
            c.trait.cluster = i / 4;
            c.trait.core_id = i;
            core_grp.add_executor(c);
        }
    }

    my_ip_c ip;
}

component my_ip_c {
    action op {
        rand my_exec_pkg::core_trait_s dummy;           // (illustrative)
        rand executor_claim_s<my_exec_pkg::core_trait_s> claim;
        constraint claim.trait.cluster == 0;            // run on cluster 0

        exec body { my_target_op(); }
    }
}

// executor-specific implementation of a portable operation
extend component executor_base_c {
    target function void my_target_op_impl();
}
function void my_target_op() {
    executor().my_target_op_impl();                     // dispatch to the operative executor
}
```

## Rules

### Executor components (§21.7.1)

```pss
package executor_pkg {
    struct executor_trait_s {};
    struct empty_executor_trait_s : executor_trait_s {};

    component executor_base_c { target function chandle get_context(); }

    component executor_c <struct TRAIT : executor_trait_s = empty_executor_trait_s>
        : executor_base_c { TRAIT trait; }

    component executor_group_c <struct TRAIT : executor_trait_s = empty_executor_trait_s> {
        solve function void add_executor(ref executor_c<TRAIT> exe);
    }
}
```

- Executor and executor-group components are **strictly test-realization artifacts**. It is an
  **error to declare action types, pool instances, or pool bind directives** in their scope.
- `get_context()` returns the handle identifying the executor context when calling a PSS
  **export** function. **It is implemented by the tool; you may not override it.**

### Executor assignment (§21.7.2)

- An action or flow/resource object declares an `executor_claim_s<TRAIT>` attribute. The claim
  may be a direct field, a field of a nested struct, or (for flow/resource objects) the
  **supertype** the object derives from — all equivalent.
- **An entity may be assigned to at most one executor, so there may be only one executor claim
  anywhere under a given action or object. More than one is an error.**
- **Assignment is not exclusive** and is generally unrelated to relative scheduling.
- Defaults when nothing is claimed:
  - an **action** uses the executor of its containing component (§21.7.2.6);
  - a **flow/resource object** uses the default executor of the component declaring its pool;
  - a **struct** uses the executor of its containing entity;
  - failing all that, the tool decides.
- **Executors do not limit concurrency.** If concurrently scheduled actions land on the same
  executor, the tool must provide cooperative or preemptive multitasking.

### Matching a claim to a group (§21.7.2.2)

A claim resolves to a group that: (a) is parameterized by **the same trait type**; (b) is
instantiated in a **containing component** of the declaring entity; (c) is the **nearest** such
going up to the root.

- **No matching group is an error. More than one match at that level is an error.**
- Consequently, **nesting a group inside a group is pointless** — no claim could match the inner
  one.

### Claim trait semantics (§21.7.2.3)

The claim's trait type must be the selected executor's trait type, and the claim's trait
attribute **values must equal** the executor's corresponding trait values. So constraining
`claim.trait.cluster == 0` selects among executors whose `trait.cluster` is 0.

### Executor resources (§21.7.2.4)

A **resource object derived from `executor_claim_s`** is a claim not only for its own executor
assignment but **for the actions that `lock` or `share` it**. This is the mechanism for
"exclusive use of a core for the action's duration".

### Executor query (§21.7.2.5)

```pss
function ref executor_base_c executor();
```

- Returns the executor instance assigned to the entity whose exec block (or a function called
  from it) is evaluating.
- **Returns `null` if the entity has no executor.** Because executor assignment is resolved
  during the solve, **calling `executor()` in `pre_solve` always returns `null`.**
- Different concurrently executing actions get different references. This is the standard way to
  delegate a portable operation to an executor-specific implementation.

### Component executors (§21.7.2.6)

```pss
function void set_executor(ref executor_base_c xtr);
```

- Every component instance with target exec blocks (`run_start`, `run_end`, `header`,
  `declaration`) **shall** be associated with an executor.
- `set_executor()` is called in `exec init_up`/`init_down`; **at most one executor per
  instance**; consecutive calls override.
- Without an explicit assignment a component inherits its **parent's** executor. **If none can
  be determined and the component has component-level target execs, it is an error.**
- The component's executor is the default for actions on it that make no claim; an action's own
  claim does **not** change the component's executor.
- **An executor is its own executor.** Assigning any other executor to an executor instance is
  an error, as is an execution unit assigning an executor referencing a different execution
  unit.

### Target execution units (§21.8)

```pss
package executor_pkg {
    enum target_language_e { C, CPP, SV };
    component target_execution_unit_c {
        solve function void   set_filename(string filename);
        solve function string get_filename();
        solve function void   set_target_language(target_language_e lang);
        // ... get_target_language()
    }
}
```

- Group executor realizations into files sharing a target language, so they can be compiled
  together. **Also strictly a test-realization artifact** — no action types, pools, or binds in
  scope.
- `filename` is the root of the generated file name (a tool may emit `<filename>.c` and
  `<filename>.h`). Unspecified, the tool derives one from the instance name.
- **Default target language is `C`.** The language enum is extensible by the tool.
- An executor references a unit via `set_target_execution_unit()`. **If target execution units
  are declared in the system, failing to give an executor one is an error.**

## Gotchas

**Two executor claims under one action.**
```pss
action a {
    rand executor_claim_s<t_s> c1;
    rand nested_s n;             // ...whose struct also contains a claim
}
```
*Tier 2.* At most one claim anywhere under the entity — including inside nested structs and
inherited supertypes, which is how this usually happens by accident.

**Expecting an executor claim to prevent sharing.** It does not. Use a resource derived from
`executor_claim_s`.
*Tier 4* — this is the most consequential misunderstanding on this page.

**No matching executor group.** An error, and the message points at the claim, not at where the
group should have been. Check trait type and component placement.
*Tier 2–3.*

**A group nested inside another group.** Unreachable by any claim.
*Tier 4* — silently does nothing.

**Declaring an action or pool inside an executor / group / execution-unit component.** An
error; these are realization-only components.
*Tier 2.*

**Calling `executor()` in `pre_solve`.** Always `null` — assignment has not happened.
*Tier 4* — a null dereference at generation time, or worse, silently taking a default path.

**Component target execs with no determinable executor.** An error when the component type
defines `run_start`/`run_end`/`header`/`declaration` and neither it nor any ancestor set one.
*Tier 2–3.*

**Overriding `get_context()`.** Not permitted; the tool implements it.
*Tier 2.*

**Assuming the default target language.** It is `C`. If the environment is SystemVerilog and no
unit says so, you get C.
*Tier 4.*

**Assuming actions on the same executor serialize.** The tool is required to make concurrent
execution work via multitasking. If you need serialization, that is a resource or a scheduling
dependency.
*Tier 4.*

## See also

- `02-sync-and-communication.md` — what happens when several actions share one executor.
- `03-address-spaces.md` §executor-based customization — overriding read/write and
  `addr_value()` per executor.
- `../structural/05-resource-objects.md` — the `lock`/`share` half of executor resources.
- `../activity/03-scheduling-semantics.md` — executors are non-preemptible cooperative threads.
- `../procedural/04-foreign-interface.md` — exported functions and `get_context()`.
