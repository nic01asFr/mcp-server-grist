#!/usr/bin/env python3
"""
Génère docs/tools-reference.mdx à partir des outils réellement enregistrés.

Les paramètres viennent des signatures Python et les descriptions des
docstrings : la référence est exacte par construction, et indépendante de
la version de fastmcp. Le test tests/test_docs.py échoue si le fichier
n'est plus à jour.

Usage :
    python scripts/generate_tools_reference.py          # réécrit le fichier
    python scripts/generate_tools_reference.py --check  # vérifie seulement
"""
import inspect
import sys
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "tools-reference.mdx"
sys.path.insert(0, str(ROOT / "src"))

# Ordre et titres des catégories (module des outils -> titre)
CATEGORIES = {
    "navigation": "Navigation",
    "records": "Enregistrements",
    "queries": "Requêtes SQL",
    "administration": "Administration",
    "schema": "Schéma et références",
    "access": "Gestion des accès",
    "export": "Export et téléchargement",
    "attachments": "Pièces jointes",
    "webhooks": "Webhooks",
}


class _Recorder:
    """Faux serveur MCP qui enregistre les fonctions déclarées comme outils."""

    def __init__(self):
        self.tools = []

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools.append(fn)
            return fn
        return decorator


def collect_tools():
    """Retourne les fonctions-outils, dans l'ordre d'enregistrement du serveur."""
    from mcp_server_grist.tools import register_all_tools
    recorder = _Recorder()
    register_all_tools(recorder)
    return recorder.tools


def format_type(annotation) -> str:
    """Rend une annotation de façon stable (indépendante de la version de Python)."""
    if annotation is inspect.Parameter.empty:
        return ""
    if annotation is type(None):
        return "None"
    if annotation is typing.Any:
        return "Any"
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        inner = ", ".join(format_type(a) for a in non_none)
        if len(non_none) < len(args):
            return f"Optional[{inner}]" if len(non_none) == 1 else f"Optional[Union[{inner}]]"
        return f"Union[{inner}]"
    if origin is not None:
        name = {list: "List", dict: "Dict", tuple: "Tuple", set: "Set"}.get(
            origin, getattr(origin, "__name__", str(origin)))
        return f"{name}[{', '.join(format_type(a) for a in args)}]" if args else name
    return getattr(annotation, "__name__", str(annotation))


def tool_parameters(fn):
    """Paramètres exposés aux clients MCP (ctx est injecté par le serveur)."""
    params = []
    for name, p in inspect.signature(fn).parameters.items():
        if name == "ctx":
            continue
        required = p.default is inspect.Parameter.empty
        params.append({
            "name": name,
            "type": format_type(p.annotation),
            "required": required,
            "default": None if required else repr(p.default),
        })
    return params


def render(tools) -> str:
    by_category = {}
    for fn in tools:
        by_category.setdefault(fn.__module__.rsplit(".", 1)[-1], []).append(fn)

    lines = [
        "---",
        'title: "Référence des outils"',
        'description: "Liste complète des outils MCP Grist, avec leurs paramètres"',
        "---",
        "",
        "{/* Fichier généré par scripts/generate_tools_reference.py : ne pas modifier à la main. */}",
        "",
        "# Référence des outils MCP Grist",
        "",
        f"Le serveur expose **{len(tools)} outils**. Le paramètre `ctx` des fonctions Python",
        "est fourni par le serveur : les clients MCP ne le voient pas.",
        "",
    ]
    order = list(CATEGORIES) + sorted(set(by_category) - set(CATEGORIES))
    for category in order:
        fns = by_category.get(category)
        if not fns:
            continue
        lines += [f"## {CATEGORIES.get(category, category)}", ""]
        lines += [f"- [`{fn.__name__}`](#{fn.__name__})" for fn in fns]
        lines.append("")
        for fn in fns:
            lines += [f"### {fn.__name__}", ""]
            params = tool_parameters(fn)
            if params:
                lines += ["| Paramètre | Type | Requis | Défaut |", "|---|---|---|---|"]
                for p in params:
                    default = f"`{p['default']}`" if p["default"] is not None else ""
                    type_ = f"`{p['type']}`" if p["type"] else ""
                    lines.append(
                        f"| `{p['name']}` | {type_} | {'oui' if p['required'] else 'non'} | {default} |"
                    )
            else:
                lines.append("Aucun paramètre.")
            lines.append("")
            doc = inspect.cleandoc(fn.__doc__ or "").strip()
            if doc:
                lines += ["```text", doc, "```", ""]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    content = render(collect_tools())
    if "--check" in sys.argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print(f"{OUTPUT.relative_to(ROOT)} n'est pas à jour : "
                  "lancez python scripts/generate_tools_reference.py")
            return 1
        print("Référence des outils à jour.")
        return 0
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)} écrit ({content.count(chr(10) + '### ')} outils).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
