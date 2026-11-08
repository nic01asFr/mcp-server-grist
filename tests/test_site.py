"""
Le site public et les fichiers pour agents (site/) correspondent aux outils réels.

- site/ est exactement ce que scripts/generate_site.py produit (régénérer avec
  `python scripts/generate_site.py`) ;
- chaque outil est rangé sous un seul verbe et dit s'il écrit ;
- la fiche respecte la forme du contrat fiche-capacites-0.1 (Widgets-Grist) ;
- llms.txt et SKILL.md citent chaque outil, et aucun outil inexistant.
"""
import copy
import importlib.util
import inspect
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("generate_site", ROOT / "scripts" / "generate_site.py")
site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site)

OUTILS = {fn.__name__: fn for fn in site.ref.collect_tools()}
SITE = ROOT / "site"
FICHE = json.loads((SITE / "fiche-capacites.json").read_text(encoding="utf-8"))
COMMANDES = json.loads((SITE / "commandes.json").read_text(encoding="utf-8"))


def test_site_is_up_to_date():
    problemes = site.ecarts(site.construire())
    assert not problemes, "site/ n'est pas à jour (python scripts/generate_site.py) : " + ", ".join(problemes)


def test_every_tool_has_exactly_one_verb():
    ranges = [n for noms in FICHE["verbes"].values() for n in noms]
    assert sorted(ranges) == sorted(OUTILS)
    assert set(FICHE["non_couverts"]) == set(site.ORDRE_VERBES) - set(FICHE["verbes"])


def test_unmapped_tool_is_refused():
    source = site.charger_source()
    source = copy.deepcopy(source)
    source["verbes"]["exploiter"].remove("list_tables")
    with pytest.raises(ValueError, match="list_tables"):
        site.construire_donnees(source)


def test_writing_tool_must_say_what_it_writes():
    source = copy.deepcopy(site.charger_source())
    del source["ecrit"]["delete_column"]
    with pytest.raises(ValueError, match="delete_column"):
        site.construire_donnees(source)


def test_capability_sheet_shape():
    # Forme du contrat fiche-capacites-0.1 (docs/fiche-capacites-0.1.schema.json de Widgets-Grist)
    autorises = {"contrat", "widget", "version", "presentation", "verbes", "non_couverts", "contrats",
                 "prerequis", "limites", "exemples", "entree_webmcp", "interfaces"}
    requis = {"contrat", "widget", "version", "presentation", "verbes", "non_couverts", "contrats"}
    assert requis <= set(FICHE) <= autorises
    assert FICHE["contrat"] == "fiche-capacites-0.1"
    assert re.fullmatch(r"[a-z][a-z0-9-]*", FICHE["widget"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", FICHE["version"])
    assert set(FICHE["presentation"]) == {"titre", "resume"}
    assert set(FICHE["verbes"]) <= set(site.ORDRE_VERBES)
    assert set(FICHE["contrats"]) == {"produit", "lit"}
    assert set(FICHE["interfaces"]) <= {"skill", "cli", "mcp", "webmcp", "vitrine"}
    assert FICHE["prerequis"].get("acces_grist") in ("none", "read table", "full")


def test_commands_match_tool_signatures():
    assert [c["nom"] for c in COMMANDES["commandes"]] == list(OUTILS)
    for c in COMMANDES["commandes"]:
        params = {n: p for n, p in inspect.signature(OUTILS[c["nom"]]).parameters.items() if n != "ctx"}
        assert set(c["entree"]["properties"]) == set(params), c["nom"]
        requis = [n for n, p in params.items() if p.default is inspect.Parameter.empty]
        assert c["entree"].get("required", []) == requis, c["nom"]
        assert set(c["exemples"][0]["entree"]) == set(requis), c["nom"]


@pytest.mark.parametrize("fichier", ["llms.txt", "SKILL.md"])
def test_agent_files_cite_every_tool_and_no_other(fichier):
    texte = (SITE / fichier).read_text(encoding="utf-8")
    cites = set(re.findall(r"`([a-z_]+)`", texte))
    assert not [n for n in OUTILS if n not in cites], "outils non cités"
    parametres = {n for fn in OUTILS.values() for n in inspect.signature(fn).parameters}
    inconnus = sorted(n for n in cites if "_" in n and n not in OUTILS and n not in parametres)
    assert not inconnus, f"{fichier} cite des outils inexistants : {inconnus}"


@pytest.mark.parametrize("page", ["index.html", "en/index.html"])
def test_pages_have_seo_and_agent_links(page):
    texte = (SITE / page).read_text(encoding="utf-8")
    for attendu in ('rel="canonical"', 'hreflang="fr"', 'hreflang="en"', 'application/ld+json',
                    'property="og:title"', 'llms.txt', 'SKILL.md'):
        assert attendu in texte, f"{page} : {attendu} manquant"
    assert all(f"<code>{n}</code>" in texte for n in OUTILS), f"{page} : un outil n'est pas listé"


def _luminance(hexa):
    canaux = [int(hexa.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contraste(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


THEMES = site.charger_source()["theme"]


def test_default_theme_is_declared():
    assert THEMES["defaut"] in THEMES["themes"]


@pytest.mark.parametrize("nom", sorted(THEMES["themes"]))
@pytest.mark.parametrize("mode", ["clair", "sombre"])
def test_theme_contrasts_are_readable(nom, mode):
    # Seuil WCAG 2.x AA pour du texte : 4,5:1
    t = THEMES["themes"][nom][mode]
    paires = [("texte", "fond"), ("texte", "surface"), ("texte", "surface-2"), ("texte-2", "fond"),
              ("texte-2", "surface"), ("accent", "fond"), ("accent", "surface"), ("bouton-texte", "bouton")]
    faibles = [f"{a} sur {b} : {_contraste(t[a], t[b]):.2f}" for a, b in paires if _contraste(t[a], t[b]) < 4.5]
    assert not faibles, f"contrastes insuffisants ({nom}, {mode}) : {faibles}"
