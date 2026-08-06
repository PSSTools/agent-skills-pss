# Flow objects: `buffer`, `stream`, `state`

*Domain: structural. LRM §9.3.*

Flow objects are how actions relate to each other **without knowing about each other**. One
action declares "I produce a `desc_s`", another declares "I consume a `desc_s`", and the tool
works out that one must precede the other. Their kind determines the scheduling rule.

## When you are writing this

- The user said "X produces Y which Z uses".
- The user described an ordering: "configure before transfer", "the descriptor must exist
  first".
- The user described a mode or condition: "in DMA mode", "after reset", "while the clock is
  gated".
- You are about to write a sequential activity block and should ask whether the order has a
  *reason*.

## Decide

The kind is a scheduling decision, not a data decision. Choose by **when the two actions run**:

| | Producers | Consumers | Scheduling rule |
|---|---|---|---|
| `buffer` | exactly 1 | 0 or more | consumer begins **after** producer **completes** |
| `stream` | exactly 1 | exactly 1 | producer and consumer **begin at the same time** |
| `state` | pool holds one at a time | any number of readers | a writer never overlaps any reader or writer of that pool |

| The situation | Kind |
|---|---|
| a descriptor written to memory, later read | `buffer` |
| a data block handed off and then reused | `buffer` |
| packets flowing over a bus while both ends run | `stream` |
| a notification consumed by exactly one waiter | `stream` |
| "the device is in low-power mode" | `state` |
| "this operation is only legal after reset" | `state` |
| just data, with no ordering meaning | `struct` — not a flow object |
| exclusive occupancy, contents irrelevant | `resource` — see `05-resource-objects.md` |

Two rules of thumb that resolve most cases:

- **If you want one producer and many concurrent consumers, use `buffer`, not `stream`.** A
  stream has exactly one of each.
- **If the consumer doesn't care what's inside, it isn't a flow object.** It's a resource.

## Canonical form

```pss
struct mem_segment_s { rand bit[32] addr; rand bit[16] size; }

buffer data_buff_s  { rand mem_segment_s seg; }
stream data_stream_s{ rand mem_segment_s seg; }

state  mode_s {
    rand mode_e mode;
    constraint initial -> mode == IDLE;      // the pool's starting state
    constraint mode != prev.mode;            // relate to the previous state object
}

component dma_c {
    pool data_buff_s buf_p;   bind buf_p *;
    pool mode_s      mode_p;  bind mode_p *;

    action produce { output data_buff_s out_data; }

    action consume {
        input  data_buff_s in_data;
        input  mode_s      m;                       // reads the current state
        constraint m.mode == DMA;
    }

    action set_mode { output mode_s m; }            // writes the pool's state
}
```

Object-reference arrays are legal, including multidimensional:

```pss
action gather { input data_buff_s srcs[4]; }        // == 4 distinct input fields
```

## Rules

### Common

- Flow object reference fields are declared in actions with `input` or `output` (§9.3.4).
- Instance fields of a flow-object type — used as plain data — may only be declared under
  *higher-level flow object types*, as their data attribute. You cannot put a `buffer` field
  inside a `struct`.
- Flow object types may inherit from previously defined `struct`s or from the same flow kind.
- An object-reference array is **entirely input or entirely output**; the mode is not per
  element (§9.3.4a-b).
- Array elements may be bound to *different* pools, but only via **explicit** binding — default
  type-based binding applies to all elements uniformly (§9.3.4c).

### `buffer` (§9.3.1)

- Exactly one producing action; zero or more consumers.
- A consumer shall not begin until the producer **completes**.
- An action may not have the same buffer object as both an input and an output.
- The type implies no particular memory layout.

### `stream` (§9.3.2)

- Exactly one producer **and exactly one consumer**.
- Both begin execution at the same time, after the same preceding action(s) complete — i.e.
  they run in `parallel`.

### `state` (§9.3.3)

- A state pool contains **a single object at a time**, reflecting the last state output to it.
- The built-in `initial` (bool) is true for the object present before any action has written
  the pool. Constrain it to define the starting state.
- The built-in `prev` references the previous state object of the same type. It is **unresolved
  for the initial object**, and is only available inside a state type declaration or extension.
- Accessing `initial` on an *instance field* of a state type is illegal.
- An action outputting a state object completes before any inputting action begins.
- A writer shall not be concurrent with any other reader or writer of that pool. Readers may be
  concurrent with each other.
- A state action must be bound to a state pool via a **static bind directive** (§12.3) — see
  `06-pools-and-binding.md`.
- Each element of an array of state references must be bound to a **different** state pool,
  because a state pool holds only one object (§9.3.4d).

## Gotchas

**Using `stream` for one-to-many.**
```pss
stream pkt_s {}
action src  { output pkt_s p; }
action sink { input  pkt_s p; }
activity { do src; parallel { do sink; do sink; } }   // WRONG: two consumers
```
*Tier 3* — no legal scenario; the message will be about binding, not about the `stream`
declaration. Use `buffer` if the data persists, or two streams if there are genuinely two flows.

**Using `buffer` when both must run concurrently.** The consumer waits for the producer to
*complete*, so a `buffer` can never model a live handoff. Symptom: the test serializes when the
user expected overlap. *Tier 4* — completely legal, just not what was asked for.

**Same object as input and output of one action.**
```pss
action rmw { input buf_s b; output buf_s b; }   // WRONG for a buffer
```
*Tier 1–2.* Model read-modify-write as two objects, or as a `state`.

**`prev` on the initial state.** Unresolved. Guard it:
```pss
constraint !initial -> mode != prev.mode;    // RIGHT
constraint mode != prev.mode;                // WRONG for the initial object
```
*Tier 3–4.*

**Forgetting the state pool bind.** A `state` input/output without a static pool bind has
nothing to read or write. *Tier 3*, and the message points at the pool, not here.

**Modeling exclusivity as a flow object.** "Four DMA channels" as a `buffer` gives you data
dependencies between unrelated transfers. It's a `resource`. *Tier 4.*

**Expecting default binding to spread an array across pools.** It cannot — default binding is
type-based and uniform. Use explicit `bind` per element. *Tier 3.*

## See also

- `06-pools-and-binding.md` — a flow object is useless until a pool of its type is bound.
- `05-resource-objects.md` — the other kind of inter-action relationship.
- `../activity/02-action-inferencing.md` — an unbound `input` will pull in a producer you did
  not write.
- `../activity/03-scheduling-semantics.md` — what "completes" and "concurrent" mean formally.
- `../constraints/02-scheduling-constraints.md` — `state` sequencing constraints.
- `../../playbooks/01-model-a-flow.md` — task-first.
