# Checker rules — implementation specifications

**This directory is not skill content.** It is a specification for whoever implements static
checks. It lives outside `reference/` deliberately: the pages an agent reads stay tool-neutral
(rules and check tiers, never tool flags), while these write-ups target a concrete checker API.

## Why these rules

`../reference/tooling.md` defines four check tiers. Tier 1 (parse and name resolution) is handled
by any front end. **Tiers 2–4 are where PSS models actually go wrong**, and a mechanical check
is a far stronger guarantee than a documented rule. Every rule here is one this skill already
documents; implementing it converts a "read the page and remember" into a diagnostic.

The rules were selected by one criterion: **mechanically decidable from the linked AST**, with
no solver.

## Target API

The write-ups target the `pssparser` Python checker plug-in interface:

```python
from pssparser.checkers.base import CheckerBase
from pssparser.checkers.markerdef import MarkerDef

class PlatformChecker(CheckerBase):
    name        = "platform"
    description = "Solve/target platform qualification"

    marker_defs = [
        MarkerDef(
            id="PSL001",
            severity="error",
            summary="Solve function called from a target exec block",
            detail="...",
        ),
    ]

    def check(self, context) -> None:
        ...   # walk the linked AST; report against the marker ids above
```

Registration is via the `pssparser.checkers` entry-point group, or ad hoc with
`--load-checker MODULE:CLASS`.

**Marker prefix.** `pssparser` reserves the `PSS` prefix for its built-in `CoreChecker`
(`PSS001`–`PSS005`, see `pssparser/checkers/core_checker.py`) and asks plug-ins to pick their
own three-letter prefix. These rules use **`PSL`** ("PSS language"), numbered by group:
`PSL00x` platform, `PSL01x` functions, `PSL02x` registers, `PSL03x` structural, `PSL04x`
heuristics.

## Write-up format

Each rule is specified with:

| Field | Content |
|---|---|
| **Rule** | the normative statement, as it appears in the page's *Rules* section |
| **LRM clause** | the citation, so the implementer can verify independently |
| **Tier** | 2, 3, or 4. Tier 3 rules may need solver support and are marked *deferred* |
| **Marker** | proposed id, severity, summary, and detail text in `MarkerDef` shape |
| **Detection** | what to walk in the linked AST, and the precise condition |
| **False-positive risk** | constructs that look like violations but are not |
| **Triggering example** | a minimal model that must report |
| **Near-miss example** | a minimal model that must **not** report |

## Files

| File | Rules | Tier | Status |
|---|---|---|---|
| `01-platform-qualification.md` | solve/target function calls; component attribute writes; `pre_solve` handle access | 2 | **implemented** |
| `02-function-declarations.md` | parameter directions on native functions; `pure` misuse; bare non-`void` calls; `const` parameter passing | 2 | spec only |
| `03-registers-and-layout.md` | conflicting offset schemes; `packed_s` extension; `reg_c`/`reg_group_c` extension; nested `set_handle`; access-mode violations | 2 | spec only |
| `04-structural.md` | atomic-vs-compound actions; pool/bind coverage; exact pool type match; `pure component` contents | 2–3 | spec only |
| `05-unchecked-hazards.md` | `match` without `default`; `super;` omission; side effects in `message()`; auto-binned wide coverpoints | 4 (heuristic) | spec only |

The implementation lives in **`packages/pss-lang-checkers/`**.

Rules in `05-` are **heuristics**, not decision procedures. They should ship as `warning`
severity and be individually disableable — a false positive on a stylistic rule costs more
trust than the rule is worth.

## Implementation order

`01-` is **done** — see `packages/pss-lang-checkers/`, which also documents the two AST-binding
limitations that shape any implementation against the current `pssparser` build (calls resolve
by name, not by symbol path; procedural statements carry no source location). `03-` next: register-model
violations are silent and expensive. `02-` and `04-` after. `05-` last, and only with the
severity caveat above.
