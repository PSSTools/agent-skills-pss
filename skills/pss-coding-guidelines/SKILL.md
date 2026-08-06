---
name: pss-coding-guidelines
description: Project coding style and file-organization rules for PSS (Portable Test and Stimulus)
  source in this repository — a file is a unit of behaviour, so components, functions and actions get
  their own files while data types and register banks are grouped; components are top-level files
  plus a same-named companion directory whose actions/ and functions/ subdirectories attach elements
  via `extend`. Use when creating, moving, or reviewing any .pss file under src/pss (or any other PSS
  source tree in this project), or when deciding where a new component, action, function, register,
  or data type belongs.
---

# PSS coding guidelines

Style and organization rules for PSS source in this project. For *language* questions — what a
construct means, what is legal — use the `pss-procedural-stmts` skill. This skill answers **where
code goes and what it looks like**, not what it does.

This guide is expected to grow. When a new convention is agreed, add a numbered rule here rather
than leaving it implicit in the source.

---

## 1. A file is a unit of *behaviour*, not a unit of syntax

Every **component**, **function**, and **action** gets its own file, named after the element it
defines. `transfer_single()` lives in `transfer_single.pss`.

**Everything else — enums, structs, register value types — is grouped.** These are looked up by type
name from wherever they are used and are never included selectively, so a file per type buys nothing
and costs navigation.

The test to apply, in order:

1. **Would a build ever want this element without its neighbours?** If yes, own file. That is what
   makes functions and actions separate: `functions/` can be included without `actions/`, and a
   single operation can be pulled in on its own.
2. **Would you go looking for this element by its own name?** If yes, own file. Operations and
   components are what you navigate to; a struct you reach by following a reference.
3. **Otherwise, group it** with the things it is meaningless apart from.

Applied:

| Element | Granularity |
|---------|-------------|
| component | own file (+ companion directory, rule 3) |
| function / operation | own file under `functions/` |
| action | own file under `actions/` |
| enums and plain data structs | **one file per package** |
| register value struct + its register type | together (rule 5.1) |
| all registers of one bank + the group that maps them | **one file per bank** (rule 5.2) |
| foreign-function prototypes forming one contract | one file |

Rough ceiling: if a grouped file passes ~300 lines, split it along whatever seam is already there
(one enum file and one struct file; one file per register bank). Do not split it back down to one
element per file.

## 2. A scope is a directory — when it needs to be

A *scope* is the root PSS source directory (`src/pss`, the implicit global package) or a package
directory beneath it (`src/pss/wb_dma_regs_pkg`).

A package earns a **directory** only when rule 1 gives it more than one file. Otherwise it is a
single file at the parent scope, named for the package: `src/pss/wb_dma_types_pkg.pss`,
`src/pss/wb_dma_hs_pkg.pss`. A directory holding one file is noise.

- Files directly in a package directory open that package explicitly:
  ```pss
  package wb_dma_regs_pkg {
      // ...
  }
  ```
- Files directly in `src/pss` declare into the global scope with no `package` wrapper.
- The directory name **is** the package name. Do not put `foo_pkg` content in a directory named
  anything else.

## 3. Components are top-level in their scope

Within a scope, each component is a file *and* a same-named directory:

```
src/pss/wb_dma_ops_c.pss          <- the component declaration
src/pss/wb_dma_ops_c/             <- everything that extends it
```

The `.pss` file holds **only** the component's skeleton:

- the `component` declaration itself,
- its data members (sub-components, attributes, register groups),
- its `init` solve-time constructor and/or `exec init_down` / `init_up` blocks.

Nothing else. Read the declaration file and you know the component's shape.

```pss
// src/pss/wb_dma_ops_c.pss
import addr_reg_pkg::*;
import wb_dma_regs_pkg::*;

component wb_dma_ops_c {
    wb_dma_regs_c    regs;

    solve function void \init (addr_handle_t base) {
        regs.set_handle(base);
    }
}
```

Note `\init` — an escaped identifier, because `init` collides with the `exec init` keyword. It needs
the trailing space; see rule 9.

## 4. Elements attach via `extend`, grouped by kind

Everything else about a component goes in its companion directory, in a subdirectory named for the
element **kind** (plural), one file per element:

```
src/pss/wb_dma_ops_c/
    actions/
        mem_to_mem.pss
        mem_to_dev.pss
    functions/
        transfer_single.pss
```

Each such file re-opens the component with `extend`:

```pss
// src/pss/wb_dma_ops_c/functions/transfer_single.pss
extend component wb_dma_ops_c {
    function void transfer_single() {
    }
}
```

Grouping by kind — rather than by feature — is deliberate: a build can include `functions/` without
`actions/`, or one action without its siblings. Keep the subdirectory names stable so file lists can
glob them.

Established subdirectories:

| Directory | Holds |
|-----------|-------|
| `actions/` | one `extend component C { action A { … } }` per file |
| `functions/` | one `extend component C { function … }` per file |

**Only behaviour gets a kind directory.** There is no `structs/` or `enums/` — rule 1 groups those
into a package file. Add a new kind directory only for something that is separately includable and
separately findable, and record it in the table above.

> **Toolchain note.** `pssparser` currently fails to resolve composite field access inside an
> `extend component` body — locals and parameters alike, in both functions and `exec` bodies — while
> accepting the identical body written inline. That collides with this rule, so expect
> `root ref-path element … is not a composite scope` errors on correct source. Do **not** restructure
> around it; see `src/pss/README.md` for the reproducer and the current status.

## 5. Packages follow the same pattern

A package directory is just another scope, so the rules recurse — subject to rule 2: a package with
one file's worth of content is one file, not a directory.

```
src/pss/wb_dma_types_pkg.pss                <- all the enums and plain structs
src/pss/wb_dma_hs_pkg.pss                   <- one foreign-function contract
src/pss/wb_dma_regs_pkg/                    <- earns a directory: one file per bank
    wb_dma_regs_c.pss
    wb_dma_ch_regs_c.pss
```

### 5.1 A register's value struct lives with its register

A register type and the packed struct that gives it its fields are one thing described twice, so
they are never separated.

### 5.2 A register bank is one file

A bank is one artifact with one address decode: its registers are meaningless apart from the group
that maps them, and nobody includes a single register on its own. So the group component, every
register type it holds, and every value struct those need go in **one file, named for the group**.

```pss
// src/pss/wb_dma_regs_pkg/wb_dma_ch_regs_c.pss
package wb_dma_regs_pkg {
    import std_pkg::*;
    import addr_reg_pkg::*;

    struct ch_ctrl_s : packed_s<> { rand bit enable; rand bit[31] reserved; }
    pure component ch_ctrl_r : reg_c<ch_ctrl_s, READWRITE, 32> {}

    // … the rest of the bank's registers …

    pure component wb_dma_ch_regs_c : reg_group_c {
        ch_ctrl_r  ctrl;
        // …
        function bit[64] get_offset_of_instance(string name) { … }
        function bit[64] get_offset_of_instance_array(string name, int index) { … }
    }
}
```

The offset functions stay **inline** in the group rather than moving to a `functions/` directory:
they are the address decode, so they belong next to the declarations they decode, and nobody
includes a register group without them. This is the one place rule 4 does not apply.

Address-map constants (base, stride, channel count) go in the top-level bank's file — they describe
where the whole register file sits.

## 6. Naming

| Suffix | Kind |
|--------|------|
| `_c` | component |
| `_pkg` | package |
| `_r` | register type |
| `_s` | struct |
| `_e` | enum |
| `_a` | action |

A file that holds one element is named for it, suffix included. A **grouped** file (rule 1) is named
for the thing that gives the group its identity: the package (`wb_dma_types_pkg.pss`) or the register
group (`wb_dma_ch_regs_c.pss`).

An operation keeps the name the operation model gives it — `transfer_single`, not `do_transfer` —
and its action wrapper is that name plus `_a`.

## 7. Imports

`import` is **per file**. Put every import a file needs at its top; never rely on one that happens to
appear in a sibling file, even a sibling extending the same component. A file must be readable, and
resolvable, on its own terms.

Wildcard-import the package and use short names. Qualify (`wb_dma_regs_pkg::WB_DMA_CH_STRIDE`) only
where the qualification tells the reader something — typically a constant reached from outside its
own package, where the package name is the useful context.

Register and packed-struct files need both `std_pkg` (for `packed_s`) and `addr_reg_pkg` (for
`reg_c` / `reg_group_c`).

## 8. File order is dependency order

`pssparser` resolves in the order files are presented, and a reference to a type declared in a
later-listed file of the same package is a hard crash rather than a diagnostic. So a file list for
this tree is ordered, not globbed: data types, then register banks, then components leaf-first, then
`pss_top`.

Two consequences for how you write:

- **Avoid cross-file forward references within a package.** If two files in one package have an
  order dependency, that is usually a sign the elements belong in the same file — which is how
  `wb_dma_word_r` ended up in the channel bank that uses it rather than the global one.
- A plain alphabetical `find … | sort` will not build this tree. The working order is recorded in
  `src/pss/README.md`.

## 9. Escaped identifiers need the trailing space

`\init` is written `\init (…)`, with a space before the paren. An escaped identifier is terminated by
whitespace, so `\init(` lexes as a single token and produces a confusing syntax error. The same
applies at the call site: `ch[i].\init (i, h);`.

---

## Checklist for a new element

1. Which scope does it belong to — root, or a package?
2. Does it deserve its own file (rule 1)? Components, functions and actions do; types and registers
   join an existing grouped file.
3. Component? → top-level `<name>.pss` + `<name>/` directory, skeleton only: members and `init`.
4. Function or action? → `<component>/functions|actions/<name>.pss`, wrapped in
   `extend component <component> { … }`.
5. Data type or register? → append it to the package file or the register-bank file, in the section
   it belongs to.
6. File name matches the element, or the group's identity, with the rule-6 suffix.
7. Imports at the top of this file, not inherited from a sibling.
8. Did you add a dependency on a file that sorts later in its package? Merge instead (rule 8).
