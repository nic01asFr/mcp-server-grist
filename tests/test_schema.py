"""
Tests pour Grist MCP Server v0.2.0.

Ces tests valident:
- Les corrections de format des payloads
- Les nouveaux outils de schéma
- La gestion des types de colonnes
"""
import json
import pytest
from typing import Any, Dict

# Import des modules à tester
from mcp_server_grist.types import (
    ColumnDefinition,
    TableDefinition,
    SchemaDefinition,
    validate_column_type,
    prepare_widget_options,
    parse_schema_dict,
    GRIST_COLUMN_TYPES,
)
from mcp_server_grist.tools.utils import (
    prepare_column_fields,
    prepare_table_payload,
    prepare_modify_table_payload,
    prepare_column_payload,
    prepare_modify_column_payload,
)


class TestPrepareColumnFields:
    """Tests pour prepare_column_fields."""
    
    def test_simple_column(self):
        """Test colonne simple sans options."""
        col = {"id": "name", "type": "Text", "label": "Nom"}
        fields = prepare_column_fields(col)
        
        assert "id" not in fields  # id doit être exclu
        assert fields["type"] == "Text"
        assert fields["label"] == "Nom"
    
    def test_widget_options_as_dict(self):
        """Test sérialisation widgetOptions dict → string."""
        col = {
            "id": "status",
            "type": "Choice",
            "widgetOptions": {"choices": ["A", "B", "C"]}
        }
        fields = prepare_column_fields(col)
        
        # widgetOptions doit être une string JSON
        assert isinstance(fields["widgetOptions"], str)
        parsed = json.loads(fields["widgetOptions"])
        assert parsed["choices"] == ["A", "B", "C"]
    
    def test_widget_options_as_string(self):
        """Test widgetOptions déjà en string."""
        col = {
            "id": "status",
            "type": "Choice",
            "widgetOptions": '{"choices": ["X", "Y"]}'
        }
        fields = prepare_column_fields(col)
        
        assert fields["widgetOptions"] == '{"choices": ["X", "Y"]}'
    
    def test_widget_options_none(self):
        """Test widgetOptions None ignoré."""
        col = {"id": "name", "type": "Text", "widgetOptions": None}
        fields = prepare_column_fields(col)
        
        assert "widgetOptions" not in fields


class TestPrepareTablePayload:
    """Tests pour prepare_table_payload."""
    
    def test_empty_columns(self):
        """Test création table sans colonnes."""
        payload = prepare_table_payload("MyTable", None)
        
        assert payload == {
            "tables": [{
                "id": "MyTable",
                "columns": []
            }]
        }
    
    def test_with_columns(self):
        """Test création table avec colonnes."""
        columns = [
            {"id": "name", "type": "Text", "label": "Nom"},
            {"id": "age", "type": "Int"}
        ]
        payload = prepare_table_payload("Users", columns)
        
        assert len(payload["tables"]) == 1
        table = payload["tables"][0]
        assert table["id"] == "Users"
        assert len(table["columns"]) == 2
        
        # Vérifier la structure des colonnes
        col1 = table["columns"][0]
        assert col1["id"] == "name"
        assert "id" not in col1["fields"]
        assert col1["fields"]["type"] == "Text"
        assert col1["fields"]["label"] == "Nom"
    
    def test_with_widget_options(self):
        """Test création table avec widgetOptions."""
        columns = [
            {
                "id": "status",
                "type": "Choice",
                "widgetOptions": {"choices": ["Active", "Inactive"]}
            }
        ]
        payload = prepare_table_payload("Items", columns)
        
        col_fields = payload["tables"][0]["columns"][0]["fields"]
        assert isinstance(col_fields["widgetOptions"], str)
        parsed = json.loads(col_fields["widgetOptions"])
        assert parsed["choices"] == ["Active", "Inactive"]


class TestPrepareModifyTablePayload:
    """Tests pour prepare_modify_table_payload."""
    
    def test_rename_table(self):
        """Test renommage de table."""
        payload = prepare_modify_table_payload("OldName", "NewName")
        
        assert payload == {
            "tables": [{
                "id": "OldName",
                "fields": {
                    "tableId": "NewName"
                }
            }]
        }
    
    def test_no_changes(self):
        """Test sans modifications."""
        payload = prepare_modify_table_payload("Table1", None)
        
        assert payload["tables"][0]["fields"] == {}


class TestPrepareColumnPayload:
    """Tests pour prepare_column_payload."""
    
    def test_simple_column(self):
        """Test colonne simple."""
        payload = prepare_column_payload(
            column_id="name",
            column_type="Text",
            label="Nom"
        )
        
        assert len(payload["columns"]) == 1
        col = payload["columns"][0]
        assert col["id"] == "name"
        assert col["fields"]["type"] == "Text"
        assert col["fields"]["label"] == "Nom"
        assert col["fields"]["untieColIdFromLabel"] is True
    
    def test_formula_column(self):
        """Test colonne calculée."""
        payload = prepare_column_payload(
            column_id="full_name",
            column_type="Text",
            formula="$first + ' ' + $last"
        )
        
        fields = payload["columns"][0]["fields"]
        assert fields["formula"] == "$first + ' ' + $last"
        assert fields["isFormula"] is True
    
    def test_choice_with_choices(self):
        """Test colonne Choice avec choix."""
        payload = prepare_column_payload(
            column_id="status",
            column_type="Choice",
            choices=["A", "B", "C"]
        )
        
        fields = payload["columns"][0]["fields"]
        assert "widgetOptions" in fields
        opts = json.loads(fields["widgetOptions"])
        assert opts["choices"] == ["A", "B", "C"]
    
    def test_reference_column(self):
        """Test colonne référence."""
        payload = prepare_column_payload(
            column_id="owner",
            column_type="Ref:Users",
            label="Propriétaire",
            visible_col=5
        )
        
        fields = payload["columns"][0]["fields"]
        assert fields["type"] == "Ref:Users"
        assert fields["label"] == "Propriétaire"
        assert fields["visibleCol"] == 5


class TestValidateColumnType:
    """Tests pour validate_column_type."""
    
    def test_valid_simple_types(self):
        """Test types simples valides."""
        for col_type in ["Text", "Numeric", "Int", "Bool", "Date", "DateTime"]:
            grist_type, opts, warnings = validate_column_type(col_type)
            assert grist_type == col_type
            assert len(warnings) == 0
    
    def test_choice_without_choices(self):
        """Test Choice sans choices génère un warning."""
        grist_type, opts, warnings = validate_column_type("Choice")
        
        assert grist_type == "Choice"
        assert len(warnings) == 1
        assert "choices" in warnings[0].lower()
    
    def test_invalid_type(self):
        """Test type invalide lève une exception."""
        with pytest.raises(ValueError) as excinfo:
            validate_column_type("InvalidType")
        
        assert "invalide" in str(excinfo.value).lower() or "inconnu" in str(excinfo.value).lower()
    
    def test_ref_already_formatted(self):
        """Test Ref:Table déjà formaté."""
        grist_type, opts, warnings = validate_column_type("Ref:Users")
        
        assert grist_type == "Ref:Users"


class TestParseSchemaDict:
    """Tests pour parse_schema_dict."""
    
    def test_simple_schema(self):
        """Test parsing schéma simple."""
        schema_dict = {
            "tables": {
                "Users": {
                    "columns": {
                        "name": {"type": "Text", "label": "Nom"},
                        "age": {"type": "Int"}
                    }
                }
            }
        }
        
        schema = parse_schema_dict(schema_dict)
        
        assert len(schema.tables) == 1
        assert schema.tables[0].id == "Users"
        assert len(schema.tables[0].columns) == 2
    
    def test_schema_with_references(self):
        """Test parsing schéma avec références."""
        schema_dict = {
            "tables": {
                "Tasks": {
                    "columns": {
                        "title": {"type": "Text"},
                        "owner": {
                            "type": "Ref",
                            "target": "Users",
                            "visible": "name"
                        }
                    }
                }
            }
        }
        
        schema = parse_schema_dict(schema_dict)
        
        owner_col = schema.tables[0].columns[1]
        assert owner_col.type == "Ref"
        assert owner_col.target_table == "Users"
        assert owner_col.visible_column == "name"
    
    def test_schema_with_data(self):
        """Test parsing schéma avec données."""
        schema_dict = {
            "tables": {
                "Items": {
                    "columns": {
                        "name": {"type": "Text"}
                    }
                }
            },
            "data": {
                "Items": [
                    {"name": "Item 1"},
                    {"name": "Item 2"}
                ]
            }
        }
        
        schema = parse_schema_dict(schema_dict)
        
        assert schema.data is not None
        assert len(schema.data["Items"]) == 2
    
    def test_simplified_column_format(self):
        """Test format simplifié {"col": "Type"}."""
        schema_dict = {
            "tables": {
                "Simple": {
                    "columns": {
                        "name": "Text",
                        "count": "Int"
                    }
                }
            }
        }
        
        schema = parse_schema_dict(schema_dict)
        
        assert schema.tables[0].columns[0].type == "Text"
        assert schema.tables[0].columns[1].type == "Int"


class TestSchemaDefinition:
    """Tests pour SchemaDefinition."""
    
    def test_get_table(self):
        """Test récupération d'une table par ID."""
        schema = SchemaDefinition(tables=[
            TableDefinition(id="Table1"),
            TableDefinition(id="Table2")
        ])
        
        assert schema.get_table("Table1") is not None
        assert schema.get_table("Table1").id == "Table1"
        assert schema.get_table("NonExistent") is None
    
    def test_validate_missing_target(self):
        """Test validation détecte table cible manquante."""
        schema = SchemaDefinition(tables=[
            TableDefinition(
                id="Tasks",
                columns=[
                    ColumnDefinition(
                        id="owner",
                        type="Ref",
                        target_table="NonExistentTable"
                    )
                ]
            )
        ])
        
        errors = schema.validate()
        
        assert len(errors) == 1
        assert "NonExistentTable" in errors[0]


class TestTableDefinition:
    """Tests pour TableDefinition."""
    
    def test_get_simple_columns(self):
        """Test filtrage colonnes simples."""
        table = TableDefinition(
            id="Test",
            columns=[
                ColumnDefinition(id="name", type="Text"),
                ColumnDefinition(id="owner", type="Ref", target_table="Users"),
                ColumnDefinition(id="tags", type="RefList", target_table="Tags"),
                ColumnDefinition(id="count", type="Int"),
            ]
        )
        
        simple = table.get_simple_columns()
        
        assert len(simple) == 2
        assert simple[0].id == "name"
        assert simple[1].id == "count"
    
    def test_get_reference_columns(self):
        """Test filtrage colonnes référence."""
        table = TableDefinition(
            id="Test",
            columns=[
                ColumnDefinition(id="name", type="Text"),
                ColumnDefinition(id="owner", type="Ref", target_table="Users"),
                ColumnDefinition(id="tags", type="RefList", target_table="Tags"),
            ]
        )
        
        refs = table.get_reference_columns()
        
        assert len(refs) == 2
        assert refs[0].id == "owner"
        assert refs[1].id == "tags"


class TestColumnDefinition:
    """Tests pour ColumnDefinition."""
    
    def test_to_grist_fields_simple(self):
        """Test conversion simple vers Grist."""
        col = ColumnDefinition(
            id="name",
            type="Text",
            label="Nom"
        )
        
        fields = col.to_grist_fields()
        
        assert fields["type"] == "Text"
        assert fields["label"] == "Nom"
        assert fields["untieColIdFromLabel"] is True
    
    def test_to_grist_fields_reference(self):
        """Test conversion référence vers Grist."""
        col = ColumnDefinition(
            id="owner",
            type="Ref",
            target_table="Users",
            label="Propriétaire"
        )
        
        fields = col.to_grist_fields()
        
        assert fields["type"] == "Ref:Users"
        assert fields["label"] == "Propriétaire"
    
    def test_to_grist_fields_formula(self):
        """Test conversion formule vers Grist."""
        col = ColumnDefinition(
            id="full_name",
            type="Text",
            formula="$first + ' ' + $last"
        )
        
        fields = col.to_grist_fields()
        
        assert fields["formula"] == "$first + ' ' + $last"
        assert fields["isFormula"] is True
    
    def test_to_grist_fields_choices(self):
        """Test conversion choix vers Grist."""
        col = ColumnDefinition(
            id="status",
            type="Choice",
            choices=["Active", "Inactive"]
        )
        
        fields = col.to_grist_fields()
        
        assert "widgetOptions" in fields
        opts = json.loads(fields["widgetOptions"])
        assert opts["choices"] == ["Active", "Inactive"]


# Tests d'intégration (nécessitent un mock ou une instance Grist)
class TestIntegration:
    """Tests d'intégration (à exécuter avec un environnement Grist)."""
    
    @pytest.mark.skip(reason="Nécessite une instance Grist")
    async def test_create_table_with_choices(self):
        """Test création table avec colonnes Choice."""
        pass
    
    @pytest.mark.skip(reason="Nécessite une instance Grist")
    async def test_create_schema_full(self):
        """Test création schéma complet."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
