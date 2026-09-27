import os
import sys

import agent_skills_pss
from agent_skills_pss.skills import get_skill_dirs

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points

    def _eps(group):
        return entry_points(group=group)
else:
    from importlib.metadata import entry_points as _all

    def _eps(group):
        return _all().get(group, [])

EXPECTED = {
    "pss-coding-guidelines",
    "pss-language-ref",
    "pss-operation-model-create",
    "pss-register-model-create",
}


def _frontmatter(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    assert lines[0] == "---", path
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        if line and not line[0].isspace() and ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


def test_entrypoint_registered():
    eps = [ep for ep in _eps("agent.skills") if ep.name == "agent-skills-pss"]
    assert len(eps) == 1
    assert eps[0].load() is get_skill_dirs


def test_skill_dirs():
    dirs = get_skill_dirs()
    assert {os.path.basename(d) for d in dirs} == EXPECTED
    for d in dirs:
        assert os.path.isabs(d)
        fm = _frontmatter(os.path.join(d, "SKILL.md"))
        assert fm.get("name") == os.path.basename(d)
        assert fm.get("description")


def test_skills_are_packaged():
    # Run against the installed wheel: the skills must come from package data,
    # not from a source checkout that happens to be nearby.
    pkg = os.path.dirname(os.path.abspath(agent_skills_pss.__file__))
    if os.path.basename(os.path.dirname(pkg)) == "src":
        return  # editable/source run
    for d in get_skill_dirs():
        assert d.startswith(os.path.join(pkg, "share", "skills"))
