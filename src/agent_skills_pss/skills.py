#****************************************************************************
#* skills.py
#*
#* Agent-skill discovery hook. Registered via the 'agent.skills' entry-point
#* group so that any environment with agent-skills-pss installed exposes the
#* PSS agent skills to IVPM (and any other agent.skills consumer).
#****************************************************************************
import os
from typing import List


def _skills_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # Installed wheel: the repository's skills/ tree is packaged under share/.
    root = os.path.join(here, "share", "skills")
    if os.path.isdir(root):
        return root
    # Editable install / source checkout: src/agent_skills_pss -> <repo>/skills
    return os.path.normpath(os.path.join(here, "..", "..", "skills"))


def get_skill_dirs() -> List[str]:
    """Return the directories of the bundled PSS agent skills.

    Referenced by the ``agent.skills`` entry-point in pyproject.toml. Each
    returned directory contains a ``SKILL.md`` with name/description frontmatter.
    Must stay cheap and side-effect free: consumers call it in a subprocess.
    """
    root = _skills_root()
    if not os.path.isdir(root):
        return []
    return sorted(
        os.path.join(root, d) for d in os.listdir(root)
        if os.path.isfile(os.path.join(root, d, "SKILL.md")))
