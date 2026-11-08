"""
Utilitaires partagés pour Grist MCP Server.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("grist_mcp_server")

# Champs de colonne que Grist ignore silencieusement à la création
# (actions AddTable / AddColumn) : ils doivent être appliqués après coup
# avec ModifyColumn. AddColumn conserve visibleCol, mais pas AddTable.
POST_CREATE_FIELDS = ("untieColIdFromLabel", "description", "visibleCol")

# Types pouvant identifier un enregistrement (choix de colonne affichée par défaut,
# repris de Grist : UserActions._pick_and_set_display_col).
IDENT_TYPES = ("Text", "Any", "Numeric", "Int", "Date", "DateTime", "Choice")

# Champs de colonne reconnus par Grist (métadonnées _grist_Tables_column).
KNOWN_COLUMN_FIELDS = {
    "type", "label", "formula", "isFormula", "widgetOptions", "description",
    "untieColIdFromLabel", "visibleCol", "recalcWhen", "recalcDeps", "rules",
}


def split_ref_type(column_type: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Décompose un type référence Grist.

    'Ref:Agents' -> ('Ref', 'Agents'), 'RefList:Agents' -> ('RefList', 'Agents'),
    tout autre type -> (None, None).
    """
    if isinstance(column_type, str) and ":" in column_type:
        base, target = column_type.split(":", 1)
        if base in ("Ref", "RefList") and target:
            return base, target
    return None, None


def merge_widget_options(widget_options: Any, choices: Optional[List[str]] = None) -> Optional[str]:
    """
    Retourne les widgetOptions sous forme de chaîne JSON (format attendu par Grist).

    - widget_options peut être un dict, une chaîne JSON ou None ;
    - choices, s'il est fourni, est ajouté à la clé "choices".
    Sans choices, une chaîne JSON fournie est renvoyée telle quelle.
    """
    if choices is None:
        if isinstance(widget_options, dict):
            return json.dumps(widget_options)
        if isinstance(widget_options, str):
            return widget_options
        return None

    opts: Dict[str, Any] = {}
    if isinstance(widget_options, dict):
        opts = dict(widget_options)
    elif isinstance(widget_options, str) and widget_options.strip():
        parsed = json.loads(widget_options)
        if not isinstance(parsed, dict):
            raise ValueError("widgetOptions doit être un objet JSON")
        opts = parsed
    opts["choices"] = list(choices)
    return json.dumps(opts)


def prepare_column_fields(col: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prépare les fields d'une colonne pour l'API Grist.

    Gère notamment:
    - Exclusion de l'id des fields
    - Sérialisation des widgetOptions en JSON string
    - Clé "choices" (raccourci) fusionnée dans widgetOptions
    """
    fields = {}

    for key, value in col.items():
        if key in ("id", "choices", "widgetOptions"):
            continue
        fields[key] = value

    widget_options = merge_widget_options(col.get("widgetOptions"), col.get("choices"))
    if widget_options is not None:
        fields["widgetOptions"] = widget_options

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
        columns_list = await client.list_columns(doc_id, table_id)
        ref = column_ref_index(columns_list).get(column_name)
        if ref is not None:
            return ref, None

        # Colonne non trouvée
        available = [c.id for c in columns_list]
        return None, f"Colonne '{column_name}' non trouvée dans '{table_id}'. Colonnes disponibles: {available}"

    except Exception as e:
        return None, f"Erreur lors de la résolution: {str(e)}"


def column_ref_index(columns_list) -> Dict[str, int]:
    """
    Index nom -> colRef d'une liste de colonnes (GristColumn).

    L'ID de colonne est prioritaire sur le libellé : un libellé ne masque
    jamais l'ID d'une autre colonne.
    """
    index: Dict[str, int] = {}
    labels: Dict[str, int] = {}
    for col in columns_list:
        fields = col.fields or {}
        col_ref = fields.get("colRef")
        if col_ref is None:
            continue
        index[col.id] = col_ref
        label = fields.get("label")
        if label:
            labels.setdefault(label, col_ref)
    for label, col_ref in labels.items():
        index.setdefault(label, col_ref)
    return index


async def check_table_exists(
    client,
    doc_id: str,
    table_id: str
) -> Tuple[bool, List[str]]:
    """
    Vérifie si une table existe dans un document.

    Une erreur d'accès à l'API (réseau, clé, document) est propagée au lieu
    d'être présentée comme une table inexistante.

    Returns:
        Tuple (exists, list_of_tables)
    """
    tables_list = await client.list_tables(doc_id)
    table_ids = [t.id for t in tables_list]
    return table_id in table_ids, table_ids


async def finalize_columns(
    client,
    doc_id: str,
    table_id: str,
    updates: Dict[str, Dict[str, Any]]
) -> List[str]:
    """
    Applique, après création, les réglages que Grist ignore à la création.

    `updates` associe l'ID réel de chaque colonne à ses réglages parmi
    untieColIdFromLabel, description et visibleCol (colRef, 0 = identifiant
    de ligne). Pour visibleCol, la formule d'affichage est aussi posée,
    sans quoi Grist afficherait l'identifiant de ligne.

    Returns:
        Liste d'avertissements (vide si tout est appliqué).
    """
    warnings: List[str] = []
    actions = [
        ["ModifyColumn", table_id, col_id, values]
        for col_id, values in updates.items() if values
    ]
    if not actions:
        return warnings
    try:
        await client.apply_user_actions(doc_id, actions)
    except Exception as e:
        cols = ", ".join(col_id for col_id, values in updates.items() if values)
        warnings.append(f"Réglages non appliqués aux colonnes {table_id}.({cols}) : {e}")
        return warnings

    display = {col_id: values["visibleCol"] for col_id, values in updates.items()
               if values and "visibleCol" in values}
    if display:
        warnings.extend(await set_display_formulas(client, doc_id, table_id, display))
    return warnings


async def set_display_formulas(
    client,
    doc_id: str,
    table_id: str,
    visible_cols: Dict[str, int]
) -> List[str]:
    """
    Pose la formule d'affichage des colonnes référence ($ref.colonne_visible).

    C'est ce que fait l'interface Grist quand on choisit « Afficher la
    colonne » : régler visibleCol seul ne suffit pas.

    Returns:
        Liste d'avertissements.
    """
    warnings: List[str] = []
    columns = {c.id: (c.fields or {}) for c in await client.list_columns(doc_id, table_id)}
    target_cache: Dict[str, Dict[int, str]] = {}
    actions = []
    for col_id, visible_ref in visible_cols.items():
        fields = columns.get(col_id)
        if fields is None:
            warnings.append(f"Colonne '{table_id}.{col_id}' introuvable pour régler son affichage")
            continue
        _, target = split_ref_type(fields.get("type"))
        if not target:
            warnings.append(
                f"'{table_id}.{col_id}' n'est pas une colonne référence : colonne affichée ignorée"
            )
            continue
        formula = ""
        if visible_ref:
            if target not in target_cache:
                target_cache[target] = {
                    (c.fields or {}).get("colRef"): c.id
                    for c in await client.list_columns(doc_id, target)
                }
            visible_id = target_cache[target].get(visible_ref)
            if not visible_id:
                warnings.append(
                    f"Colonne visible (colRef {visible_ref}) introuvable dans '{target}' "
                    f"pour '{table_id}.{col_id}'"
                )
                continue
            formula = f"${col_id}.{visible_id}"
        actions.append(["SetDisplayFormula", table_id, None, fields.get("colRef"), formula])
    if actions:
        try:
            await client.apply_user_actions(doc_id, actions)
        except Exception as e:
            warnings.append(f"Formule d'affichage non appliquée dans '{table_id}' : {e}")
    return warnings


async def create_table_with_columns(
    client,
    doc_id: str,
    table_id: str,
    columns: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Crée une table et ses colonnes, puis applique ce que Grist ignore à la création.

    Utilise l'action AddTable (identique à POST /tables) via /apply pour
    connaître les IDs réellement attribués (Grist peut les modifier, par
    exemple 'Prénom' -> 'Prenom'). Chaque colonne reçoit ensuite
    untieColIdFromLabel=True (sauf valeur explicite), sa description et
    sa colonne affichée.

    Returns:
        {"table_id": id réel, "columns": {id demandé: id réel}, "warnings": [...]}
    """
    warnings: List[str] = []
    prepared = []
    for col in columns or []:
        col_id = col.get("id")
        if not col_id:
            warnings.append(f"Colonne sans 'id' ignorée : {col}")
            continue
        fields = prepare_column_fields(col)
        unknown = sorted(set(fields) - KNOWN_COLUMN_FIELDS)
        if unknown:
            warnings.append(f"Champs inconnus de Grist ignorés pour '{col_id}' : {unknown}")
        prepared.append((col_id, fields))

    col_infos = []
    for col_id, fields in prepared:
        info = {k: v for k, v in fields.items() if k not in POST_CREATE_FIELDS}
        # Libellé par défaut = ID demandé, conservé même si Grist doit
        # modifier l'ID (ex. libellé 'Prénom', ID 'Prenom').
        info.setdefault("label", col_id)
        info["id"] = col_id
        col_infos.append(info)

    result = await client.apply_user_actions(doc_id, [["AddTable", table_id, col_infos]])
    ret = (result.get("retValues") or [{}])[0] or {}
    actual_table = ret.get("table_id", table_id)
    actual_cols = ret.get("columns") or [col_id for col_id, _ in prepared]
    mapping = dict(zip([col_id for col_id, _ in prepared], actual_cols))

    if actual_table != table_id:
        warnings.append(f"L'ID de table '{table_id}' a été modifié en '{actual_table}' par Grist")
    for requested, actual in mapping.items():
        if requested != actual:
            warnings.append(f"L'ID de colonne '{requested}' a été modifié en '{actual}' par Grist")

    updates: Dict[str, Dict[str, Any]] = {}
    for col_id, fields in prepared:
        values: Dict[str, Any] = {}
        # False est la valeur par défaut de Grist : l'envoyer déclencherait
        # un renommage de l'ID d'après le libellé. On n'envoie que True.
        if fields.get("untieColIdFromLabel", True):
            values["untieColIdFromLabel"] = True
        if fields.get("description"):
            values["description"] = fields["description"]
        if fields.get("visibleCol") is not None:
            values["visibleCol"] = fields["visibleCol"]
        updates[mapping.get(col_id, col_id)] = values
    warnings.extend(await finalize_columns(client, doc_id, actual_table, updates))

    return {"table_id": actual_table, "columns": mapping, "warnings": warnings}


async def add_reverse_reference(
    client,
    doc_id: str,
    table_id: str,
    column_id: str,
    reverse_column_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crée la colonne inverse d'une colonne référence existante.

    Utilise la référence à double sens native de Grist (AddReverseColumn) :
    les deux colonnes restent synchronisées. Si l'instance Grist ne connaît
    pas cette action (version ancienne), crée à la place une colonne
    calculée en lecture seule (lookupRecords), avec un avertissement.

    Returns:
        {"table": table cible, "column": ID réel, "two_way": bool, "warnings": [...]}
    """
    warnings: List[str] = []
    source_cols = {c.id: (c.fields or {}) for c in await client.list_columns(doc_id, table_id)}
    source_type = (source_cols.get(column_id) or {}).get("type")
    base, target = split_ref_type(source_type)
    if not target:
        raise ValueError(f"'{table_id}.{column_id}' n'est pas une colonne référence")

    try:
        result = await client.apply_user_actions(doc_id, [["AddReverseColumn", table_id, column_id]])
    except Exception as e:
        message = str(e)
        if "AddReverseColumn" not in message or "already exists" in message:
            raise
        # Instance Grist sans références à double sens : colonne calculée.
        condition = "CONTAINS($id)" if base == "RefList" else "$id"
        new_id = reverse_column_id or table_id
        payload = prepare_column_payload(
            column_id=new_id,
            column_type=f"RefList:{table_id}",
            formula=f"{table_id}.lookupRecords({column_id}={condition})",
        )
        created = await client.create_columns(doc_id, target, payload)
        actual = created[0]["id"] if created else new_id
        warnings.append(
            "Cette instance Grist ne gère pas les références à double sens : "
            f"'{target}.{actual}' est une colonne calculée en lecture seule"
        )
        values: Dict[str, Any] = {"untieColIdFromLabel": True}
        # Même choix que Grist pour une colonne inverse : première colonne
        # « identifiante » de la table source.
        for col_id, fields in source_cols.items():
            if (col_id != "manualSort" and not col_id.startswith("gristHelper_")
                    and str(fields.get("type", "")).split(":")[0] in IDENT_TYPES
                    and fields.get("colRef")):
                values["visibleCol"] = fields["colRef"]
                break
        warnings.extend(await finalize_columns(client, doc_id, target, {actual: values}))
        return {"table": target, "column": actual, "two_way": False, "warnings": warnings}

    actual = ((result.get("retValues") or [{}])[0] or {}).get("colId")
    if reverse_column_id and actual and reverse_column_id != actual:
        try:
            renamed = await client.apply_user_actions(
                doc_id, [["RenameColumn", target, actual, reverse_column_id]]
            )
            actual = (renamed.get("retValues") or [actual])[0] or actual
            if actual != reverse_column_id:
                warnings.append(
                    f"L'ID de colonne inverse '{reverse_column_id}' a été modifié en '{actual}' par Grist"
                )
        except Exception as e:
            warnings.append(f"Colonne inverse créée sous l'ID '{actual}' (renommage impossible : {e})")
    if actual:
        warnings.extend(await finalize_columns(
            client, doc_id, target, {actual: {"untieColIdFromLabel": True}}
        ))
    return {"table": target, "column": actual, "two_way": True, "warnings": warnings}


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
