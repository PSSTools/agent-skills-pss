# Stage 9 — data types and the component tree

You know the operations, their contracts and their notification schemes. Now give them somewhere to
live.

## Choose the subject

A **subject** is the thing an end-to-end operation completes against: a channel, a queue, a port, an
engine. It is whatever `<subject>_probe` reads and `<subject>_wait` waits on.

For a device with N identical instances of something, the choice is between:

| | Consequence |
|---|---|
| **A component per instance** (`ch[4] : dev_ch_c`) | Every register access inside an operation body is **index-free**. Each instance binds its own register group to its own region. The guard and wake channels are per-instance members, which is what they want to be |
| **An index argument** (`transfer(int chan, …)`) | Every access is an indexed lookup; the guard needs an array; the channel number is threaded through every signature |

**Prefer the component per instance.** The cost is that each one binds a top-level register group at
its own base rather than the banks being an array nested in one device-wide group — which is a
one-line difference at elaboration, paid once, in exchange for removing an index from every line of
every operation.

## The component tree

```
pss_top                              ENVIRONMENT — system assembly
├── sys_mem                          address space: the MMIO region + RAM
├── dev : dev_c                      DEVICE — engine-global operations
│   ├── regs : dev_regs_c            engine-global bank
│   └── sub[N] : dev_sub_c           DEVICE — per-subject operations
│       ├── regs : dev_sub_regs_c    one bank each
│       ├── inflight : channel_c<bit,1>
│       └── wake     : channel_c<bit,1>
└── peer[N] : peer_c                 ENVIRONMENT or the peer's own model
```

**The device tree has no `pss_top`.** Where the register file sits in the address map, where RAM is,
and what the scenarios are — only the system knows those, and they change per integration. A device
model that contains them is not the deliverable it claims to be. It should load and elaborate on its
own.

Register *offsets* and instance strides stay in the device's register package: those are device
knowledge.

## Address binding happens on the way down

A child's `init_up` runs **before** its parent's, so anything a child needs during its own
initialization must be set on the way down. The environment's `init_down` adds the region, gets a
handle, and passes it into the device, which derives every subject's bank from the map constants in
one call.

**Name that solve-time constructor `initialize`.** It is a plain identifier, so it needs no escaping
and no whitespace discipline at the call site:

```pss
solve function void initialize(addr_handle_t base);   // on the subject component
```

Do **not** call it `init`, and do not write the escaped form `\init `. Older models use the escaped
identifier on the belief that `init` is reserved; it is not — PSS 3.1 §4.4 Table 3 does not list it,
and the `exec_kind` production (§20.1.1) has only `init_down` and `init_up`, no bare `init`. But
`\init ` carries a real hazard regardless: an escaped identifier is terminated by **whitespace**, so
`\init(` lexes as one token and produces a baffling syntax error, and the trailing space is required
at both declaration and call site. `initialize` is a plain identifier with none of that, and it does
not read as a near-miss for the `init_up` / `init_down` execs it is called from.

## Data types

| Type | When |
|---|---|
| **Config struct** | Once an operation has more than about three related arguments. Named for the thing configured. Gives constraints a home |
| **Status enum** | One per device, three-valued (see `03-classify.md`) |
| **Memory-layout struct** | For anything the device reads *from memory* — a descriptor, a command block. Declare it as the packed layout even if the model has to serialize it by hand; the declaration is the specification |

Keep these in a types package, grouped. Nothing ever wants one enum without its neighbours.

## Actions

Wrap operations in actions at the blocking level only. One action per operation, named for the
operation.

**Do not slice an operation into an arm-action and a wait-action** to express concurrency.
Concurrency in a scenario is *parallel composition of whole operations* — N transfers in parallel,
not N arms followed by N waits. Slicing changes how every scenario is written in order to solve a
problem that is not a scenario problem.

## File layout

Layout is `pss-coding-guidelines`' subject, not this skill's. The short version: one element per
file, components as a top-level file plus a same-named directory, everything else attached with
`extend` under `functions/` or `actions/`; data types and register banks grouped.

```
<dev>_cfg_pkg/
    <dev>_cfg_blocking.pss        the flag, true    ]  mutually exclusive;
    <dev>_cfg_nonblocking.pss     the flag, false   ]  the build selects one
<dev>_types_pkg.pss               status enum incl. PENDING, config structs
<dev>_regs_pkg/                   ← from pss-register-model-create
<dev>_sub_c.pss                   subject component: regs, inflight, wake, initialize
<dev>_sub_c/functions/
    initialize.pss                ]
    <op>_start.pss                ]
    <op>_check.pss                ]  the non-blocking core — every level
    <subject>_probe.pss           ]
    <configuration ops>.pss       ]
    <op>.pss                      ]  gated
    <subject>_wait.pss            ]
<dev>_sub_c/actions/
    <op>_a.pss                    gated
```

**The comments are most of the value.** Each operation file should state its completion contract,
what it waits for, and which decisions shaped it. That reasoning has nowhere else to live, and it is
what a reader needs six months later — the code says *what*, and every interesting question about an
operation model is *why*.

→ Next: `07-verify.md`
