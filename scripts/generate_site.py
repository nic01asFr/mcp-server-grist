#!/usr/bin/env python3
"""
Génère le site public et les fichiers pour agents (dossier site/).

Une porte d'entrée par public, toutes déduites de la même source :
- site/index.html, site/en/index.html : la page grand public (référencement compris) ;
- site/llms.txt, site/SKILL.md : la description et les consignes pour un agent IA ;
- site/fiche-capacites.json, site/commandes.json : la fiche structurée
  (contrats fiche-capacites-0.1 et commandes-0.1 de Widgets-Grist) ;
- site/sitemap.xml.

Sources : les outils réellement enregistrés (signatures et docstrings) et
docs/vitrine.json (texte de la page, rangement des outils par verbe).
Rien de site/ ne s'écrit à la main ; tests/test_site.py échoue si un fichier
n'est plus à jour.

Usage :
    python scripts/generate_site.py          # réécrit site/
    python scripts/generate_site.py --check  # vérifie seulement
"""
import html
import inspect
import json
import re
import sys
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SOURCE = ROOT / "docs" / "vitrine.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_tools_reference as ref  # noqa: E402  (collect_tools, tool_parameters)

# Ordre du cycle de vie (Widgets-Grist, docs/WIDGETS-AUTO-DESCRIPTIFS.md §5)
ORDRE_VERBES = ["presenter", "configurer", "creer", "editer", "structurer",
                "personnaliser", "publier", "exploiter", "recolter", "traiter"]
# Ordre d'affichage sur la page : du plus courant au plus rare
ORDRE_PAGE = ["exploiter", "structurer", "editer", "creer", "configurer"]
# Préfixes d'outils qui n'écrivent jamais rien : garde-fou contre un oubli dans "ecrit"
PREFIXES_LECTURE = ("list_", "describe_", "get_", "filter_", "execute_", "validate_",
                    "export_", "download_")

# Valeurs des exemples d'appel minimal, par nom de paramètre
EXEMPLES = {
    "doc_id": "abc123", "table_id": "Taches", "org_id": 2, "workspace_id": 3,
    "target_workspace_id": 4, "column_id": "statut", "name": "Projets 2026",
    "sql_query": "SELECT titre, statut FROM Taches WHERE statut = ?",
    "records": [{"titre": "Rédiger la doc", "statut": "ouvert"}], "record_ids": [1],
    "schema": {"tables": {"Projets": {"columns": {"nom": "Text"}},
                          "Taches": {"columns": {"titre": "Text", "projet": {
                              "type": "Ref", "target": "Projets", "visible": "nom"}}}}},
    "target_table": "Projets", "visible_column": "nom", "user_email": "quelquun@exemple.fr",
    "access_level": "editors", "attachment_id": 1, "webhook_id": "e1f2a3b4",
    "url": "https://exemple.fr/webhook", "filename": "note.txt", "content_base64": "Qm9uam91cg==",
}
EXEMPLES_PAR_OUTIL = {"update_grist_records": {"records": [{"id": 1, "statut": "fait"}]}}

# Règles du skill : gabarit commun de Widgets-Grist (scripts/generer-skill.js),
# la première adaptée à un serveur sans outil de présentation.
INTERDITS = [
    "Ne jamais promettre un refus côté serveur des valeurs invalides : sans contrôle dans le document, une valeur invalide est acceptée.",
    "Ne jamais deviner un identifiant de document, de table ou de colonne : le demander ou le lire.",
    "Ne jamais présenter comme fait un verbe de la section « Non couvert » : le dire, et proposer l’interface qui le couvre quand il en existe une.",
    "Ne jamais publier ni envoyer ailleurs sans l’accord explicite de la personne.",
]


def regles_ecriture(premier):
    return [
        f"Commencer par `{premier}`, puis descendre la hiérarchie (espace de travail, document, table) pour obtenir des identifiants réels.",
        "Ne citer que les outils listés ci-dessous, avec leur nom exact ; ne jamais en inventer un.",
        "Donner à chaque outil une entrée conforme à son schéma ; en cas d’erreur, relire le message et corriger l’entrée plutôt que réessayer à l’identique.",
        "Écrire en français, sans jargon, dès que le résultat est destiné à une personne.",
        "Annoncer à la personne ce qui sera écrit dans un document avant de l’écrire, et seulement quand l’outil est marqué comme écrivant ; demander confirmation avant toute suppression.",
    ]


# ---------------------------------------------------------------- données

def charger_source():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def version_paquet():
    texte = (ROOT / "src" / "mcp_server_grist" / "version.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', texte).group(1)


def schema_json(annotation):
    """Schéma JSON d'une annotation Python (stable, indépendant de fastmcp)."""
    if annotation in (inspect.Parameter.empty, typing.Any):
        return {}
    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if origin is typing.Union:
        types = [a for a in args if a is not type(None)]
        return schema_json(types[0]) if len(types) == 1 else {"anyOf": [schema_json(a) for a in types]}
    if origin in (list, typing.List):
        return {"type": "array", "items": schema_json(args[0])} if args else {"type": "array"}
    if origin in (dict, typing.Dict) or annotation is dict:
        return {"type": "object"}
    simples = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array"}
    return {"type": simples[annotation]} if annotation in simples else {}


def descriptions_parametres(doc):
    """Descriptions des paramètres, lues dans la section Args: de la docstring."""
    bloc = re.search(r"^Args:\n(.*?)(?:\n\S|\Z)", doc, re.S | re.M)
    if not bloc:
        return {}
    descriptions, courant = {}, None
    for ligne in bloc.group(1).splitlines():
        m = re.match(r"^ {4}(\w+)\s*:\s*(.*)$", ligne)
        if m:
            courant = m.group(1)
            descriptions[courant] = m.group(2).strip()
        elif courant and ligne.strip():
            descriptions[courant] += " " + ligne.strip()
    return {k: re.sub(r"\s+", " ", v).strip() for k, v in descriptions.items()}


def premier_paragraphe(doc):
    return re.sub(r"\s+", " ", doc.split("\n\n", 1)[0]).strip()


def commande(fn, verbe, ecrit):
    doc = inspect.cleandoc(fn.__doc__ or "")
    descs = descriptions_parametres(doc)
    props, requis, exemple = {}, [], {}
    surcharge = EXEMPLES_PAR_OUTIL.get(fn.__name__, {})
    for nom, p in inspect.signature(fn).parameters.items():
        if nom == "ctx":
            continue
        s = schema_json(p.annotation)
        if descs.get(nom):
            s["description"] = descs[nom]
        if p.default is inspect.Parameter.empty:
            requis.append(nom)
            if nom not in surcharge and nom not in EXEMPLES:
                raise ValueError(f"{fn.__name__} : pas de valeur d'exemple pour le paramètre {nom}")
            exemple[nom] = surcharge.get(nom, EXEMPLES.get(nom))
        elif p.default is not None and isinstance(p.default, (str, int, float, bool)):
            s["default"] = p.default
        props[nom] = s
    entree = {"type": "object", "properties": props}
    if requis:
        entree["required"] = requis
    return {
        "nom": fn.__name__,
        "verbe": verbe,
        "description": premier_paragraphe(doc),
        "entree": entree,
        "sortie": {"type": "object"},
        "nature": "pure",
        "ecrit": ecrit,
        "exemples": [{"titre": "Appel minimal", "entree": exemple}],
    }


def construire_donnees(source=None, outils=None):
    """Fiche de capacités et commandes, avec contrôles de cohérence."""
    source = source or charger_source()
    outils = outils or ref.collect_tools()
    par_nom = {fn.__name__: fn for fn in outils}

    verbe_de = {}
    for verbe, noms in source["verbes"].items():
        if verbe not in ORDRE_VERBES:
            raise ValueError(f"verbe inconnu : {verbe}")
        for nom in noms:
            if nom in verbe_de:
                raise ValueError(f"{nom} est rangé sous deux verbes")
            verbe_de[nom] = verbe
    oublies = sorted(set(par_nom) - set(verbe_de))
    inconnus = sorted(set(verbe_de) - set(par_nom))
    if oublies or inconnus:
        raise ValueError(f"rangement des outils incomplet : non rangés {oublies}, inexistants {inconnus}")

    ecrit = source["ecrit"]
    for nom in ecrit:
        if nom not in par_nom:
            raise ValueError(f"ecrit : outil inexistant {nom}")
        if nom.startswith(PREFIXES_LECTURE):
            raise ValueError(f"ecrit : {nom} a un nom d'outil de lecture")
    for nom in par_nom:
        if nom not in ecrit and not nom.startswith(PREFIXES_LECTURE):
            raise ValueError(f"ecrit : {nom} n'est pas un outil de lecture, dire ce qu'il écrit")

    version = version_paquet()
    commandes = [commande(fn, verbe_de[fn.__name__], ecrit.get(fn.__name__, "rien")) for fn in outils]
    verbes = {v: [c["nom"] for c in commandes if c["verbe"] == v] for v in ORDRE_VERBES}
    fiche = {
        "contrat": "fiche-capacites-0.1",
        "widget": source["widget"],
        "version": version,
        "presentation": source["presentation"],
        "verbes": {v: n for v, n in verbes.items() if n},
        "non_couverts": [v for v, n in verbes.items() if not n],
        "contrats": {"produit": [], "lit": []},
        "prerequis": source["prerequis"],
        "limites": source["limites"],
        "exemples": [c["nom"] for c in commandes],
        "interfaces": {"skill": True, "cli": False, "mcp": True, "webmcp": False, "vitrine": True},
    }
    doc_commandes = {"contrat": "commandes-0.1", "widget": source["widget"],
                     "version": version, "commandes": commandes}
    return fiche, doc_commandes


# ---------------------------------------------------------------- agents

def ligne_outil(c):
    requis = c["entree"].get("required", [])
    ecrit = "n’écrit rien" if c["ecrit"] == "rien" else "écrit : " + c["ecrit"]
    return (f"- `{c['nom']}` : {c['description']}\n  Entrée requise : "
            + (", ".join(f"`{r}`" for r in requis) if requis else "aucune")
            + f" ; appelle l’API Grist ; {ecrit}.")


def rendre_skill(fiche, commandes, source):
    titre, resume = fiche["presentation"]["titre"], fiche["presentation"]["resume"]
    par_nom = {c["nom"]: c for c in commandes["commandes"]}
    l = ["---", f"name: {fiche['widget']}", "description: " + json.dumps(f"{titre} : {resume}", ensure_ascii=False),
         "---", "", f"# {titre}", "", resume, "",
         f"Version {fiche['version']}. Généré depuis `fiche-capacites.json` (contrat {fiche['contrat']}) "
         "et `commandes.json` : ne pas modifier à la main.", "", "## Interfaces", ""]
    noms = {"skill": "ce skill", "cli": "ligne de commande", "mcp": "serveur MCP",
            "webmcp": "page WebMCP", "vitrine": "page de présentation"}
    l += [f"- {nom} : {'disponible' if fiche['interfaces'][cle] else 'non disponible'}." for cle, nom in noms.items()]
    l += ["", "Lancer le serveur : `uvx mcp-server-grist` (stdio), avec les variables `GRIST_API_KEY` et `GRIST_API_URL`.",
          "", "## Outils", ""]
    for verbe in ORDRE_VERBES:
        for i, nom in enumerate(fiche["verbes"].get(verbe, [])):
            if i == 0:
                l += [f"### {verbe}", ""]
            l.append(ligne_outil(par_nom[nom]))
        if fiche["verbes"].get(verbe):
            l.append("")
    l += ["## Non couvert", "", "Verbes sans outil : " + ", ".join(fiche["non_couverts"]) + ".", "",
          "## Limites", ""]
    l += [f"- {x}" for x in fiche["limites"]]
    l += ["", "## Règles d’écriture", ""]
    l += [f"- {r}" for r in regles_ecriture(source["premier_outil"])]
    l += ["", "## Interdits", ""]
    l += [f"- {r}" for r in INTERDITS]
    return "\n".join(l) + "\n"


def rendre_llms(fiche, commandes, source):
    base = source["base"]
    l = [f"# {fiche['presentation']['titre']}", "", f"> {fiche['presentation']['resume']}", "",
         f"Version {fiche['version']}. Fiche de capacités : fiche-capacites.json (contrat {fiche['contrat']}).", "",
         "## Comment appeler ces outils", "",
         "- Serveur MCP (stdio) : `uvx mcp-server-grist`, ou `pip install mcp-server-grist` puis `mcp-server-grist`.",
         "- Serveur MCP (HTTP) : `mcp-server-grist --transport streamable-http --port 8000` (point d’accès /mcp).",
         "- Configuration : `GRIST_API_KEY` (obligatoire) et `GRIST_API_URL` (ex. https://grist.numerique.gouv.fr/api).",
         f"- Premier outil à appeler : `{source['premier_outil']}`.", "", "## Outils", ""]
    for c in commandes["commandes"]:
        l.append(f"- `{c['nom']}` ({c['verbe']}) : {c['description']}")
    l += ["", "## Ce qui n’est pas couvert", "", "Verbes sans outil : " + ", ".join(fiche["non_couverts"]) + ".",
          "", "## Limites", ""]
    l += [f"- {x}" for x in fiche["limites"]]
    l += ["", "## Pour aller plus loin", "",
          f"- [Page de présentation]({base})",
          f"- [Consignes pour un agent (SKILL.md)]({base}SKILL.md)",
          f"- [Fiche de capacités]({base}fiche-capacites.json) et [commandes]({base}commandes.json)",
          f"- [Référence des outils]({source['liens']['reference']})",
          f"- [Code source]({source['liens']['depot']})"]
    return "\n".join(l) + "\n"


# ---------------------------------------------------------------- page

def e(texte):
    return html.escape(str(texte), quote=True)


def variables_themes(theme):
    """Variables CSS : thème par défaut sur :root, les autres sur :root[data-theme=…], en clair et en sombre."""
    var = lambda p: " ".join(f"--{k}: {v};" for k, v in p.items())  # noqa: E731
    lignes = []
    for cle, t in theme["themes"].items():
        sel = ":root" if cle == theme["defaut"] else f':root[data-theme="{cle}"]'
        lignes.append(f"{sel} {{ {var(t['clair'])} }}")
        lignes.append(f"@media (prefers-color-scheme: dark) {{ {sel} {{ {var(t['sombre'])} }} }}")
    return "\n".join(lignes)


def css(theme):
    """Feuille de style : les thèmes de docs/vitrine.json (défaut : grist.numerique.gouv.fr)."""
    return f"""
{variables_themes(theme)}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--fond); color: var(--texte);
  font: 16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; -webkit-font-smoothing: antialiased; }}
a {{ color: var(--accent); }}
.bouton.creux, h3 a {{ color: var(--texte); }}
main {{ max-width: 60rem; margin: 0 auto; padding: 4rem 1.5rem 6rem; }}
h1, h2, h3 {{ font-weight: 600; line-height: 1.15; text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(2.2rem, 6vw, 3.4rem); letter-spacing: -.01em; }}
h2 {{ font-size: 1.5rem; margin-bottom: 1rem; }}
h3 {{ font-size: 1.1rem; margin-bottom: .5rem; }}
p {{ margin: 0 0 1rem; color: var(--texte-2); }}
section {{ margin-top: 4rem; }}
.eyebrow {{ font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); font-weight: 600; margin-bottom: 1.4rem; }}
.pitch {{ font-size: 1.15rem; max-width: 42rem; margin-top: 1.2rem; }}
.tags {{ display: flex; flex-wrap: wrap; gap: .4rem; margin: 1rem 0; }}
.tag {{ font-size: .78rem; padding: .2rem .6rem; border-radius: 999px; border: 1px solid var(--bord); color: var(--texte-2); }}
.faits {{ display: flex; flex-wrap: wrap; gap: 1.4rem; font-size: .88rem; color: var(--texte-2); margin: 1.4rem 0; }}
.faits b {{ color: var(--texte); font-weight: 600; }}
.boutons {{ display: flex; flex-wrap: wrap; gap: .6rem; margin-top: 1.4rem; }}
.bouton {{ display: inline-block; padding: .55rem 1rem; border-radius: 6px; text-decoration: none; font-size: .92rem;
  background: var(--bouton); color: var(--bouton-texte); font-weight: 600; }}
.bouton.creux {{ background: transparent; color: var(--texte); border: 1px solid var(--bord); }}
.themes {{ display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; margin-top: 1rem; font-size: .82rem; color: var(--texte-2); }}
.themes[hidden] {{ display: none; }}
.themes button {{ font: inherit; padding: .2rem .7rem; border-radius: 999px; border: 1px solid var(--bord);
  background: transparent; color: var(--texte); cursor: pointer; }}
.themes button[aria-pressed="true"] {{ background: var(--bouton); color: var(--bouton-texte); border-color: var(--bouton); }}
.grille {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1rem; }}
.carte {{ background: var(--surface); border: 1px solid var(--bord); border-radius: 8px; padding: 1.2rem; }}
.carte p {{ margin: 0; }}
pre {{ background: var(--surface-2); border: 1px solid var(--bord); border-radius: 6px; padding: .9rem 1rem;
  overflow-x: auto; font-size: .82rem; line-height: 1.5; }}
code {{ font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; font-size: .85em; }}
p code, li code, td code {{ background: var(--surface); border: 1px solid var(--bord); border-radius: 4px; padding: .1rem .35rem; }}
.tableau {{ overflow-x: auto; }}
.grille > *, main > section > div {{ min-width: 0; }}
pre {{ max-width: 100%; }}
table {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
th, td {{ text-align: left; vertical-align: top; padding: .6rem .5rem; border-bottom: 1px solid var(--bord); }}
th {{ font-weight: 600; }}
td {{ color: var(--texte-2); }}
td:first-child {{ color: var(--texte); font-weight: 600; }}
ul.outils {{ list-style: none; padding: 0; margin: 0 0 1.6rem; columns: 2 18rem; column-gap: 2rem; }}
ul.outils li {{ break-inside: avoid; margin-bottom: .6rem; color: var(--texte-2); font-size: .92rem; }}
ul.outils li code {{ color: var(--texte); }}
ul.liste li {{ color: var(--texte-2); margin-bottom: .5rem; }}
.pied {{ max-width: 60rem; margin: 0 auto; padding: 2rem 1.5rem 4rem; border-top: 1px solid var(--bord);
  font-size: .85rem; color: var(--texte-2); }}
"""


def premiere_phrase(texte):
    m = re.match(r"(.+?[.!?])(\s|$)", texte)
    return m.group(1) if m else texte


def rendre_page(langue, fiche, commandes, source):
    t = source[langue]
    liens = source["liens"]
    base = source["base"]
    url = base if langue == "fr" else base + "en/"
    racine = "" if langue == "fr" else "../"
    autre = base + "en/" if langue == "fr" else base
    par_nom = {c["nom"]: c for c in commandes["commandes"]}
    nb = len(commandes["commandes"])

    def lien_public(p):
        if p.get("lien"):
            return f'<p><a href="{e(liens[p["lien"]])}">{e(p["libelle"])}</a></p>'
        if p.get("lien_local"):
            return f'<p><a href="{racine}{e(p["lien_local"])}">{e(p["libelle"])}</a></p>'
        return ""

    publics = "\n".join(
        f'<div class="carte"><h3>{e(p["qui"])}</h3><p>{e(p["texte"])}</p>{lien_public(p)}</div>' for p in t["publics"])
    clients = "\n".join(
        f'<div><h3>{e(c["nom"])}</h3><p>{e(c["texte"])}</p><pre><code>{e(c["code"])}</code></pre></div>'
        for c in t["clients"])
    entetes = "".join(f"<th>{e(x)}</th>" for x in t["officiel_entetes"])
    lignes = "\n".join("<tr>" + "".join(f"<td>{e(x)}</td>" for x in ligne) + "</tr>" for ligne in t["officiel_lignes"])
    outils = []
    for verbe in ORDRE_PAGE:
        noms = fiche["verbes"].get(verbe, [])
        if not noms:
            continue
        items = "\n".join(f'<li><code>{e(n)}</code> {e(premiere_phrase(par_nom[n]["description"]))}</li>' for n in noms)
        outils.append(f'<h3>{e(t["verbes_libelles"][verbe])}</h3>\n<ul class="outils">\n{items}\n</ul>')
    lies = "\n".join(
        f'<div class="carte"><h3><a href="{e(liens[x["lien"]])}">{e(x["nom"])}</a></h3><p>{e(x["texte"])}</p></div>'
        for x in t["lies"])

    ld = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": fiche["presentation"]["titre"], "description": t["description"], "url": url,
        "inLanguage": langue, "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Windows, macOS, Linux", "softwareVersion": fiche["version"],
        "license": "https://opensource.org/licenses/MIT", "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
        "sameAs": [liens["depot"], liens["pypi"]],
    }
    ld_json = json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c")
    meta = "\n".join([
        f'<link rel="canonical" href="{e(url)}">',
        f'<link rel="alternate" hreflang="fr" href="{e(base)}">',
        f'<link rel="alternate" hreflang="en" href="{e(base)}en/">',
        f'<link rel="alternate" hreflang="x-default" href="{e(base)}">',
        f'<link rel="alternate" type="text/plain" href="{racine}llms.txt" title="llms.txt">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="mcp-server-grist">',
        f'<meta property="og:locale" content="{"fr_FR" if langue == "fr" else "en_US"}">',
        f'<meta property="og:url" content="{e(url)}">',
        f'<meta property="og:title" content="{e(t["titre_page"])}">',
        f'<meta property="og:description" content="{e(t["description"])}">',
        '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{e(t["titre_page"])}">',
        f'<meta name="twitter:description" content="{e(t["description"])}">',
    ])
    return f"""<!doctype html>
<html lang="{langue}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(t["titre_page"])}</title>
<meta name="description" content="{e(t["description"])}">
{meta}
<script type="application/ld+json">{ld_json}</script>
<style>{css(source["theme"])}</style>
<script>{script_theme(source["theme"])}</script>
</head>
<body>
<main>
<p class="eyebrow">{e(t["eyebrow"])}</p>
<h1>{e(t["h1"])}</h1>
<p class="pitch">{e(t["pitch"])}</p>
<div class="tags">{"".join(f'<span class="tag">{e(x)}</span>' for x in t["instances"])}</div>
<p class="faits"><span><b>v{e(fiche["version"])}</b></span><span><b>{nb}</b> {e(t["mot_outils"])}</span><span>Python 3.10+</span><span>MIT</span></p>
<div class="boutons">
<a class="bouton" href="#installer">{e(t["installer_titre"])}</a>
<a class="bouton creux" href="{e(liens["depot"])}">{e(t["boutons"]["depot"])}</a>
<a class="bouton creux" href="{e(liens["pypi"])}">{e(t["boutons"]["pypi"])}</a>
<a class="bouton creux" href="{racine}llms.txt">{e(t["boutons"]["agents"])}</a>
<a class="bouton creux" href="{e(autre)}" hreflang="{"en" if langue == "fr" else "fr"}">{e(t["boutons"]["autre_langue"])}</a>
</div>
{selecteur_theme(source["theme"], t, langue)}

<section>
<h2>{e(t["publics_titre"])}</h2>
<div class="grille">
{publics}
</div>
</section>

<section id="installer">
<h2>{e(t["installer_titre"])}</h2>
<p>{e(t["installer_intro"])}</p>
{clients}
</section>

<section>
<h2>{e(t["demandes_titre"])}</h2>
<ul class="liste">
{"".join(f"<li>{e(x)}</li>" for x in t["demandes"])}
</ul>
</section>

<section>
<h2>{e(t["officiel_titre"])}</h2>
<p>{e(t["officiel_intro"])}</p>
<div class="tableau"><table>
<thead><tr>{entetes}</tr></thead>
<tbody>
{lignes}
</tbody>
</table></div>
</section>

<section>
<h2>{e(t["outils_titre"])}</h2>
<p>{e(t["outils_intro"])} <a href="{e(liens["reference"])}">{e(liens["reference"].rsplit("/", 1)[-1])}</a></p>
{chr(10).join(outils)}
</section>

<section>
<h2>{e(t["savoir_titre"])}</h2>
<ul class="liste">
{"".join(f"<li>{e(x)}</li>" for x in t["savoir"])}
</ul>
</section>

<section>
<h2>{e(t["lies_titre"])}</h2>
<div class="grille">
{lies}
</div>
</section>
</main>
<footer class="pied">
<p>{e(t["pied"])}</p>
<p><a href="{e(liens["depot"])}">GitHub</a> · <a href="{e(liens["pypi"])}">PyPI</a> · <a href="{racine}llms.txt">llms.txt</a> · <a href="{racine}SKILL.md">SKILL.md</a> · <a href="{racine}fiche-capacites.json">fiche-capacites.json</a> — {e(t["genere"])}, v{e(fiche["version"])}.</p>
</footer>
</body>
</html>
"""


CLE_THEME = "mcp-server-grist-theme"


def script_theme(theme):
    """Applique le thème mémorisé avant l'affichage ; sans JavaScript, le thème par défaut s'applique."""
    connus = json.dumps(sorted(theme["themes"]))
    return ("(function () { try { var t = localStorage.getItem('" + CLE_THEME + "'); "
            "if (" + connus + ".indexOf(t) >= 0 && t !== '" + theme["defaut"] + "') "
            "document.documentElement.setAttribute('data-theme', t); } catch (e) {} })();")


def selecteur_theme(theme, t, langue):
    """Boutons de choix du thème (affichés seulement si JavaScript fonctionne)."""
    boutons = "".join(
        f'<button type="button" data-choix="{e(cle)}" aria-pressed="{"true" if cle == theme["defaut"] else "false"}">'
        f'{e(th["nom"][langue])}</button>' for cle, th in theme["themes"].items())
    js = ("(function () { var d = document.documentElement, defaut = '" + theme["defaut"] + "', "
          "zone = document.getElementById('themes'); zone.hidden = false; "
          "function maj() { var actif = d.getAttribute('data-theme') || defaut; "
          "zone.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.choix === actif)); }); } "
          "zone.addEventListener('click', function (ev) { var b = ev.target.closest('button'); if (!b) return; "
          "var c = b.dataset.choix; if (c === defaut) d.removeAttribute('data-theme'); else d.setAttribute('data-theme', c); "
          "try { localStorage.setItem('" + CLE_THEME + "', c); } catch (e) {} maj(); }); maj(); })();")
    return (f'<div class="themes" id="themes" hidden role="group" aria-label="{e(t["theme_libelle"])}">'
            f'<span>{e(t["theme_libelle"])} :</span>{boutons}</div>\n<script>{js}</script>')


def rendre_sitemap(source):
    base = source["base"]
    urls = []
    for loc in (base, base + "en/"):
        urls.append(
            f"  <url>\n    <loc>{loc}</loc>\n"
            f'    <xhtml:link rel="alternate" hreflang="fr" href="{base}"/>\n'
            f'    <xhtml:link rel="alternate" hreflang="en" href="{base}en/"/>\n  </url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n")


# ---------------------------------------------------------------- ensemble

def construire():
    """Tous les fichiers de site/ : {chemin relatif: contenu}."""
    source = charger_source()
    fiche, commandes = construire_donnees(source)
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=2) + "\n"  # noqa: E731
    return {
        "index.html": rendre_page("fr", fiche, commandes, source),
        "en/index.html": rendre_page("en", fiche, commandes, source),
        "llms.txt": rendre_llms(fiche, commandes, source),
        "SKILL.md": rendre_skill(fiche, commandes, source),
        "fiche-capacites.json": dump(fiche),
        "commandes.json": dump(commandes),
        "sitemap.xml": rendre_sitemap(source),
    }


def ecarts(fichiers):
    """Différences entre site/ et ce que le générateur produirait."""
    attendus = set(fichiers)
    presents = {str(p.relative_to(SITE)) for p in SITE.rglob("*") if p.is_file()} if SITE.exists() else set()
    problemes = [f"manquant : {f}" for f in sorted(attendus - presents)]
    problemes += [f"en trop : {f}" for f in sorted(presents - attendus)]
    problemes += [f"pas à jour : {f}" for f in sorted(attendus & presents)
                  if (SITE / f).read_text(encoding="utf-8") != fichiers[f]]
    return problemes


def main() -> int:
    fichiers = construire()
    if "--check" in sys.argv:
        problemes = ecarts(fichiers)
        if problemes:
            print("site/ n'est pas à jour (lancez python scripts/generate_site.py) :")
            print("\n".join("  " + p for p in problemes))
            return 1
        print("site/ à jour.")
        return 0
    for f in {str(p.relative_to(SITE)) for p in SITE.rglob("*") if p.is_file()} - set(fichiers) if SITE.exists() else ():
        (SITE / f).unlink()
    for chemin, contenu in fichiers.items():
        cible = SITE / chemin
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_text(contenu, encoding="utf-8")
    print(f"site/ écrit : {', '.join(sorted(fichiers))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
