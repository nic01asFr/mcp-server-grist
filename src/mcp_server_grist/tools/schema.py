"""
Outils de gestion de schéma Grist.

Outils:
- create_reference_column: Création de références avec résolution automatique
- validate_schema: Validation d'un schéma sans création
- create_schema: Création complète d'un schéma avec relations
- export_schema: Export du schéma d'un document existant

v0.2.2 : colonne affichée réellement appliquée (formule d'affichage),
relations inverses à double sens natives, untieColIdFromLabel et description
appliqués après création, notation 'Ref:Table' acceptée, relance de
create_schema sans doublons.
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
    add_reverse_reference,
    build_error_response,
    build_success_response,
    check_table_exists,
    column_ref_index,
    create_table_with_columns,
    finalize_columns,
    prepare_column_payload,
    resolve_visible_col,
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


async def _create_reference(
    client,
    doc_id: str,
    table_id: str,
    column_id: str,
    ref_type: str,
    label: Optional[str] = None,
    visible_col: Optional[int] = None,
    description: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """
    Crée une colonne référence puis applique la colonne affichée, la
    description et untieColIdFromLabel (ignorés par Grist à la création).

    Returns:
        (ID réel de la colonne, avertissements)
    """
    payload = prepare_column_payload(
        column_id=column_id,
        column_type=ref_type,
        label=label,
        visible_col=visible_col,
    )
    created = await client.create_columns(doc_id, table_id, payload)
    actual = created[0].get("id", column_id) if created else column_id
    warnings: List[str] = []
    if actual != column_id:
        warnings.append(f"L'ID de colonne '{column_id}' a été modifié en '{actual}' par Grist")

    values: Dict[str, Any] = {"untieColIdFromLabel": True}
    if description:
        values["description"] = description
    if visible_col is not None:
        values["visibleCol"] = visible_col
    warnings.extend(await finalize_columns(client, doc_id, table_id, {actual: values}))
    return actual, warnings


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
    Crée une colonne de référence qui affiche la colonne choisie de la table cible.

    Cette fonction:
    1. Vérifie que les tables source et cible existent
    2. Résout le nom (ID ou libellé) de la colonne visible
    3. Crée la colonne de référence et règle son affichage
    4. Optionnellement crée la relation inverse (référence à double sens Grist :
       les deux colonnes restent synchronisées)

    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table source
        column_id: ID de la nouvelle colonne de référence
        target_table: ID de la table cible
        visible_column: ID ou libellé de la colonne à afficher (table cible)
        is_list: Si True, crée RefList au lieu de Ref (défaut: False)
        label: Libellé d'affichage (optionnel)
        reverse_column: Si fourni, ID de la colonne inverse (RefList) créée dans target_table

    Returns:
        Dict avec statut, détails et éventuels warnings
    """
    try:
        client = get_client(ctx)
        if not client:
            return build_error_response("Client Grist non configuré")

        # PHASE 1: Validation - tables source et cible
        exists, available_tables = await check_table_exists(client, doc_id, target_table)
        if not exists:
            return build_error_response(
                f"Table cible '{target_table}' inexistante",
                details={"available_tables": available_tables}
            )
        if table_id not in available_tables:
            return build_error_response(
                f"Table source '{table_id}' inexistante",
                details={"available_tables": available_tables}
            )

        # PHASE 2: Résolution - colRef de visible_column
        col_ref, error = await resolve_visible_col(
            client, doc_id, target_table, visible_column
        )
        if error:
            return build_error_response(error)

        # PHASE 3: Création de la colonne et de son affichage
        ref_type = f"RefList:{target_table}" if is_list else f"Ref:{target_table}"
        actual_id, warnings = await _create_reference(
            client, doc_id, table_id, column_id, ref_type,
            label=label, visible_col=col_ref,
        )

        # PHASE 4: Relation inverse (optionnel)
        reverse_result = None
        if reverse_column:
            try:
                reverse = await add_reverse_reference(
                    client, doc_id, table_id, actual_id, reverse_column
                )
                warnings.extend(reverse["warnings"])
                reverse_result = {
                    "id": reverse["column"],
                    "table": reverse["table"],
                    "two_way": reverse["two_way"],
                }
            except Exception as e:
                warnings.append(
                    f"Échec création relation inverse '{reverse_column}': {str(e)}"
                )

        # PHASE 5: Réponse
        result = build_success_response(
            f"Colonne référence '{actual_id}' créée avec succès",
            column={"id": actual_id},
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


async def _existing_columns(client, doc_id: str, table_id: str, cache: Dict[str, Dict[str, int]]):
    """Index nom -> colRef d'une table existante (avec cache)."""
    if table_id not in cache:
        cache[table_id] = column_ref_index(await client.list_columns(doc_id, table_id))
    return cache[table_id]


def _schema_column_names(table: TableDefinition) -> set:
    """IDs et libellés des colonnes d'une table du schéma."""
    names = set()
    for col in table.columns:
        names.add(col.id)
        if col.label:
            names.add(col.label)
    return names


async def _validate(client, doc_id: str, schema: Dict[str, Any], cache: Dict[str, Dict[str, int]]):
    """
    Valide le schéma. Returns: (schema_def, existing_tables, errors, warnings).
    Lève ValueError si le schéma ne peut pas être lu.
    """
    errors: List[str] = []
    warnings: List[str] = []

    schema_def = parse_schema_dict(schema)
    existing_tables = {t.id for t in await client.list_tables(doc_id)}
    schema_tables = {t.id: t for t in schema_def.tables}
    all_tables = existing_tables | set(schema_tables)

    for table in schema_def.tables:
        if table.id in existing_tables:
            # Table existante : elle ne sera pas modifiée, ses colonnes
            # ne sont donc pas vérifiées.
            warnings.append(f"Table '{table.id}' existe déjà dans le document")
            continue

        for col in table.columns:
            if col.type in ("Choice", "ChoiceList") and not col.choices:
                warnings.append(
                    f"Table '{table.id}', colonne '{col.id}': "
                    f"type {col.type} sans 'choices' défini"
                )
            if col.type not in ("Ref", "RefList"):
                continue

            where = f"Table '{table.id}', colonne '{col.id}'"
            if not col.target_table:
                errors.append(f"{where}: target_table requis pour type {col.type}")
                continue
            if col.target_table not in all_tables:
                errors.append(f"{where}: table cible '{col.target_table}' inexistante")
                continue

            # Colonnes connues de la table cible (existante dans le document,
            # sinon telle que définie dans le schéma).
            target_names = None
            if col.target_table in existing_tables:
                try:
                    target_names = set(await _existing_columns(client, doc_id, col.target_table, cache))
                except Exception as e:
                    warnings.append(f"{where}: colonnes de '{col.target_table}' non vérifiées ({e})")
            else:
                target_names = _schema_column_names(schema_tables[col.target_table])

            if not col.visible_column:
                warnings.append(
                    f"{where}: pas de colonne visible ('visible'), "
                    f"la référence affichera l'identifiant de ligne"
                )
            elif target_names is not None and col.visible_column not in target_names:
                errors.append(
                    f"{where}: colonne visible '{col.visible_column}' inexistante "
                    f"dans '{col.target_table}' (disponibles: {sorted(target_names)})"
                )

            if col.reverse_column and target_names is not None and col.reverse_column in target_names:
                errors.append(
                    f"{where}: la colonne inverse '{col.reverse_column}' existe déjà "
                    f"dans '{col.target_table}'"
                )

    for data_table in (schema_def.data or {}):
        if data_table not in schema_tables:
            warnings.append(
                f"Données pour '{data_table}' ignorées : table absente du schéma"
            )

    return schema_def, existing_tables, errors, warnings


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
    - Existence des colonnes visibles ('visible') dans les tables cibles
    - Absence de conflit pour les colonnes inverses ('reverse')
    - Colonnes Choice/ChoiceList sans choix (avertissement)

    Args:
        doc_id: L'ID du document (pour vérifier les tables existantes)
        schema: Schéma à valider (format dict)

    Returns:
        Dict avec statut de validation, erreurs et warnings
    """
    try:
        client = get_client(ctx)
        if not client:
            return build_error_response("Client Grist non configuré")

        try:
            schema_def, _, errors, warnings = await _validate(client, doc_id, schema, {})
        except (ValueError, AttributeError, TypeError) as e:
            return build_error_response(f"Erreur de parsing du schéma: {str(e)}")

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


def _simple_column_dict(col: ColumnDefinition) -> Dict[str, Any]:
    """Définition de colonne simple au format attendu par create_table_with_columns."""
    col_def: Dict[str, Any] = {"id": col.id, "type": col.type}
    if col.label:
        col_def["label"] = col.label
    if col.formula:
        col_def["formula"] = col.formula
        col_def["isFormula"] = True
    if col.description:
        col_def["description"] = col.description
    if col.widget_options:
        col_def["widgetOptions"] = col.widget_options
    if col.choices:
        col_def["choices"] = col.choices
    return col_def


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
    1. Validation du schéma (rien n'est créé si elle échoue)
    2. Création des tables avec leurs colonnes simples
    3. Création des colonnes de référence (colonne affichée réglée)
    4. Création des relations inverses (références à double sens)
    5. Insertion des données (optionnel)

    Les tables déjà présentes dans le document ne sont jamais modifiées : ni
    colonnes, ni références, ni données ne leur sont ajoutées. Relancer le
    même schéma ne crée donc pas de doublons. Elles restent utilisables comme
    cibles de références.

    Args:
        doc_id: L'ID du document
        schema: Schéma complet à créer
        skip_existing: Si True (défaut), ignore les tables existantes. Si False,
            échoue sans rien créer quand une table existe déjà.
        insert_data: Si True, insère les données définies (défaut: True)

    Returns:
        Dict avec rapport détaillé de création

    Example schema:
        {
            "tables": {
                "Agents": {"columns": {
                    "nom": {"type": "Text", "label": "Nom"},
                    "service": {"type": "Choice", "choices": ["A", "B"]}
                }},
                "Taches": {"columns": {
                    "titre": "Text",
                    "responsable": {"type": "Ref", "target": "Agents",
                                    "visible": "nom", "reverse": "taches"}
                }}
            },
            "data": {"Agents": [{"nom": "Dupont", "service": "A"}]}
        }
        "Ref:Agents" est accepté comme équivalent de {"type": "Ref", "target": "Agents"}.
    """
    report = SchemaCreationReport()

    try:
        client = get_client(ctx)
        if not client:
            return build_error_response("Client Grist non configuré")

        # PHASE 1: Validation
        col_cache: Dict[str, Dict[str, int]] = {}
        try:
            schema_def, existing_tables, errors, warnings = await _validate(
                client, doc_id, schema, col_cache
            )
        except (ValueError, AttributeError, TypeError) as e:
            return build_error_response(f"Erreur de parsing du schéma: {str(e)}")
        if errors:
            return build_error_response(
                "Schéma invalide",
                details={"errors": errors, "warnings": warnings}
            )
        already = [t.id for t in schema_def.tables if t.id in existing_tables]
        if already and not skip_existing:
            return build_error_response(
                "Tables déjà présentes (skip_existing=False) : rien n'a été créé",
                details={"existing_tables": already}
            )
        report.warnings.extend(warnings)

        # Mapping table_id schéma → table_id réel (au cas où Grist renomme)
        table_mapping = {t: t for t in existing_tables}
        column_mapping: Dict[str, Dict[str, str]] = {}
        created: set = set()

        # PHASE 2: Création des tables avec colonnes simples
        for table in schema_def.tables:
            if table.id in existing_tables:
                report.warnings.append(f"Table '{table.id}' ignorée (existe déjà)")
                continue

            simple_columns = [_simple_column_dict(col) for col in table.get_simple_columns()]
            try:
                result = await create_table_with_columns(client, doc_id, table.id, simple_columns)
            except Exception as e:
                report.errors.append(f"Échec création table '{table.id}': {str(e)}")
                continue
            table_mapping[table.id] = result["table_id"]
            column_mapping[table.id] = result["columns"]
            created.add(table.id)
            report.warnings.extend(result["warnings"])
            report.tables_created.append({
                "id": result["table_id"],
                "requested_id": table.id,
                "columns_count": len(simple_columns),
                "columns": result["columns"],
            })

        # PHASES 3-4: Colonnes de référence et relations inverses
        for table in schema_def.tables:
            if table.id not in created:
                continue
            actual_table_id = table_mapping[table.id]

            for col in table.get_reference_columns():
                target_table = table_mapping.get(col.target_table)
                if not target_table:
                    report.errors.append(
                        f"Référence {table.id}.{col.id} non créée : "
                        f"table cible '{col.target_table}' non créée"
                    )
                    continue
                ref_type = f"{col.type}:{target_table}"
                try:
                    visible_col_ref = None
                    if col.visible_column:
                        # ID réel si Grist a modifié l'ID demandé (ex. 'Prénom' -> 'Prenom')
                        visible_name = column_mapping.get(col.target_table, {}).get(
                            col.visible_column, col.visible_column
                        )
                        index = await _existing_columns(client, doc_id, target_table, col_cache)
                        visible_col_ref = index.get(visible_name)
                        if visible_col_ref is None:
                            report.warnings.append(
                                f"Colonne visible '{col.visible_column}' non résolue "
                                f"pour {table.id}.{col.id}"
                            )

                    actual_col, col_warnings = await _create_reference(
                        client, doc_id, actual_table_id, col.id, ref_type,
                        label=col.label, visible_col=visible_col_ref,
                        description=col.description,
                    )
                    report.warnings.extend(col_warnings)
                    report.references_created.append({
                        "table": actual_table_id,
                        "column": actual_col,
                        "target": target_table,
                        "type": ref_type
                    })
                except Exception as e:
                    report.errors.append(
                        f"Échec création référence {table.id}.{col.id}: {str(e)}"
                    )
                    continue

                if col.reverse_column:
                    try:
                        reverse = await add_reverse_reference(
                            client, doc_id, actual_table_id, actual_col, col.reverse_column
                        )
                        report.warnings.extend(reverse["warnings"])
                        report.references_created.append({
                            "table": reverse["table"],
                            "column": reverse["column"],
                            "target": actual_table_id,
                            "type": f"RefList:{actual_table_id}",
                            "is_reverse": True,
                            "two_way": reverse["two_way"],
                        })
                    except Exception as e:
                        report.warnings.append(
                            f"Échec relation inverse '{col.reverse_column}': {str(e)}"
                        )

        # PHASE 5: Insertion des données (tables créées par cet appel uniquement)
        if insert_data and schema_def.data:
            for table_id, records in schema_def.data.items():
                if not records:
                    continue
                if table_id not in created:
                    if table_id in existing_tables:
                        report.warnings.append(
                            f"Données pour '{table_id}' non insérées : table existante non modifiée"
                        )
                    continue
                actual_table_id = table_mapping[table_id]
                try:
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
