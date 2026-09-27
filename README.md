# agent-skills-pss

Agent skills for writing, reviewing and deriving PSS (Portable Test and
Stimulus, Accellera 3.1) models:

| skill | purpose |
|---|---|
| `pss-language-ref` | PSS language reference, checker rules and playbooks |
| `pss-coding-guidelines` | coding style and file-organization rules for PSS source |
| `pss-operation-model-create` | derive a PSS operation model from a spec, RTL or testbench |
| `pss-register-model-create` | derive a PSS register model from a spec, register tables or IP-XACT |

## Installation

```
pip install agent-skills-pss
```

The package registers its skills under the `agent.skills` entry-point group,
so [IVPM](https://github.com/fvutils/ivpm) links them into `.agents/skills/`
(and the Claude/Cursor mirrors) of any project whose environment has it
installed:

```yaml
# ivpm.yaml
deps:
  - name: agent-skills-pss
    src: pypi
```

To locate the skills directly:

```python
from agent_skills_pss import get_skill_dirs
get_skill_dirs()   # absolute paths, one per skill directory
```

A git checkout of this repository works too: the skills live in `skills/`.

## Releasing

Releases are tag-driven; there is no version to bump in the source.

```
git tag v0.2.0 && git push origin v0.2.0
```

CI derives the version from git (`scripts/stamp-version.sh`). A tag build is
the tag's version; any other build is named relative to the nearest tag, e.g.
`0.1.0.post3+gh.g1b7503e` is three commits after `v0.1.0`, built on GitHub.
Those local versions are rejected by PyPI, so only a tag can be published.
A plain source checkout reports `0.0.0`.
