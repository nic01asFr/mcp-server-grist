"""
Cohérence entre la documentation et les outils réellement exposés.

- docs/tools-reference.mdx doit être à jour (régénérer avec
  `python scripts/generate_tools_reference.py`) ;
- le README doit citer chaque outil, et aucun outil inexistant ;
- les exemples `await outil(param=...)` de la doc doivent utiliser des
  outils et des paramètres qui existent.
"""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "generate_tools_reference", ROOT / "scripts" / "generate_tools_reference.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

TOOLS = {fn.__name__: fn for fn in gen.collect_tools()}
# Préfixes des noms d'outils : sert à repérer dans la doc ce qui se présente comme un outil.
TOOL_PREFIXES = ("list_", "describe_", "get_", "create_", "modify_", "delete_", "add_",
                 "update_", "download_", "upload_", "filter_", "execute_", "validate_",
                 "export_", "move_", "force_", "clear_")
HAND_WRITTEN_DOCS = [ROOT / "README.md", ROOT / "docs" / "index.mdx"]


def test_tools_reference_is_up_to_date():
    current = (ROOT / "docs" / "tools-reference.mdx").read_text(encoding="utf-8")
    assert current == gen.render(gen.collect_tools()), (
        "docs/tools-reference.mdx n'est pas à jour : "
        "lancez python scripts/generate_tools_reference.py")


def test_readme_lists_every_tool():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = [name for name in TOOLS if f"`{name}`" not in readme]
    assert not missing, f"Outils absents du README : {missing}"


@pytest.mark.parametrize("path", HAND_WRITTEN_DOCS, ids=lambda p: p.name)
def test_docs_do_not_mention_unknown_tools(path):
    names = set(re.findall(r"`([a-z_]+)`", path.read_text(encoding="utf-8")))
    unknown = sorted(n for n in names if n.startswith(TOOL_PREFIXES) and n not in TOOLS)
    assert not unknown, f"{path.name} cite des outils inexistants : {unknown}"


def _example_calls(text):
    """Extrait (outil, [paramètres nommés]) des appels `await outil(...)`."""
    for match in re.finditer(r"await (\w+)\(", text):
        depth, i, start = 1, match.end(), match.end()
        while depth and i < len(text):
            depth += {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}.get(text[i], 0)
            i += 1
        args, depth, top = text[start:i - 1], 0, []
        for j, ch in enumerate(args):
            depth += {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}.get(ch, 0)
            if depth == 0:
                kw = re.match(r"\s*(\w+)\s*=(?!=)", args[j:]) if j == 0 or args[j - 1] in ",(" else None
                if kw:
                    top.append(kw.group(1))
        yield match.group(1), top


@pytest.mark.parametrize("path", HAND_WRITTEN_DOCS, ids=lambda p: p.name)
def test_doc_examples_use_real_tools_and_parameters(path):
    problems = []
    for tool, kwargs in _example_calls(path.read_text(encoding="utf-8")):
        if tool not in TOOLS:
            problems.append(f"outil inexistant : {tool}")
            continue
        allowed = {p["name"] for p in gen.tool_parameters(TOOLS[tool])}
        problems += [f"{tool}: paramètre inconnu '{k}'" for k in kwargs if k not in allowed]
    assert not problems, f"{path.name} : {problems}"
