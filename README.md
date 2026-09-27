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

Bump `version_info` in `src/agent_skills_pss/__about__.py`, then tag:

```
git tag v0.1.0 && git push origin v0.1.0
```

CI checks that the tag matches the source version before publishing to PyPI.
Builds from branch pushes carry a `.dev<run>+<forge>.g<sha>` version and cannot
be published.
