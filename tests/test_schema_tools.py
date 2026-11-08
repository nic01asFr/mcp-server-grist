"""
Tests des outils de schéma et de colonnes (v0.2.2).

Un faux client reproduit le comportement de Grist observé sur une vraie
instance (grist-core 1.7) :
- AddTable / AddColumn ignorent untieColIdFromLabel et description
  (AddTable ignore aussi visibleCol) ;
- AddTable peut modifier un ID de colonne ('Prénom' -> 'Prenom') ;
- visibleCol seul ne règle pas l'affichage : il faut SetDisplayFormula ;
- AddReverseColumn crée une colonne inverse nommée d'après la table source.
"""
import json

import pytest

from mcp_server_grist.models import GristColumn, GristTable
from mcp_server_grist.tools import administration, schema
from mcp_server_grist.tools.utils import merge_widget_options, prepare_column_fields
from mcp_server_grist.types import parse_schema_dict


class FakeGrist:
    """Client Grist en mémoire qui enregistre les actions reçues."""

    def __init__(self, supports_reverse=True):
        self.supports_reverse = supports_reverse
        self.tables = {}          # table_id -> {col_id: fields}
        self.records = {}         # table_id -> [fields]
        self.actions = []         # toutes les user actions appliquées
        self.created_columns = [] # appels create_columns
        self._next_ref = 100

    def _ref(self):
        self._next_ref += 1
        return self._next_ref

    # --- API utilisée par les outils ---
    async def list_tables(self, doc_id):
        return [GristTable(id=t, fields={}) for t in self.tables]

    async def list_columns(self, doc_id, table_id):
        return [GristColumn(id=c, fields=dict(f)) for c, f in self.tables[table_id].items()]

    async def create_columns(self, doc_id, table_id, payload):
        self.created_columns.append((table_id, payload))
        out = []
        for col in payload["columns"]:
            fields = col["fields"]
            kept = {k: v for k, v in fields.items()
                    if k in ("type", "label", "formula", "isFormula", "widgetOptions", "visibleCol")}
            kept.setdefault("label", col["id"])
            kept.update(colRef=self._ref(), untieColIdFromLabel=False)
            self.tables[table_id][col["id"]] = kept
            out.append({"id": col["id"]})
        return out

    async def add_records(self, doc_id, table_id, records):
        self.records.setdefault(table_id, []).extend(records)
        return list(range(1, len(records) + 1))

    async def apply_user_actions(self, doc_id, actions):
        results = []
        for action in actions:
            name = action[0]
            if name == "AddReverseColumn" and not self.supports_reverse:
                raise ValueError("Blocked by access rules: 'AddReverseColumn' actions are not controlled")
            results.append(getattr(self, "_do_" + name)(*action[1:]))
        self.actions.extend(actions)
        return {"retValues": results}

    def _do_AddTable(self, table_id, columns):
        self.tables[table_id] = {}
        actual = []
        for info in columns:
            col_id = info["id"].replace("é", "e")   # Grist assainit les identifiants
            self.tables[table_id][col_id] = {
                "type": info.get("type", "Any"), "label": info.get("label", col_id),
                "widgetOptions": info.get("widgetOptions", ""), "colRef": self._ref(),
                "untieColIdFromLabel": False,
            }
            actual.append(col_id)
        return {"table_id": table_id, "columns": actual}

    def _do_ModifyColumn(self, table_id, col_id, values):
        self.tables[table_id][col_id].update(values)

    def _do_SetDisplayFormula(self, table_id, field_ref, col_ref, formula):
        for fields in self.tables[table_id].values():
            if fields["colRef"] == col_ref:
                fields["display"] = formula

    def _do_AddReverseColumn(self, table_id, col_id):
        target = self.tables[table_id][col_id]["type"].split(":", 1)[1]
        self.tables[target][table_id] = {
            "type": f"RefList:{table_id}", "label": table_id, "colRef": self._ref(),
        }
        return {"colId": table_id, "colRef": self.tables[target][table_id]["colRef"]}

    def _do_RenameColumn(self, table_id, old, new):
        self.tables[table_id][new] = self.tables[table_id].pop(old)
        return new


@pytest.fixture
def grist(monkeypatch):
    fake = FakeGrist()
    monkeypatch.setattr(schema, "get_client", lambda ctx=None: fake)
    monkeypatch.setattr(administration, "get_client", lambda ctx=None: fake)
    return fake


SCHEMA = {
    "tables": {
        "Agents": {"columns": {
            "nom": {"type": "Text", "label": "Nom", "description": "Nom de famille"},
            "service": {"type": "Choice", "choices": ["A", "B"]},
        }},
        "Projets": {"columns": {
            "titre": "Text",
            "chef": {"type": "Ref", "target": "Agents", "visible": "nom"},
        }},
        "Taches": {"columns": {
            "titre": "Text",
            "projet": {"type": "Ref", "target": "Projets", "visible": "titre", "reverse": "taches"},
            "resp": {"type": "Ref:Agents", "visible": "Nom"},
        }},
    },
    "data": {"Agents": [{"nom": "Dupont", "service": "A"}]},
}


# --- Fonctions pures -------------------------------------------------------

def test_choices_merged_into_widget_options():
    fields = prepare_column_fields({"id": "s", "type": "Choice", "choices": ["x", "y"]})
    assert "choices" not in fields
    assert json.loads(fields["widgetOptions"]) == {"choices": ["x", "y"]}


def test_choices_merged_with_existing_widget_options():
    assert json.loads(merge_widget_options({"alignment": "left"}, ["a"])) == {
        "alignment": "left", "choices": ["a"]}
    assert json.loads(merge_widget_options('{"alignment": "left"}', ["a"])) == {
        "alignment": "left", "choices": ["a"]}
    assert merge_widget_options('{"a": 1}') == '{"a": 1}'
    assert merge_widget_options(None) is None


def test_ref_type_notation_is_normalized():
    col = parse_schema_dict({"tables": {"T": {"columns": {"r": "Ref:Agents"}}}}).tables[0].columns[0]
    assert (col.type, col.target_table) == ("Ref", "Agents")
    assert parse_schema_dict({"tables": {"T": {"columns": {"r": "RefList:A"}}}}).tables[0].get_reference_columns()


def test_ref_type_notation_conflicting_target_rejected():
    with pytest.raises(ValueError):
        parse_schema_dict({"tables": {"T": {"columns": {"r": {"type": "Ref:A", "target": "B"}}}}})


# --- create_table / create_column -----------------------------------------

async def test_create_table_applies_choices_untie_and_description(grist):
    result = await administration.create_table("doc", "Clients", [
        {"id": "Prénom", "type": "Text", "description": "prénom usuel"},
        {"id": "statut", "type": "Choice", "choices": ["Actif"]},
    ])
    assert result["success"], result
    add_table = next(a for a in grist.actions if a[0] == "AddTable")
    for info in add_table[2]:
        assert not set(info) & {"choices", "description", "untieColIdFromLabel"}
    cols = grist.tables["Clients"]
    assert json.loads(cols["statut"]["widgetOptions"]) == {"choices": ["Actif"]}
    assert cols["Prenom"]["description"] == "prénom usuel"
    assert cols["Prenom"]["label"] == "Prénom"
    assert all(c["untieColIdFromLabel"] is True for c in cols.values())
    assert result["columns"] == {"Prénom": "Prenom", "statut": "statut"}
    assert any("Prenom" in w for w in result["warnings"])


async def test_create_column_sets_display_formula_and_untie(grist):
    await administration.create_table("doc", "Clients", [{"id": "nom", "type": "Text"}])
    await administration.create_table("doc", "Commandes", [{"id": "num", "type": "Text"}])
    nom_ref = grist.tables["Clients"]["nom"]["colRef"]
    result = await administration.create_column(
        "doc", "Commandes", "client", "Ref:Clients", visible_col=nom_ref, description="d")
    assert result["success"] and "warnings" not in result, result
    col = grist.tables["Commandes"]["client"]
    assert col["display"] == "$client.nom"
    assert col["untieColIdFromLabel"] is True and col["description"] == "d"


async def test_create_column_never_sends_untie_false(grist):
    # untieColIdFromLabel=False ferait renommer l'ID d'après le libellé par Grist.
    await administration.create_table("doc", "T", [{"id": "a", "type": "Text"}])
    grist.actions.clear()
    result = await administration.create_column(
        "doc", "T", "montant", "Numeric", label="Montant", untie_col_id_from_label=False)
    assert result["success"], result
    assert not any(a[0] == "ModifyColumn" and a[3].get("untieColIdFromLabel") is False
                   for a in grist.actions)
    assert "montant" in grist.tables["T"]


async def test_modify_column_visible_col_sets_display_formula(grist, monkeypatch):
    await administration.create_table("doc", "Clients", [{"id": "nom", "type": "Text"}])
    await administration.create_table("doc", "Commandes", [{"id": "num", "type": "Text"}])
    await administration.create_column("doc", "Commandes", "client", "Ref:Clients")

    async def modify_columns(doc_id, table_id, payload):
        for col in payload["columns"]:
            grist.tables[table_id][col["id"]].update(col["fields"])
    monkeypatch.setattr(grist, "modify_columns", modify_columns, raising=False)

    nom_ref = grist.tables["Clients"]["nom"]["colRef"]
    result = await administration.modify_column("doc", "Commandes", "client", visible_col=nom_ref)
    assert result["success"], result
    assert grist.tables["Commandes"]["client"]["display"] == "$client.nom"


# --- create_schema --------------------------------------------------------

async def test_create_schema_references_display_and_two_way_reverse(grist):
    result = await schema.create_schema("doc", SCHEMA)
    assert result["success"], result
    assert grist.tables["Projets"]["chef"]["display"] == "$chef.nom"
    assert grist.tables["Taches"]["resp"]["display"] == "$resp.nom"   # 'Ref:Agents' + libellé 'Nom'
    assert ["AddReverseColumn", "Taches", "projet"] in grist.actions
    assert "taches" in grist.tables["Projets"]                       # renommée depuis 'Taches'
    # 'Ref:Agents' créée en phase référence, jamais dans AddTable
    add_taches = next(a for a in grist.actions if a[0] == "AddTable" and a[1] == "Taches")
    assert [c["id"] for c in add_taches[2]] == ["titre"]
    assert len(grist.records["Agents"]) == 1


async def test_create_schema_rerun_creates_nothing(grist):
    await schema.create_schema("doc", SCHEMA)
    actions, created, records = len(grist.actions), len(grist.created_columns), len(grist.records["Agents"])
    result = await schema.create_schema("doc", SCHEMA)
    assert result["success"], result
    assert (len(grist.actions), len(grist.created_columns), len(grist.records["Agents"])) == (
        actions, created, records)


async def test_create_schema_invalid_visible_column_creates_nothing(grist):
    bad = json.loads(json.dumps(SCHEMA))
    bad["tables"]["Projets"]["columns"]["chef"]["visible"] = "nmo"
    result = await schema.create_schema("doc", bad)
    assert not result["success"]
    assert any("nmo" in e for e in result["details"]["errors"])
    assert grist.actions == [] and grist.tables == {}


async def test_create_schema_skip_existing_false_creates_nothing(grist):
    grist.tables["Agents"] = {}
    result = await schema.create_schema("doc", SCHEMA, skip_existing=False)
    assert not result["success"]
    assert grist.actions == [] and set(grist.tables) == {"Agents"}


async def test_reverse_falls_back_to_formula_on_old_grist(grist):
    grist.supports_reverse = False
    result = await schema.create_schema("doc", SCHEMA)
    assert result["success"], result
    reverse = grist.tables["Projets"]["taches"]
    assert reverse["formula"] == "Taches.lookupRecords(projet=$id)"
    assert reverse["display"] == "$taches.titre"
    assert any("double sens" in w for w in result["report"]["warnings"])


# --- create_reference_column ------------------------------------------------

async def test_create_reference_column_with_reverse(grist):
    await administration.create_table("doc", "Clients", [{"id": "nom", "type": "Text"}])
    await administration.create_table("doc", "Commandes", [{"id": "num", "type": "Text"}])
    result = await schema.create_reference_column(
        "doc", "Commandes", "client", "Clients", "nom", reverse_column="commandes")
    assert result["success"], result
    assert grist.tables["Commandes"]["client"]["display"] == "$client.nom"
    assert result["reverse_column"] == {"id": "commandes", "table": "Clients", "two_way": True}


async def test_create_reference_column_reports_api_errors(grist, monkeypatch):
    async def broken(doc_id):
        raise ValueError("HTTP error: 401 - invalid API key")
    monkeypatch.setattr(grist, "list_tables", broken)
    result = await schema.create_reference_column("doc", "A", "x", "B", "nom")
    assert not result["success"]
    assert "401" in result["message"] and "inexistante" not in result["message"]
