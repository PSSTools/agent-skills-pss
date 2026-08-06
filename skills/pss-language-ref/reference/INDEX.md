# Index

Keyword → page, and LRM clause → page. Grep this file when you have a *token* and need a rule.

Paths are relative to this file. `lang/` pages are grouped by domain; see each domain's
`README.md` for orientation.

---

## PSS keywords

Every keyword reserved by PSS 3.1 §4.4.

| Keyword | Means | Page |
|---|---|---|
| `abstract` | action that cannot be traversed directly; must be inherited from | `lang/structural/03-actions.md` |
| `action` | declares a unit of schedulable behavior | `lang/structural/03-actions.md` |
| `activity` | declares the composition body of a compound action | `lang/activity/01-activities.md` |
| `array` | fixed-size collection type `array<T,N>` | `lang/data/03-collections.md` |
| `as` | package alias (`import p as q;`) | `lang/structural/01-packages-and-name-resolution.md` |
| `assert` | compile-time assertion in `compile` processing | `lang/structural/09-conditional-code.md` |
| `atomic` | activity block specifier: no other action may interleave | `lang/activity/01-activities.md` |
| `bind` | associates a pool with action object-reference fields | `lang/structural/06-pools-and-binding.md` |
| `bins` | named value groups of a coverpoint | `lang/coverage/01-data-coverage.md` |
| `bit` | unsigned integer type, 1 bit by default | `lang/data/02-data-types.md` |
| `body` | exec kind: the target-platform implementation of an atomic action | `lang/procedural/01-exec-blocks.md` |
| `bool` | boolean type | `lang/data/02-data-types.md` |
| `break` | exits the innermost procedural loop | `lang/procedural/03-procedural-statements.md` |
| `buffer` | flow object: persistent, consumer runs after producer completes | `lang/structural/04-flow-objects.md` |
| `chandle` | opaque foreign handle | `lang/data/02-data-types.md` |
| `class` | imported foreign class | `lang/procedural/04-foreign-interface.md` |
| `compile` | `compile if` / `compile has` / `compile assert` — elaboration-time | `lang/structural/09-conditional-code.md` |
| `component` | structural container: instances, attributes, actions, pools | `lang/structural/02-components.md` |
| `concat` | behavioral coverage concatenation scenario | `lang/coverage/02-behavioral-coverage.md` |
| `const` | immutable declaration; non-mutating parameter | `lang/data/02-data-types.md`, `lang/procedural/02-functions.md` |
| `constraint` | declares a constraint block or named constraint | `lang/constraints/01-algebraic-constraints.md` |
| `continue` | next iteration of the innermost procedural loop | `lang/procedural/03-procedural-statements.md` |
| `cover` | behavioral coverage statement | `lang/coverage/02-behavioral-coverage.md` |
| `covergroup` | data coverage model declaration | `lang/coverage/01-data-coverage.md` |
| `coverpoint` | a sampled expression within a covergroup | `lang/coverage/01-data-coverage.md` |
| `cross` | cross coverage of two or more coverpoints | `lang/coverage/01-data-coverage.md` |
| `declaration` | exec kind: target-template global declarations | `lang/procedural/01-exec-blocks.md` |
| `default` | `match` fallback arm; default value constraint; `default disable` | `lang/procedural/03-procedural-statements.md`, `lang/constraints/01-algebraic-constraints.md` |
| `disable` | disables a constraint or coverage element | `lang/constraints/01-algebraic-constraints.md` |
| `dist` | weighted value distribution directive | `lang/constraints/01-algebraic-constraints.md` |
| `do` | traverses an action in an activity | `lang/activity/01-activities.md` |
| `dynamic` | dynamic constraint declaration/reference | `lang/constraints/01-algebraic-constraints.md` |
| `else` | alternative branch of `if` (activity, constraint, procedural) | `lang/activity/01-activities.md` |
| `enum` | enumeration type | `lang/data/02-data-types.md` |
| `eventually` | behavioral coverage eventuality scenario | `lang/coverage/02-behavioral-coverage.md` |
| `exec` | declares a block of realization code | `lang/procedural/01-exec-blocks.md` |
| `export` | exposes a PSS function or action to foreign code | `lang/procedural/04-foreign-interface.md` |
| `extend` | adds members to an existing type everywhere it is used | `lang/structural/07-inheritance-extension-overrides.md` |
| `false` | boolean literal | `lang/data/01-lexical-and-literals.md` |
| `file` | exec file tag: directs template output to a named file | `lang/procedural/01-exec-blocks.md` |
| `float32` | 32-bit floating point | `lang/data/02-data-types.md` |
| `float64` | 64-bit floating point | `lang/data/02-data-types.md` |
| `forall` | constraint quantified over all instances of a type | `lang/constraints/01-algebraic-constraints.md` |
| `foreach` | iterates a collection (activity, constraint, or procedural) | `lang/procedural/03-procedural-statements.md` |
| `function` | declares or defines a function | `lang/procedural/02-functions.md` |
| `has` | `compile has (x)` — is this declaration visible? | `lang/structural/09-conditional-code.md` |
| `header` | exec kind: target-template file header text | `lang/procedural/01-exec-blocks.md` |
| `if` | conditional (activity, constraint, procedural, `compile if`) | `lang/activity/01-activities.md` |
| `iff` | guard on a coverage bin or cover statement | `lang/coverage/01-data-coverage.md` |
| `ignore_bins` | coverpoint values excluded from coverage | `lang/coverage/01-data-coverage.md` |
| `illegal_bins` | coverpoint values that are an error if hit | `lang/coverage/01-data-coverage.md` |
| `import` | imports a package, or declares a foreign function | `lang/structural/01-packages-and-name-resolution.md`, `lang/procedural/04-foreign-interface.md` |
| `in` | set membership in an expression or constraint | `lang/data/04-expressions-operators.md` |
| `init_down` | exec kind: component init, parent before child | `lang/procedural/01-exec-blocks.md` |
| `init_up` | exec kind: component init, child before parent | `lang/procedural/01-exec-blocks.md` |
| `inout` | imported-function parameter direction | `lang/procedural/02-functions.md` |
| `input` | action's consumed flow object; imported-function parameter direction | `lang/structural/04-flow-objects.md` |
| `instance` | instance-qualified component reference | `lang/structural/02-components.md` |
| `int` | signed integer type, 32 bits by default | `lang/data/02-data-types.md` |
| `join_branch` | fine-grained join on named branches | `lang/activity/01-activities.md` |
| `join_first` | fine-grained join on the first N to complete | `lang/activity/01-activities.md` |
| `join_none` | fine-grained join: no dependency on the block | `lang/activity/01-activities.md` |
| `join_select` | fine-grained join on N randomly selected branches | `lang/activity/01-activities.md` |
| `list` | growable collection type `list<T>` | `lang/data/03-collections.md` |
| `lock` | exclusive claim on a resource object | `lang/structural/05-resource-objects.md` |
| `map` | keyed collection type `map<K,V>` | `lang/data/03-collections.md` |
| `match` | multi-way branch (activity or procedural) | `lang/procedural/03-procedural-statements.md`, `lang/activity/01-activities.md` |
| `monitor` | behavioral coverage observation type | `lang/coverage/02-behavioral-coverage.md` |
| `null` | null reference literal | `lang/data/02-data-types.md` |
| `numeric` | numeric template parameter category | `lang/structural/08-templates.md` |
| `output` | action's produced flow object; imported-function parameter direction | `lang/structural/04-flow-objects.md` |
| `overlap` | behavioral coverage overlapping scenario | `lang/coverage/02-behavioral-coverage.md` |
| `override` | replaces a type globally or within a scope | `lang/structural/07-inheritance-extension-overrides.md` |
| `package` | namespace and home for extensions | `lang/structural/01-packages-and-name-resolution.md` |
| `parallel` | activity block: branches begin at the same time | `lang/activity/01-activities.md` |
| `pool` | container of objects available to bound actions | `lang/structural/06-pools-and-binding.md` |
| `post_solve` | exec kind: solve-platform, after randomization | `lang/procedural/01-exec-blocks.md` |
| `pre_body` | exec kind: solve-platform, after executor/address assignment | `lang/procedural/01-exec-blocks.md` |
| `pre_solve` | exec kind: solve-platform, before randomization | `lang/procedural/01-exec-blocks.md` |
| `private` | access protection: this type only | `lang/structural/07-inheritance-extension-overrides.md` |
| `protected` | access protection: this type and derived types | `lang/structural/07-inheritance-extension-overrides.md` |
| `public` | access protection: unrestricted (default) | `lang/structural/07-inheritance-extension-overrides.md` |
| `pure` | function with no side effects; `pure component` | `lang/procedural/02-functions.md`, `lang/structural/02-components.md` |
| `rand` | field the solver may choose a value for | `lang/constraints/03-randomization.md` |
| `randomize` | procedural randomization statement | `lang/procedural/03-procedural-statements.md` |
| `ref` | reference type | `lang/data/02-data-types.md` |
| `repeat` | loop (activity or procedural), count or while form | `lang/activity/01-activities.md`, `lang/procedural/03-procedural-statements.md` |
| `replicate` | generative in-place expansion in an activity | `lang/activity/01-activities.md` |
| `resource` | object claimed exclusively or shared by actions | `lang/structural/05-resource-objects.md` |
| `return` | returns from a function or exec | `lang/procedural/03-procedural-statements.md` |
| `run_end` | exec kind: target-platform, once at test teardown | `lang/procedural/01-exec-blocks.md` |
| `run_start` | exec kind: target-platform, once at test bring-up | `lang/procedural/01-exec-blocks.md` |
| `schedule` | activity block: any legal order | `lang/activity/01-activities.md` |
| `select` | activity branch point: one of these | `lang/activity/01-activities.md` |
| `sequence` | explicit sequential activity or procedural block | `lang/activity/01-activities.md` |
| `set` | set collection type `set<T>` | `lang/data/03-collections.md` |
| `share` | non-exclusive claim on a resource object | `lang/structural/05-resource-objects.md` |
| `solve` | platform qualifier: generation time only | `lang/procedural/01-exec-blocks.md` |
| `state` | flow object representing environment state, with `prev`/`initial` | `lang/structural/04-flow-objects.md` |
| `static` | class-level (not instance) member; `static const` | `lang/structural/02-components.md` |
| `stream` | flow object: producer and consumer start together | `lang/structural/04-flow-objects.md` |
| `string` | string type | `lang/data/02-data-types.md` |
| `struct` | plain-data aggregate | `lang/data/02-data-types.md` |
| `super` | base-type member access; splices base exec/constraint | `lang/structural/07-inheritance-extension-overrides.md` |
| `symbol` | named reusable activity fragment | `lang/activity/01-activities.md` |
| `target` | platform qualifier: test runtime only; target language | `lang/procedural/01-exec-blocks.md` |
| `this` | the enclosing instance | `lang/structural/02-components.md` |
| `true` | boolean literal | `lang/data/01-lexical-and-literals.md` |
| `type` | template type parameter; generic parameter category | `lang/structural/08-templates.md` |
| `typedef` | type alias | `lang/data/02-data-types.md` |
| `unique` | constraint: all listed values differ | `lang/constraints/01-algebraic-constraints.md` |
| `void` | no return value | `lang/procedural/02-functions.md` |
| `while` | loop (procedural, or `repeat…while` in an activity) | `lang/procedural/03-procedural-statements.md` |
| `with` | inline constraint on a traversal or `randomize` | `lang/constraints/01-algebraic-constraints.md` |
| `yield` | cooperatively suspend a target exec | `lang/procedural/03-procedural-statements.md` |

## Built-in and core-library names

Not keywords, but reserved in practice — declaring your own is a mistake.

| Name | From | Page |
|---|---|---|
| `pss_top` | built-in | `lang/structural/02-components.md` |
| `comp` | built-in action field | `lang/structural/02-components.md` |
| `instance_id` | built-in resource field | `lang/structural/05-resource-objects.md` |
| `initial`, `prev` | built-in state-object fields | `lang/structural/04-flow-objects.md` |
| `format`, `print` | `std_pkg` (solve) | `lang/platform/05-core-library-api.md` |
| `message`, `message_verbosity_e` | `std_pkg` (target) | `lang/platform/05-core-library-api.md` |
| `error`, `fatal` | `std_pkg` | `lang/platform/05-core-library-api.md` |
| `urandom`, `urandom_range` | `std_pkg` | `lang/platform/05-core-library-api.md` |
| `file_open`, `file_write`, `file_close`, … | `std_pkg` | `lang/platform/05-core-library-api.md` |
| `float32_s`, `float64_s`, computation functions | `std_pkg` | `lang/platform/05-core-library-api.md` |
| `executor_c`, `executor_group_c`, `executor_claim_s` | `executor_pkg` | `lang/platform/01-executors.md` |
| `channel_c` and sync types | `sync_pkg` | `lang/platform/02-sync-and-communication.md` |
| `addr_space_base_c`, `contiguous_addr_space_c`, `transparent_addr_space_c` | `addr_reg_pkg` | `lang/platform/03-address-spaces.md` |
| `addr_region_s`, `contiguous_addr_region_s`, `transparent_addr_region_s` | `addr_reg_pkg` | `lang/platform/03-address-spaces.md` |
| `addr_claim_s`, `contiguous_addr_claim_s`, `transparent_addr_claim_s` | `addr_reg_pkg` | `lang/platform/03-address-spaces.md` |
| `addr_handle_t`, `make_handle_from_claim`, `make_handle_from_handle` | `addr_reg_pkg` | `lang/platform/03-address-spaces.md` |
| `read8/16/32/64`, `write8/16/32/64`, `read_bytes`, `write_bytes`, `read_struct`, `write_struct` | `addr_reg_pkg` | `lang/platform/03-address-spaces.md` |
| `mem_access_desc_s` | `addr_reg_pkg` | `lang/platform/03-address-spaces.md` |
| `packed_s`, `sizeof_s`, `endianness_e` | `addr_reg_pkg` | `lang/platform/04-registers.md` |
| `reg_c`, `reg_group_c`, `reg_access_e` (`READWRITE`/`READONLY`/`WRITEONLY`) | `addr_reg_pkg` | `lang/platform/04-registers.md` |

---

## LRM clause → page

For traceability, and for re-deriving these pages against a future draft.

| Clause | Page(s) |
|---|---|
| 1–3 Overview, references, definitions | not carried — no actionable content |
| 4 Lexical conventions | `lang/data/01-lexical-and-literals.md` |
| 5 Modeling concepts | `playbooks/00-choosing-constructs.md` |
| 6 Execution semantic concepts | `lang/activity/03-scheduling-semantics.md` |
| 7 Data types | `lang/data/02-data-types.md`, `lang/data/03-collections.md`, `lang/data/05-annotations.md` (§7.13) |
| 8 Operators and expressions | `lang/data/04-expressions-operators.md` |
| 9.1 Components | `lang/structural/02-components.md` |
| 9.2 Actions | `lang/structural/03-actions.md` |
| 9.3 Flow objects | `lang/structural/04-flow-objects.md` |
| 9.4 Resource objects | `lang/structural/05-resource-objects.md` |
| 10 Template types | `lang/structural/08-templates.md` |
| 11.1–11.5, 11.7, 11.8 Activities | `lang/activity/01-activities.md` |
| 11.6 Activity evaluation with extension/inheritance | `lang/structural/07-inheritance-extension-overrides.md` |
| 11.9–11.11 Explicit and hierarchical binding | `lang/structural/06-pools-and-binding.md` |
| 12 Pools | `lang/structural/06-pools-and-binding.md` |
| 13.1 Algebraic constraints | `lang/constraints/01-algebraic-constraints.md` |
| 13.2, 13.3 Scheduling and sequencing constraints | `lang/constraints/02-scheduling-constraints.md` |
| 13.4 Randomization process | `lang/constraints/03-randomization.md` |
| 14 Action inferencing | `lang/activity/02-action-inferencing.md` |
| 15 Data coverage | `lang/coverage/01-data-coverage.md` |
| 16 Behavioral coverage | `lang/coverage/02-behavioral-coverage.md` |
| 17 Inheritance, extension, overrides | `lang/structural/07-inheritance-extension-overrides.md` |
| 18 Source organization | `lang/structural/01-packages-and-name-resolution.md` |
| 19 Conditional code processing | `lang/structural/09-conditional-code.md` |
| 20.1, 20.5 exec blocks and target templates | `lang/procedural/01-exec-blocks.md` |
| 20.2, 20.3 Functions | `lang/procedural/02-functions.md` |
| 20.4, 20.6, 20.9, 20.10 Foreign interface | `lang/procedural/04-foreign-interface.md` |
| 20.7 Procedural constructs | `lang/procedural/03-procedural-statements.md` |
| 20.8 Blocking calls and concurrent execution | `lang/platform/02-sync-and-communication.md` |
| 21.1–21.6 `std_pkg` | `lang/platform/05-core-library-api.md` |
| 21.7, 21.8 Executors | `lang/platform/01-executors.md` |
| 21.9 Synchronization and communication | `lang/platform/02-sync-and-communication.md` |
| 21.10–21.13 Address spaces and access | `lang/platform/03-address-spaces.md` |
| 21.13.1, 21.14 Data layout and registers | `lang/platform/04-registers.md` |
| Annex B Formal syntax | not reproduced — consult the LRM when the grammar is genuinely in question |
| Annex C Core library package | mined for signatures across `lang/platform/` |
| Annex F Behavioral coverage semantics | referenced from `lang/coverage/02-behavioral-coverage.md` |
