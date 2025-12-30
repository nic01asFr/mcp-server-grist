"""
Outils de gestion de schéma Grist.

Nouveaux outils v0.2.0:
- create_reference_column: Création de références avec résolution automatique
- validate_schema: Validation d'un schéma sans création
- create_schema: Création complète d'un schéma avec relations
- export_schema: Export du schéma d'un document existant
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from fastmcp import Context

from ..client import get_client
from ..types import (
    SchemaDefinition,
    TableDefinition,
    ColumnDefinition,
    parse_schema_dict,
)
from .utils import (
    resolve_visible_col,
    check_table_exists,
    prepare_column_payload,
    prepare_table_payload,
    build_success_response,
    build_error_response,
)

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")


@dataclass
class SchemaCreationReport:
    """Rapport de création de schéma."""
    tables_created: List[Dict[str, Any]] = field(default_factory=list)
    columns_created: List[Dict[str, Any]] = field(default_factory=list)
    references_created: List[Dict[str, Any]] = field(default_factory=list)
    records_inserted: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tables_created": self.tables_created,
            "columns_created": self.columns_created,
            "references_created": self.references_created,
            "records_inserted": self.records_inserted,
            "warnings": self.warnings,
            "errors": self.errors,
        }


async def create_reference_column(
    doc_id: str,
    table_id: str,
    column_id: str,
    target_table: str,
    visible_column: str,
    is_list: bool = False,
    label: Optional[str] = None,
    reverse_column: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Crée une colonne de référence avec résolution automatique de visibleCol.
    
    Cette fonction:
    1. Vérifie que la table cible existe
    2. Résout le nom de colonne visible en colRef numérique
    3. Crée la colonne de référence
    4. Optionnellement crée la relation inverse
    
    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table source
        column_id: ID de la nouvelle colonne de référence
        target_table: ID de la table cible
        visible_column: Nom de la colonne à afficher (sera résolu en colRef)
        is_list: Si True, crée RefList au lieu de Ref (défaut: False)
        label: Libellé d'affichage (optionnel)
        reverse_column: Si fourni, crée une RefList inverse dans target_table
    
    Returns:
        Dict avec statut, détails et éventuels warnings
    """
    try:
        client = get_client(ctx)
        if not client:
            return build_error_response("Client Grist non configuré")
        warnings = []
        
        # PHASE 1: Validation - Vérifier que target_table existe
        exists, available_tables = await check_table_exists(client, doc_id, target_table)
        if not exists:
            return build_error_response(
                f"Table cible '{target_table}' inexistante",
                details={"available_tables": available_tables}
            )
        
        # PHASE 2: Résolution - Trouver le colRef de visible_column
        col_ref, error = await resolve_visible_col(
            client, doc_id, target_table, visible_column
        )
        if error:
            return build_error_response(error)
        
        # PHASE 3: Création de la colonne
        ref_type = f"RefList:{target_table}" if is_list else f"Ref:{target_table}"
        
        payload = prepare_column_payload(
            column_id=column_id,
            column_type=ref_type,
            label=label,
            visible_col=col_ref
        )
        
        # Utiliser la méthode create_columns du client
        columns_created = await client.create_columns(doc_id, table_id, payload)
        
        # PHASE 4: Création de la relation inverse (optionnel)
        reverse_result = None
        if reverse_column:
            try:
                # Résoudre le colRef pour la table source
                source_col_ref, _ = await resolve_visible_col(
                    client, doc_id, table_id, column_id
                )
                # En cas d'échec, utiliser "id" par défaut
                if source_col_ref is None:
                    source_col_ref, _ = await resolve_visible_col(
                        client, doc_id, table_id, "id"
                    )
                
                reverse_payload = prepare_column_payload(
                    column_id=reverse_column,
                    column_type=f"RefList:{table_id}",
                    label=f"{table_id}s",
                    visible_col=source_col_ref
                )
                
                reverse_columns = await client.create_columns(doc_id, target_table, reverse_payload)
                reverse_result = reverse_columns[0] if reverse_columns else {"id": reverse_column}
                
            except Exception as e:
                warnings.append(
                    f"Échec création relation inverse '{reverse_column}': {str(e)}"
                )
        
        # PHASE 5: Réponse
        result = build_success_response(
            f"Colonne référence '{column_id}' créée avec succès",
            column=columns_created[0] if columns_created else {"id": column_id},
            reference={
                "from_table": table_id,
                "to_table": target_table,
                "type": ref_type,
                "visible_col": visible_column,
                "visible_col_ref": col_ref
            }
        )
        
        if reverse_result:
            result["reverse_column"] = reverse_result
        
        if warnings:
            result["warnings"] = warnings
        
        return result
        
    except Exception as e:
        return build_error_response(
            f"Erreur lors de la création de la colonne référence: {str(e)}"
        )


async def validate_schema(
    doc_id: str,
    schema: Dict[str, Any],
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Valide un schéma sans le créer.
    
    Vérifie:
    - Syntaxe du schéma
    - Existence des tables cibles pour les références
    - Cohérence des types de colonnes
    - Colonnes visibles existantes pour les références
    
    Args:
        doc_id: L'ID du document (pour vérifier les tables existantes)
        schema: Schéma à valider (format dict)
    
    Returns:
        Dict avec statut de validation, erreurs et warnings
    """
    try:
        errors = []
        warnings = []
        
        # Parser le schéma
        try:
            schema_def = parse_schema_dict(schema)
        except Exception as e:
            return build_error_response(
                f"Erreur de parsing du schéma: {str(e)}"
            )
        
        # Récupérer les tables existantes
        client = get_client(ctx)
        if not client:
            return build_error_response("Client Grist non configuré")
        
        # Utiliser list_tables du client
        tables_list = await client.list_tables(doc_id)
        existing_tables = {t.id for t in tables_list}
        
        # Tables définies dans le schéma
        schema_tables = {t.id for t in schema_def.tables}
        all_tables = existing_tables | schema_tables
        
        # Valider chaque table
        for table in schema_def.tables:
            # Vérifier si la table existe déjà
            if table.id in existing_tables:
                warnings.append(f"Table '{table.id}' existe déjà dans le document")
            
            # Valider les colonnes
            for col in table.columns:
                # Vérifier les références
                if col.type in ("Ref", "RefList"):
                    if not col.target_table:
                        errors.append(
                            f"Table '{table.id}', colonne '{col.id}': "
                            f"target_table requis pour type {col.type}"
                        )
                    elif col.target_table not in all_tables:
                        errors.append(
                            f"Table '{table.id}', colonne '{col.id}': "
                            f"table cible '{col.target_table}' inexistante"
                        )
                
                # Vérifier les choix
                if col.type in ("Choice", "ChoiceList") and not col.choices:
                    warnings.append(
                        f"Table '{table.id}', colonne '{col.id}': "
                        f"type {col.type} sans 'choices' défini"
                    )
        
        # Résultat
        is_valid = len(errors) == 0
        
        return {
            "success": True,
            "valid": is_valid,
            "message": "Schéma valide" if is_valid else f"{len(errors)} erreur(s) trouvée(s)",
            "schema_summary": {
                "tables_count": len(schema_def.tables),
                "tables": [
                    {
                        "id": t.id,
                        "columns_count": len(t.columns),
                        "references_count": len(t.get_reference_columns())
                    }
                    for t in schema_def.tables
                ]
            },
            "errors": errors,
            "warnings": warnings
        }
        
    except Exception as e:
        return build_error_response(
            f"Erreur lors de la validation du schéma: {str(e)}"
        )


async def create_schema(
    doc_id: str,
    schema: Dict[str, Any],
    skip_existing: bool = True,
    insert_data: bool = True,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Crée un schéma complet avec tables, colonnes et relations.
    
    Algorithme:
    1. Validation du schéma
    2. Création des tables avec colonnes simples
    3. Résolution des visibleCol pour les références
    4. Création des colonnes de référence
    5. Insertion des données (optionnel)
    
    Args:
        doc_id: L'ID du document
        schema: Schéma complet à créer
        skip_existing: Si True, ignore les tables existantes (défaut: True)
        insert_data: Si True, insère les données définies (défaut: True)
    
    Returns:
        Dict avec rapport détaillé de création
    """
    report = SchemaCreationReport()
    
    try:
        client = get_client(ctx)
        if not client:
            return build_error_response("Client Grist non configuré")
        
        # PHASE 1: Validation
        validation = await validate_schema(doc_id, schema, ctx)
        if not validation.get("valid", False):
            return build_error_response(
                "Schéma invalide",
                details={
                    "errors": validation.get("errors", []),
                    "warnings": validation.get("warnings", [])
                }
            )
        
        report.warnings.extend(validation.get("warnings", []))
        
        # Parser le schéma
        schema_def = parse_schema_dict(schema)
        
        # Récupérer les tables existantes
        tables_list = await client.list_tables(doc_id)
        existing_tables = {t.id for t in tables_list}
        
        # Mapping table_id schéma → table_id réel (au cas où Grist renomme)
        table_mapping = {}
        
        # PHASE 2: Création des tables avec colonnes simples
        for table in schema_def.tables:
            if table.id in existing_tables:
                if skip_existing:
                    report.warnings.append(f"Table '{table.id}' ignorée (existe déjà)")
                    table_mapping[table.id] = table.id
                    continue
                else:
                    report.errors.append(f"Table '{table.id}' existe déjà")
                    continue
            
            # Préparer les colonnes simples (non-référence)
            simple_columns = []
            for col in table.get_simple_columns():
                col_def = {
                    "id": col.id,
                    "type": col.type,
                }
                if col.label:
                    col_def["label"] = col.label
                if col.formula:
                    col_def["formula"] = col.formula
                    col_def["isFormula"] = True
                if col.choices:
                    col_def["widgetOptions"] = {"choices": col.choices}
                if col.description:
                    col_def["description"] = col.description
                
                simple_columns.append(col_def)
            
            # Créer la table
            try:
                payload = prepare_table_payload(table.id, simple_columns)
                tables_created = await client.create_tables(doc_id, payload)
                
                if tables_created:
                    actual_id = tables_created[0].get("id", table.id)
                    table_mapping[table.id] = actual_id
                    report.tables_created.append({
                        "id": actual_id,
                        "requested_id": table.id,
                        "columns_count": len(simple_columns)
                    })
                else:
                    table_mapping[table.id] = table.id
                    report.tables_created.append({
                        "id": table.id,
                        "columns_count": len(simple_columns)
                    })
                    
            except Exception as e:
                report.errors.append(f"Échec création table '{table.id}': {str(e)}")
                continue
        
        # PHASE 3: Cache des colRef pour les références
        col_ref_cache: Dict[str, Dict[str, int]] = {}
        
        async def get_col_ref(target_table: str, column_name: str) -> Optional[int]:
            """Récupère le colRef avec cache."""
            actual_table = table_mapping.get(target_table, target_table)
            
            if actual_table not in col_ref_cache:
                try:
                    columns_list = await client.list_columns(doc_id, actual_table)
                    col_ref_cache[actual_table] = {}
                    for col in columns_list:
                        col_id = col.id
                        col_fields = col.fields if hasattr(col, 'fields') else {}
                        col_label = col_fields.get("label", col_id)
                        col_ref = col_fields.get("colRef")
                        col_ref_cache[actual_table][col_id] = col_ref
                        col_ref_cache[actual_table][col_label] = col_ref
                except Exception:
                    pass
            
            return col_ref_cache.get(actual_table, {}).get(column_name)
        
        # PHASE 4: Création des colonnes de référence
        for table in schema_def.tables:
            actual_table_id = table_mapping.get(table.id, table.id)
            
            for col in table.get_reference_columns():
                try:
                    target_table = table_mapping.get(col.target_table, col.target_table)
                    ref_type = f"RefList:{target_table}" if col.type == "RefList" else f"Ref:{target_table}"
                    
                    # Résoudre visibleCol si spécifié
                    visible_col_ref = None
                    if col.visible_column:
                        visible_col_ref = await get_col_ref(col.target_table, col.visible_column)
                        if visible_col_ref is None:
                            report.warnings.append(
                                f"Colonne visible '{col.visible_column}' non résolue "
                                f"pour {table.id}.{col.id}"
                            )
                    
                    # Créer la colonne
                    payload = prepare_column_payload(
                        column_id=col.id,
                        column_type=ref_type,
                        label=col.label,
                        visible_col=visible_col_ref
                    )
                    
                    await client.create_columns(doc_id, actual_table_id, payload)
                    
                    report.references_created.append({
                        "table": actual_table_id,
                        "column": col.id,
                        "target": target_table,
                        "type": ref_type
                    })
                    
                    # Créer la relation inverse si demandée
                    if col.reverse_column:
                        try:
                            reverse_payload = prepare_column_payload(
                                column_id=col.reverse_column,
                                column_type=f"RefList:{actual_table_id}",
                                label=f"{table.id}s"
                            )
                            
                            await client.create_columns(doc_id, target_table, reverse_payload)
                            
                            report.references_created.append({
                                "table": target_table,
                                "column": col.reverse_column,
                                "target": actual_table_id,
                                "type": f"RefList:{actual_table_id}",
                                "is_reverse": True
                            })
                        except Exception as e:
                            report.warnings.append(
                                f"Échec relation inverse '{col.reverse_column}': {str(e)}"
                            )
                    
                except Exception as e:
                    report.errors.append(
                        f"Échec création référence {table.id}.{col.id}: {str(e)}"
                    )
        
        # PHASE 5: Insertion des données
        if insert_data and schema_def.data:
            for table_id, records in schema_def.data.items():
                actual_table_id = table_mapping.get(table_id, table_id)
                
                try:
                    if records:
                        record_ids = await client.add_records(doc_id, actual_table_id, records)
                        report.records_inserted.append({
                            "table": actual_table_id,
                            "count": len(record_ids)
                        })
                except Exception as e:
                    report.warnings.append(
                        f"Échec insertion données dans '{table_id}': {str(e)}"
                    )
        
        # Résultat final
        success = len(report.errors) == 0
        
        return {
            "success": success,
            "message": (
                f"Schéma créé avec succès: {len(report.tables_created)} tables, "
                f"{len(report.references_created)} références"
                if success else
                f"Schéma créé partiellement: {len(report.errors)} erreur(s)"
            ),
            "report": report.to_dict()
        }
        
    except Exception as e:
        report.errors.append(str(e))
        return {
            "success": False,
            "message": f"Erreur lors de la création du schéma: {str(e)}",
            "report": report.to_dict()
        }


async def export_schema(
    doc_id: str,
    format: str = "json",
    include_data: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Exporte le schéma d'un document existant.
    
    Args:
        doc_id: L'ID du document
        format: Format d'export ("json", "yaml", "mermaid")
        include_data: Si True, inclut les données (limité à 100 enregistrements/table)
    
    Returns:
        Dict avec le schéma exporté dans le format demandé
    """
    try:
        client = get_client(ctx)
        if not client:
            return build_error_response("Client Grist non configuré")
        
        # Récupérer les tables avec list_tables
        tables_list = await client.list_tables(doc_id)
        
        schema = {"tables": {}}
        data = {} if include_data else None
        
        for table in tables_list:
            table_id = table.id
            if not table_id or table_id.startswith("_"):
                continue  # Ignorer les tables système
            
            # Récupérer les colonnes avec list_columns
            columns_list = await client.list_columns(doc_id, table_id)
            
            table_def = {"columns": {}}
            
            for col in columns_list:
                col_id = col.id
                if not col_id or col_id == "id":
                    continue
                
                fields = col.fields if hasattr(col, 'fields') else {}
                col_type = fields.get("type", "Text")
                
                col_def = {"type": col_type}
                
                # Label
                label = fields.get("label")
                if label and label != col_id:
                    col_def["label"] = label
                
                # Formule
                formula = fields.get("formula")
                if formula:
                    col_def["formula"] = formula
                
                # Description
                description = fields.get("description")
                if description:
                    col_def["description"] = description
                
                # Widget options
                widget_opts = fields.get("widgetOptions")
                if widget_opts:
                    if isinstance(widget_opts, str):
                        try:
                            widget_opts = json.loads(widget_opts)
                        except Exception:
                            pass
                    if isinstance(widget_opts, dict):
                        if "choices" in widget_opts:
                            col_def["choices"] = widget_opts["choices"]
                
                # Références
                if col_type.startswith("Ref:") or col_type.startswith("RefList:"):
                    parts = col_type.split(":", 1)
                    col_def["type"] = parts[0]
                    col_def["target"] = parts[1] if len(parts) > 1 else ""
                
                table_def["columns"][col_id] = col_def
            
            schema["tables"][table_id] = table_def
            
            # Récupérer les données si demandé
            if include_data:
                try:
                    records_list = await client.list_records(doc_id, table_id, limit=100)
                    data[table_id] = [r.fields if hasattr(r, 'fields') else {} for r in records_list]
                except Exception:
                    pass
        
        if include_data:
            schema["data"] = data
        
        # Formatage selon le format demandé
        if format == "json":
            output = schema
        elif format == "yaml":
            try:
                import yaml
                output = yaml.dump(schema, default_flow_style=False, allow_unicode=True)
            except ImportError:
                output = schema
                format = "json"
        elif format == "mermaid":
            output = _generate_mermaid(schema)
        else:
            output = schema
            format = "json"
        
        return build_success_response(
            f"Schéma exporté avec succès ({len(schema['tables'])} tables)",
            format=format,
            schema=output
        )
        
    except Exception as e:
        return build_error_response(
            f"Erreur lors de l'export du schéma: {str(e)}"
        )


def _generate_mermaid(schema: Dict[str, Any]) -> str:
    """Génère un diagramme Mermaid ER à partir d'un schéma."""
    lines = ["erDiagram"]
    
    tables = schema.get("tables", {})
    
    for table_id, table_def in tables.items():
        columns = table_def.get("columns", {})
        
        # Définition de la table
        lines.append(f"    {table_id} {{")
        
        for col_id, col_def in columns.items():
            col_type = col_def.get("type", "Text")
            
            # Simplifier le type pour Mermaid
            if col_type.startswith("Ref"):
                mermaid_type = "int"
            elif col_type in ("Numeric", "Int"):
                mermaid_type = "int"
            elif col_type == "Bool":
                mermaid_type = "bool"
            elif col_type in ("Date", "DateTime"):
                mermaid_type = "date"
            else:
                mermaid_type = "string"
            
            lines.append(f"        {mermaid_type} {col_id}")
        
        lines.append("    }")
    
    # Relations
    for table_id, table_def in tables.items():
        columns = table_def.get("columns", {})
        
        for col_id, col_def in columns.items():
            target = col_def.get("target")
            if target and target in tables:
                col_type = col_def.get("type", "")
                if col_type == "RefList":
                    lines.append(f"    {table_id} }}o--o{{ {target} : {col_id}")
                else:
                    lines.append(f"    {table_id} }}o--|| {target} : {col_id}")
    
    return "\n".join(lines)


def register_schema_tools(mcp):
    """Enregistre les outils de schéma."""
    mcp.tool()(create_reference_column)
    mcp.tool()(validate_schema)
    mcp.tool()(create_schema)
    mcp.tool()(export_schema)
