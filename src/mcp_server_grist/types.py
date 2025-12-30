"""
Types et validations pour Grist MCP Server.
"""
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ColumnType(str, Enum):
    """Types de colonnes Grist supportés."""
    TEXT = "Text"
    NUMERIC = "Numeric"
    INT = "Int"
    BOOL = "Bool"
    DATE = "Date"
    DATETIME = "DateTime"
    CHOICE = "Choice"
    CHOICE_LIST = "ChoiceList"
    REF = "Ref"
    REF_LIST = "RefList"
    ATTACHMENTS = "Attachments"


# Mapping des types avec leurs configurations
GRIST_COLUMN_TYPES: Dict[str, Dict[str, Any]] = {
    # Types simples
    "Text": {
        "grist_type": "Text",
        "description": "Texte libre"
    },
    "Numeric": {
        "grist_type": "Numeric",
        "description": "Nombre décimal",
        "default_options": {"decimals": 2}
    },
    "Int": {
        "grist_type": "Int",
        "description": "Nombre entier"
    },
    "Bool": {
        "grist_type": "Bool",
        "description": "Booléen (vrai/faux)"
    },
    "Date": {
        "grist_type": "Date",
        "description": "Date (timestamp Unix)"
    },
    "DateTime": {
        "grist_type": "DateTime",
        "description": "Date et heure (timestamp Unix)"
    },
    
    # Types avec options obligatoires
    "Choice": {
        "grist_type": "Choice",
        "description": "Choix unique parmi une liste",
        "requires": ["choices"],
        "options_key": "choices"
    },
    "ChoiceList": {
        "grist_type": "ChoiceList",
        "description": "Choix multiples parmi une liste",
        "requires": ["choices"],
        "options_key": "choices"
    },
    
    # Types référence
    "Ref": {
        "grist_type": "Ref:{target}",
        "description": "Référence vers une autre table",
        "requires": ["target_table"]
    },
    "RefList": {
        "grist_type": "RefList:{target}",
        "description": "Liste de références vers une autre table",
        "requires": ["target_table"]
    },
    
    # Types spéciaux
    "Attachments": {
        "grist_type": "Attachments",
        "description": "Pièces jointes"
    },
}


@dataclass
class ColumnDefinition:
    """Définition d'une colonne Grist."""
    id: str
    type: str = "Text"
    label: Optional[str] = None
    formula: Optional[str] = None
    widget_options: Optional[Dict[str, Any]] = None
    visible_col: Optional[int] = None
    description: Optional[str] = None
    
    # Pour les références
    target_table: Optional[str] = None
    visible_column: Optional[str] = None
    reverse_column: Optional[str] = None
    
    # Pour les choix
    choices: Optional[List[str]] = None
    
    def to_grist_fields(self) -> Dict[str, Any]:
        """Convertit en format API Grist."""
        fields = {}
        
        # Type de base
        grist_type = self.type
        if self.type in ("Ref", "RefList") and self.target_table:
            grist_type = f"{self.type}:{self.target_table}"
        fields["type"] = grist_type
        
        # Label
        if self.label:
            fields["label"] = self.label
        
        # Formule
        if self.formula:
            fields["formula"] = self.formula
            fields["isFormula"] = True
        
        # Description
        if self.description:
            fields["description"] = self.description
        
        # Widget options (doit être une string JSON)
        widget_opts = self.widget_options or {}
        if self.choices:
            widget_opts["choices"] = self.choices
        if widget_opts:
            fields["widgetOptions"] = json.dumps(widget_opts)
        
        # Visible col pour les références
        if self.visible_col is not None:
            fields["visibleCol"] = self.visible_col
        
        # Toujours dissocier l'ID du label
        fields["untieColIdFromLabel"] = True
        
        return fields


@dataclass
class TableDefinition:
    """Définition d'une table Grist."""
    id: str
    columns: List[ColumnDefinition] = field(default_factory=list)
    
    def get_simple_columns(self) -> List[ColumnDefinition]:
        """Retourne les colonnes simples (non-référence)."""
        return [c for c in self.columns if c.type not in ("Ref", "RefList")]
    
    def get_reference_columns(self) -> List[ColumnDefinition]:
        """Retourne les colonnes de référence."""
        return [c for c in self.columns if c.type in ("Ref", "RefList")]


@dataclass
class SchemaDefinition:
    """Définition complète d'un schéma Grist."""
    tables: List[TableDefinition] = field(default_factory=list)
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None
    
    def get_table(self, table_id: str) -> Optional[TableDefinition]:
        """Récupère une table par son ID."""
        for table in self.tables:
            if table.id == table_id:
                return table
        return None
    
    def validate(self) -> List[str]:
        """Valide le schéma et retourne les erreurs."""
        errors = []
        table_ids = {t.id for t in self.tables}
        
        for table in self.tables:
            for col in table.get_reference_columns():
                if col.target_table and col.target_table not in table_ids:
                    errors.append(
                        f"Table '{table.id}', colonne '{col.id}': "
                        f"table cible '{col.target_table}' inexistante"
                    )
        
        return errors


def validate_column_type(
    column_type: str,
    **kwargs
) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Valide et normalise un type de colonne.
    
    Returns:
        Tuple (grist_type, default_options, warnings)
    """
    warnings = []
    
    # Si déjà formaté comme Ref:Table
    if ":" in column_type:
        base_type, target = column_type.split(":", 1)
        if base_type in ("Ref", "RefList"):
            return column_type, {}, warnings
    
    # Vérifier le type
    type_info = GRIST_COLUMN_TYPES.get(column_type)
    if not type_info:
        valid_types = list(GRIST_COLUMN_TYPES.keys())
        raise ValueError(
            f"Type de colonne inconnu: '{column_type}'. "
            f"Types valides: {valid_types}"
        )
    
    # Vérifier les paramètres requis
    for req in type_info.get("requires", []):
        if req not in kwargs or kwargs[req] is None:
            if req == "choices":
                warnings.append(
                    f"Type '{column_type}' sans 'choices' défini - "
                    "la liste sera vide"
                )
            else:
                raise ValueError(
                    f"Type '{column_type}' requiert le paramètre '{req}'"
                )
    
    # Construire le type Grist
    grist_type = type_info["grist_type"]
    if "{target}" in grist_type:
        target = kwargs.get("target_table", "")
        grist_type = grist_type.format(target=target)
    
    return grist_type, type_info.get("default_options", {}), warnings


def prepare_widget_options(
    column_type: str,
    widget_options: Optional[Dict[str, Any]] = None,
    choices: Optional[List[str]] = None
) -> Optional[str]:
    """
    Prépare les widget options pour l'API Grist.
    Retourne une string JSON ou None.
    """
    opts = widget_options.copy() if widget_options else {}
    
    # Ajouter les choix pour Choice/ChoiceList
    if column_type in ("Choice", "ChoiceList") and choices:
        opts["choices"] = choices
    
    # Ajouter les options par défaut du type
    type_info = GRIST_COLUMN_TYPES.get(column_type, {})
    default_opts = type_info.get("default_options", {})
    for key, value in default_opts.items():
        if key not in opts:
            opts[key] = value
    
    if opts:
        return json.dumps(opts)
    return None


def parse_schema_dict(schema_dict: Dict[str, Any]) -> SchemaDefinition:
    """
    Parse un dictionnaire de schéma en SchemaDefinition.
    
    Format attendu:
    {
        "tables": {
            "TableName": {
                "columns": {
                    "col_id": {
                        "type": "Text",
                        "label": "Label",
                        ...
                    }
                }
            }
        },
        "data": {
            "TableName": [
                {"col1": "value1", ...}
            ]
        }
    }
    """
    tables = []
    
    tables_dict = schema_dict.get("tables", {})
    for table_id, table_def in tables_dict.items():
        columns = []
        columns_dict = table_def.get("columns", {})
        
        for col_id, col_def in columns_dict.items():
            if isinstance(col_def, str):
                # Format simplifié: {"col_id": "Type"}
                col_def = {"type": col_def}
            
            column = ColumnDefinition(
                id=col_id,
                type=col_def.get("type", "Text"),
                label=col_def.get("label"),
                formula=col_def.get("formula"),
                widget_options=col_def.get("widgetOptions"),
                description=col_def.get("description"),
                target_table=col_def.get("target"),
                visible_column=col_def.get("visible"),
                reverse_column=col_def.get("reverse"),
                choices=col_def.get("choices"),
            )
            columns.append(column)
        
        tables.append(TableDefinition(id=table_id, columns=columns))
    
    return SchemaDefinition(
        tables=tables,
        data=schema_dict.get("data")
    )
