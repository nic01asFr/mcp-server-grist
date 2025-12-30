"""
Utilitaires partagés pour Grist MCP Server.
"""
import json
from typing import Any, Dict, List, Optional, Tuple


def prepare_column_fields(col: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prépare les fields d'une colonne pour l'API Grist.
    
    Gère notamment:
    - Exclusion de l'id des fields
    - Sérialisation des widgetOptions en JSON string
    - Normalisation des types
    """
    fields = {}
    
    for key, value in col.items():
        if key == "id":
            continue
        
        if key == "widgetOptions":
            if isinstance(value, dict):
                fields[key] = json.dumps(value)
            elif isinstance(value, str):
                fields[key] = value
            # Si None ou autre, on ignore
        else:
            fields[key] = value
    
    return fields


def prepare_table_payload(
    table_id: str,
    columns: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Prépare le payload pour créer/modifier une table.
    
    Format API Grist attendu:
    {
        "tables": [{
            "id": "TableId",
            "columns": [{
                "id": "col_id",
                "fields": { ... }
            }]
        }]
    }
    """
    prepared_columns = []
    
    for col in (columns or []):
        col_id = col.get("id")
        if not col_id:
            continue
        
        prepared_columns.append({
            "id": col_id,
            "fields": prepare_column_fields(col)
        })
    
    return {
        "tables": [{
            "id": table_id,
            "columns": prepared_columns
        }]
    }


def prepare_modify_table_payload(
    table_id: str,
    new_table_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prépare le payload pour modifier une table.
    
    Format API Grist attendu:
    {
        "tables": [{
            "id": "CurrentTableId",
            "fields": {
                "tableId": "NewTableId"
            }
        }]
    }
    """
    fields = {}
    if new_table_id:
        fields["tableId"] = new_table_id
    
    return {
        "tables": [{
            "id": table_id,
            "fields": fields
        }]
    }


def prepare_column_payload(
    column_id: str,
    column_type: str = "Text",
    label: Optional[str] = None,
    formula: Optional[str] = None,
    widget_options: Optional[Dict[str, Any]] = None,
    visible_col: Optional[int] = None,
    untie_col_id_from_label: bool = True,
    description: Optional[str] = None,
    choices: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Prépare le payload pour créer une colonne.
    """
    fields = {
        "type": column_type,
        "untieColIdFromLabel": untie_col_id_from_label
    }
    
    if label:
        fields["label"] = label
    
    if formula:
        fields["formula"] = formula
        fields["isFormula"] = True
    
    if description:
        fields["description"] = description
    
    if visible_col is not None:
        fields["visibleCol"] = visible_col
    
    # Gestion des widget options
    opts = widget_options.copy() if widget_options else {}
    if choices and column_type in ("Choice", "ChoiceList"):
        opts["choices"] = choices
    
    if opts:
        fields["widgetOptions"] = json.dumps(opts)
    
    return {
        "columns": [{
            "id": column_id,
            "fields": fields
        }]
    }


def prepare_modify_column_payload(
    column_id: str,
    new_column_id: Optional[str] = None,
    column_type: Optional[str] = None,
    label: Optional[str] = None,
    formula: Optional[str] = None,
    widget_options: Optional[Dict[str, Any]] = None,
    visible_col: Optional[int] = None,
    untie_col_id_from_label: Optional[bool] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prépare le payload pour modifier une colonne.
    """
    fields = {}
    
    if new_column_id:
        fields["colId"] = new_column_id
    
    if column_type:
        fields["type"] = column_type
    
    if label is not None:
        fields["label"] = label
    
    if formula is not None:
        fields["formula"] = formula
        fields["isFormula"] = bool(formula)
    
    if description is not None:
        fields["description"] = description
    
    if visible_col is not None:
        fields["visibleCol"] = visible_col
    
    if untie_col_id_from_label is not None:
        fields["untieColIdFromLabel"] = untie_col_id_from_label
    
    if widget_options is not None:
        fields["widgetOptions"] = json.dumps(widget_options)
    
    return {
        "columns": [{
            "id": column_id,
            "fields": fields
        }]
    }


async def resolve_visible_col(
    client,
    doc_id: str,
    table_id: str,
    column_name: str
) -> Tuple[Optional[int], Optional[str]]:
    """
    Résout le nom d'une colonne en son colRef numérique.
    
    Returns:
        Tuple (colRef, error_message)
    """
    try:
        # Utiliser la méthode list_columns du client
        columns_list = await client.list_columns(doc_id, table_id)
        columns = [{"id": c.id, "fields": c.fields} for c in columns_list]
        
        for col in columns:
            col_id = col.get("id")
            col_fields = col.get("fields", {})
            col_label = col_fields.get("label", col_id)
            col_ref = col_fields.get("colRef")
            
            # Chercher par ID ou par label
            if col_id == column_name or col_label == column_name:
                return col_ref, None
        
        # Colonne non trouvée
        available = [c.get("id") for c in columns]
        return None, f"Colonne '{column_name}' non trouvée. Colonnes disponibles: {available}"
        
    except Exception as e:
        return None, f"Erreur lors de la résolution: {str(e)}"


async def check_table_exists(
    client,
    doc_id: str,
    table_id: str
) -> Tuple[bool, List[str]]:
    """
    Vérifie si une table existe dans un document.
    
    Returns:
        Tuple (exists, list_of_tables)
    """
    try:
        # Utiliser la méthode list_tables du client
        tables_list = await client.list_tables(doc_id)
        table_ids = [t.id for t in tables_list]
        return table_id in table_ids, table_ids
    except Exception:
        return False, []


def build_error_response(
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Construit une réponse d'erreur standardisée."""
    response = {
        "success": False,
        "message": message
    }
    if details:
        response["details"] = details
    return response


def build_success_response(
    message: str,
    **kwargs
) -> Dict[str, Any]:
    """Construit une réponse de succès standardisée."""
    response = {
        "success": True,
        "message": message
    }
    response.update(kwargs)
    return response
