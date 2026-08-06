# Domain: platform — the target side

Supporting domain, and the largest one by API surface. You are here because you need something
the **core library** provides: where code runs, where data lives, and how registers and memory
are touched.

Almost everything in this domain is `target`-qualified: it belongs in `exec body`, `run_start`,
or `run_end`, not in a solve exec. The exceptions — address-space *setup* and register-group
handle association — are the reverse, and belong in `init_down`/`init_up` only. Getting that
backwards is the characteristic failure here; it is tier 2 at best, and on a parser-only tool
it is tier 4.

---

## Decide: what am I reaching for?

| You need… | Use | Page |
|---|---|---|
| to print / log from the generated test | `message()` (target) | `05-core-library-api.md` |
| to print during generation | `print()` / `format()` (solve) | `05-core-library-api.md` |
| a random value at runtime | `urandom()` / `urandom_range()` | `05-core-library-api.md` |
| to report a problem | `error()` / `fatal()` | `05-core-library-api.md` |
| to say *which processing element* an action runs on | executor claim | `01-executors.md` |
| to make two actions on different executors rendezvous | `sync_pkg` channels / target-time sync | `02-sync-and-communication.md` |
| memory the tool should allocate for you | address space + claim | `03-address-spaces.md` |
| a fixed MMIO window at a known address | non-allocatable region | `03-address-spaces.md` |
| to read/write raw memory | `read*`/`write*` on an `addr_handle_t` | `03-address-spaces.md` |
| to model a device's register map | `reg_c` / `reg_group_c` | `04-registers.md` |
| a bit-exact memory layout for a struct | `packed_s<>` + `sizeof_s<>` | `04-registers.md` |

### The three sequences worth memorizing

**Address space → region → handle → access.** You add a region to a space during elaboration,
get an `addr_handle_t`, and *use* it from a target exec. Allocation (`addr_claim_s`) is the
solve-side alternative to a fixed region: the tool picks the address.

**Register model.** `packed_s` struct describes a register's fields → `reg_c<struct>` is that
register → `reg_group_c` contains registers and answers offset queries → the top-level group
gets `set_handle()` once, from an init exec → actions call `read()`/`write()`/`write_fields()`
from `exec body`.

**Executors.** Actions declare what kind of processing element they need (a claim); executor
groups declare what exists; the tool matches them. If you never say anything, you get the
tool's default — which is usually right, and worth leaving alone until it isn't.

---

## Pages

| Page | Covers |
|---|---|
| `01-executors.md` | `executor_c`, `executor_group_c`, executor claims and traits, matching rules, executor resources, query function, target execution units (§21.7, §21.8) |
| `02-sync-and-communication.md` | blocking calls and concurrent execution, `yield`, `sync_pkg` channels (§20.8, §21.9) |
| `03-address-spaces.md` | address space categories, traits, regions, claims and allocation modes, allocation consistency, address space groups, handles, access operations (§21.10–21.13) |
| `04-registers.md` | `packed_s` and packing rules, `sizeof_s`, `reg_c`, `reg_group_c`, offset schemes, access modes, field access, symbolic register representation (§21.13.1, §21.14) |
| `05-core-library-api.md` | `std_pkg`: string formatting, output, message logging, file operations, error reporting, randomization, floating point, standard annotations (§21.1–21.6) |

## See also

- `../procedural/01-exec-blocks.md` — which exec kind each of these calls belongs in.
- `../structural/02-components.md` — `pure component`, which is what register models are built
  from.
- `../data/03-collections.md` — `packed_s` restricts what field types are allowed.
- `../../playbooks/06-access-registers-and-memory.md` — task-first.
