"""
Module d'outils pour la gestion des formulaires Grist via MCP.
Fournit des fonctions simplifiées pour créer, gérer et interagir avec des formulaires dans Grist.
"""

import json
import logging
import os
import re
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from urllib.parse import urljoin, urlparse
import functools

import httpx
from pydantic import BaseModel, Field

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grist_form_tools")

# Ajouter cette constante au début du fichier
JSON_FORMAT_HELP = """
FORMAT JSON ACCEPTÉ:
-------------------
Les entrées JSON peuvent être fournies sous deux formes:

1. Objet Python directement (liste ou dictionnaire)
   fields = [{"name": "Nom", "label": "Votre nom", "required": True}]

2. Chaîne JSON standard:
   fields_json = '[{"name":"Nom","label":"Votre nom","required":true}]'

ÉVITEZ les formats avec double échappement comme:
   '"{\\\"name\\\":\\\"Nom\\\"}"'

STRUCTURE DES CHAMPS:
-------------------
Chaque champ doit avoir au minimum:
- name: Identifiant du champ (alphanumérique + underscore)
- label: Libellé affiché dans le formulaire

Options supplémentaires:
- type: Type de données (Text, Int, Bool, Date, etc.)
- widget: Type de widget (TextBox, Dropdown, etc.)
- required: Si le champ est obligatoire (true/false)
- options: Options spécifiques au widget
- description: Texte d'aide pour le champ
"""

# Fonction pour obtenir l'URL de base Grist à partir de l'URL d'API
def get_base_url():
    """
    Récupère l'URL de base Grist à partir de l'URL d'API dans les variables d'environnement.
    Si GRIST_API_URL n'est pas défini, utilise l'URL par défaut.
    
    Returns:
        str: L'URL de base Grist (sans '/api')
    """
    api_url = os.environ.get("GRIST_API_URL", os.environ.get("GRIST_API_HOST", "https://docs.getgrist.com/api"))
    
    # Supprimer le '/api' à la fin si présent
    base_url = api_url.rstrip("/")
    if base_url.endswith("/api"):
        base_url = base_url[:-4]
    
    # Alternative: utiliser urlparse
    # parsed_url = urlparse(api_url)
    # base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    logger.debug(f"URL de base Grist: {base_url}")
    return base_url

def parse_json_safely(json_input, default=None, field_name=""):
    """
    Parse une entrée JSON de manière sécurisée, en gérant différents formats d'entrée.
    
    Args:
        json_input: Entrée à parser (chaîne JSON, dict/list Python, ou None)
        default: Valeur par défaut si json_input est None
        field_name: Nom du champ pour les messages d'erreur
        
    Returns:
        L'objet Python parsé à partir du JSON ou l'objet Python directement
        
    Exemples:
        >>> parse_json_safely('[{"name": "Nom", "label": "Votre nom"}]')
        [{'name': 'Nom', 'label': 'Votre nom'}]
        
        >>> parse_json_safely({"name": "Nom", "label": "Votre nom"})
        {'name': 'Nom', 'label': 'Votre nom'}
    """
    if json_input is None:
        return default
    
    # Si c'est déjà un dict ou une liste, le retourner tel quel
    if isinstance(json_input, (dict, list)):
        logger.debug(f"Le paramètre {field_name} est déjà un objet Python")
        return json_input
    
    # Si c'est une chaîne, essayer de la parser comme JSON
    if isinstance(json_input, str):
        # Nettoyage préliminaire de la chaîne
        json_str = json_input.strip()
        
        try:
            # Cas 1: JSON standard
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Cas 2: JSON avec double échappement
            if json_str.startswith('"') and json_str.endswith('"'):
                try:
                    # Désérialiser une première fois pour obtenir la chaîne interne
                    unescaped = json.loads(json_str)
                    if isinstance(unescaped, str):
                        try:
                            # Désérialiser la chaîne interne
                            return json.loads(unescaped)
                        except json.JSONDecodeError:
                            # Peut-être que c'était juste une chaîne simple
                            return unescaped
                    return unescaped
                except json.JSONDecodeError:
                    pass
            
            # Cas 3: Essayer de réparer les formats communs incorrects
            try:
                # Remplacer les single quotes par des double quotes
                if "'" in json_str and '"' not in json_str:
                    fixed_json = json_str.replace("'", '"')
                    return json.loads(fixed_json)
            except json.JSONDecodeError:
                pass
                
            # JSON invalide après toutes les tentatives
            error_preview = json_str[:100] + ("..." if len(json_str) > 100 else "")
            logger.error(f"Format JSON invalide pour {field_name}: {error_preview}")
            raise ValueError(f"Le format JSON pour {field_name} est invalide. Utilisez un objet/array JSON valide ou un dictionnaire/liste Python.")
    
    # Type non supporté
    raise ValueError(f"{field_name} est de type {type(json_input).__name__}, alors qu'un objet JSON ou dict/liste est attendu.")

# Modèles de données
class FormField(BaseModel):
    """Définition d'un champ de formulaire"""
    name: str
    label: str
    type: str = "Text"
    widget: str = "TextBox"
    required: bool = False
    default: Optional[Any] = None
    options: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

class FormOptions(BaseModel):
    """Options globales du formulaire"""
    description: Optional[str] = None
    success_message: Optional[str] = None
    allow_multiple: bool = True
    notification_email: Optional[str] = None
    theme: str = "default"

class ValidationRule(BaseModel):
    """Règle de validation pour un champ"""
    type: str
    params: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

# Types de validation supportés
VALIDATION_FORMULAS = {
        "email_format": "not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+$', ${column_id})",
        "unique_value": "len({table_id}.lookupRecords({column_id}=${{{column_id}}})) > 1",
        "required": "${column_id} is None or ${column_id} == ''",
        "min_length": "len(str(${column_id} or '')) < {min_length}",
        "max_length": "len(str(${column_id} or '')) > {max_length}",
        "min_value": "${column_id} < {min_value}",
        "max_value": "${column_id} > {max_value}",
        "pattern_match": "not re.match(r'{pattern}', str(${column_id} or ''))",
        "date_after": "${column_id} < {date}",
        "date_before": "${column_id} > {date}",
        "in_list": "${column_id} not in [{values}]"
}

# Templates prédéfinis pour différents types de formulaires
FORM_TEMPLATES = {
    "event_registration": [
        FormField(name="Nom", label="Nom", required=True),
        FormField(name="Prenom", label="Prénom", required=True),
        FormField(name="Email", label="Email", required=True),
        FormField(name="Telephone", label="Téléphone", required=False),
        FormField(
            name="Participation", 
            label="Mode de participation", 
            type="Choice", 
            widget="Dropdown",
            required=True,
            options={"choices": ["En présentiel", "En ligne"]}
        ),
        FormField(
            name="Commentaires", 
            label="Commentaires", 
            widget="TextArea", 
            required=False
        )
    ],
    "survey": [
        FormField(name="Nom", label="Nom", required=False),
        FormField(name="Email", label="Email", required=False),
        FormField(
            name="Satisfaction", 
            label="Niveau de satisfaction", 
            type="Int", 
            widget="Rating",
            required=True,
            options={"max": 5}
        ),
        FormField(
            name="Commentaire", 
            label="Commentaires", 
            widget="TextArea", 
            required=False
        )
    ],
    "contact": [
        FormField(name="Nom", label="Nom", required=True),
        FormField(name="Email", label="Email", required=True),
        FormField(name="Objet", label="Objet du message", required=True),
        FormField(
            name="Message", 
            label="Votre message", 
            widget="TextArea", 
            required=True
        )
    ],
    "application": [
        FormField(name="Nom", label="Nom", required=True),
        FormField(name="Prenom", label="Prénom", required=True),
        FormField(name="Email", label="Email", required=True),
        FormField(name="Telephone", label="Téléphone", required=True),
        FormField(
            name="CV", 
            label="CV", 
            type="Attachments", 
            required=True
        ),
        FormField(
            name="LettreMotivation", 
            label="Lettre de motivation", 
            type="Text",
            widget="TextArea", 
            required=True
        ),
        FormField(
            name="Disponibilite", 
            label="Date de disponibilité", 
            type="Date", 
            widget="Date",
            required=True
        )
    ]
}

# Fonction principale pour créer un formulaire
async def create_form(
    client,
    doc_id: str,
    form_name: str,
    fields: List[Union[Dict[str, Any], FormField]],
    form_options: Optional[Union[Dict[str, Any], FormOptions]] = None,
    validation_rules: Optional[Dict[str, List[Union[Dict[str, Any], ValidationRule]]]] = None
) -> Dict[str, Any]:
    """
    Crée un formulaire complet dans un document Grist existant.
    
    Args:
        client: Client Grist API
        doc_id: ID du document Grist
        form_name: Nom du formulaire
        fields: Liste des champs du formulaire (liste de dictionnaires ou objets FormField)
        form_options: Options globales du formulaire (dictionnaire ou objet FormOptions)
        validation_rules: Règles de validation par champ
        
    Returns:
        Dict contenant les informations sur le formulaire créé
    """
    # Normaliser les entrées avec gestion d'erreur améliorée
    normalized_fields = []
    try:
        for field in fields:
            if isinstance(field, dict):
                try:
                    normalized_fields.append(FormField(**field))
                except Exception as e:
                    error_msg = f"Erreur de format pour le champ '{field.get('name', '?')}': {str(e)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                normalized_fields.append(field)
    except Exception as e:
        if not str(e).startswith("Erreur de format"):
            raise ValueError(f"Erreur lors de la normalisation des champs: {str(e)}")
        else:
            raise
            
    # Créer le tableau pour le formulaire
    table_id = re.sub(r'[^a-zA-Z0-9_]', '_', form_name)
    
    # Préparer les colonnes
    columns = []
    for field in normalized_fields:
        # Configurer les options de widget
        widget_options = {
            "widget": field.widget,
            "alignment": "left",
            "formRequired": field.required,
            "question": f"{field.label}:"
        }
        
        # Ajouter des options spécifiques
        if field.options:
            widget_options.update(field.options)
        
        # Créer la colonne
        column = {
            "id": re.sub(r'[^a-zA-Z0-9_]', '_', field.name),
            "fields": {
                "label": field.label,
                "type": field.type,
                "widgetOptions": json.dumps(widget_options),
                "description": field.description or ""
            }
        }
        columns.append(column)
    
    # Ajouter une colonne timestamp
    columns.append({
        "id": "Timestamp",
        "fields": {
            "label": "Date de soumission",
            "type": "DateTime:UTC",
            "isFormula": True,
            "formula": "NOW()",
        }
    })
    
    # Structure de la table
    table_data = {
        "tables": [{
            "id": table_id,
            "columns": columns
        }]
    }
    
    # Créer la table via l'API
    try:
        await client._request("POST", f"/docs/{doc_id}/tables", json_data=table_data)
        logger.info(f"Table {table_id} créée avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la création de la table: {e}")
        raise ValueError(f"Erreur lors de la création du formulaire: {str(e)}")
    
    # Ajouter les règles de validation
    if validation_rules:
        for field_name, rules in validation_rules.items():
            normalized_rules = []
            for rule in rules:
                if isinstance(rule, dict):
                    normalized_rules.append(ValidationRule(**rule))
                else:
                    normalized_rules.append(rule)
            
            for rule in normalized_rules:
                await _add_validation_rule(
                    client, 
                    doc_id, 
                    table_id, 
                    re.sub(r'[^a-zA-Z0-9_]', '_', field_name), 
                    rule.type, 
                    rule.params or {},
                    rule.error_message
                )
    
    # Créer une table de configuration si nécessaire
    if form_options:
        if isinstance(form_options, dict):
            form_options = FormOptions(**form_options)
        
        config_table_id = f"{table_id}_Config"
        config_table = {
            "tables": [{
                "id": config_table_id,
                "columns": [
                    {
                        "id": "Option",
                        "fields": {"label": "Option", "type": "Text"}
                    },
                    {
                        "id": "Value",
                        "fields": {"label": "Valeur", "type": "Text"}
                    }
                ]
            }]
        }
        
        try:
            await client._request("POST", f"/docs/{doc_id}/tables", json_data=config_table)
            
            # Ajouter les options comme enregistrements
            config_records = [
                {"fields": {"Option": key, "Value": str(value)}}
                for key, value in form_options.dict().items()
                if value is not None
            ]
            
            if config_records:
                await client._request(
                    "POST",
                    f"/docs/{doc_id}/tables/{config_table_id}/records",
                    json_data={"records": config_records}
                )
        except Exception as e:
            logger.warning(f"Impossible de créer la table de configuration: {e}")
    
    # Créer une description pour le formulaire
    if form_options and form_options.description:
        description_table_id = f"{table_id}_Description"
        description_table = {
            "tables": [{
                "id": description_table_id,
                "columns": [
                    {
                        "id": "Description",
                        "fields": {"label": "Description", "type": "Text"}
                    }
                ]
            }]
        }
        
        try:
            await client._request("POST", f"/docs/{doc_id}/tables", json_data=description_table)
            
            # Ajouter la description
            await client._request(
                "POST",
                f"/docs/{doc_id}/tables/{description_table_id}/records",
                json_data={
                    "records": [
                        {"fields": {"Description": form_options.description}}
                    ]
                }
            )
        except Exception as e:
            logger.warning(f"Impossible de créer la table de description: {e}")
    
    # Utiliser l'URL de base dynamique
    base_url = get_base_url()
    
    return {
        "status": "success",
        "form_id": table_id,
        "document_id": doc_id,
        "fields_count": len(normalized_fields),
        "validation_count": sum(len(rules) for rules in (validation_rules or {}).values()),
        "form_url": f"{base_url}/doc/{doc_id}"
    }

async def _add_validation_rule(
    client, 
    doc_id: str, 
    table_id: str, 
    column_id: str, 
    validation_type: str, 
    params: Dict[str, Any],
    error_message: Optional[str] = None
):
    """
    Ajoute une règle de validation à une colonne
    """
    if validation_type not in VALIDATION_FORMULAS:
        raise ValueError(f"Type de validation non supporté: {validation_type}")
    
    # Préparer la formule
    formula_template = VALIDATION_FORMULAS[validation_type]
    formula = formula_template.replace("{table_id}", table_id).replace("{column_id}", column_id)
    
    # Remplacer les paramètres dans la formule
    for param_key, param_value in params.items():
        if param_key == "values":
            # Pour in_list, former une liste appropriée
            values_str = ", ".join([f'"{v}"' if isinstance(v, str) else str(v) for v in param_value])
            formula = formula.replace(f"{{{param_key}}}", values_str)
        else:
            # Pour les autres paramètres
            formula = formula.replace(f"{{{param_key}}}", 
                                   f'"{param_value}"' if isinstance(param_value, str) else str(param_value))
    
    # Créer une colonne de validation
    validation_column = {
        "columns": [
            {
                "id": f"Valid_{column_id}_{validation_type}",
                "fields": {
                    "label": error_message or f"Validation {validation_type}",
                    "type": "Bool",
                    "isFormula": True,
                    "formula": formula,
                    "widgetOptions": json.dumps({
                        "widget": "CheckBox",
                        "rulesOptions": [{"fillColor": "#FFDDDD"}]
                    })
                }
            }
        ]
    }
    
    await client._request(
        "POST", 
        f"/docs/{doc_id}/tables/{table_id}/columns", 
        json_data=validation_column
    )

async def create_form_from_template(
    client,
    doc_id: str,
    form_name: str,
    template_type: str,
    custom_fields: Optional[List[Union[Dict[str, Any], FormField]]] = None,
    form_options: Optional[Union[Dict[str, Any], FormOptions]] = None
) -> Dict[str, Any]:
    """
    Crée un formulaire basé sur un template prédéfini.
    
    Args:
        client: Client Grist API
        doc_id: ID du document Grist
        form_name: Nom du formulaire
        template_type: Type de template (event_registration, survey, contact, application)
        custom_fields: Champs personnalisés à ajouter au template
        form_options: Options globales du formulaire
        
    Returns:
        Informations sur le formulaire créé
    """
    if template_type not in FORM_TEMPLATES:
        raise ValueError(f"Type de template non reconnu: {template_type}. Disponibles: {', '.join(FORM_TEMPLATES.keys())}")
    
    # Obtenir les champs du template
    fields = list(FORM_TEMPLATES[template_type])
    
    # Ajouter les champs personnalisés
    if custom_fields:
        for field in custom_fields:
            if isinstance(field, dict):
                fields.append(FormField(**field))
            else:
                fields.append(field)
    
    # Créer les validations standard pour le template
    validation_rules = {}
    
    # Pour tous les templates, valider les emails
    for field in fields:
        if field.name.lower() == 'email':
            validation_rules[field.name] = [
                ValidationRule(
                    type="email_format", 
                    error_message="Format d'email invalide"
                )
            ]
    
    # Créer le formulaire
    return await create_form(
        client,
        doc_id,
        form_name,
        fields,
        form_options,
        validation_rules
    )

async def get_form_responses(
    client,
    doc_id: str,
    form_id: str,
    format_type: str = "records",
    include_validation: bool = False
) -> Dict[str, Any]:
    """
    Récupère les réponses d'un formulaire dans le format demandé.
    
    Args:
        client: Client Grist API
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        format_type: Format de sortie (records, summary, stats)
        include_validation: Inclure les colonnes de validation
        
    Returns:
        Les réponses du formulaire dans le format demandé
    """
    # Récupérer les colonnes du formulaire
    columns_data = await client._request("GET", f"/docs/{doc_id}/tables/{form_id}/columns")
    columns = columns_data.get("columns", [])
    
    # Filtrer les colonnes de validation si nécessaire
    if not include_validation:
        columns = [col for col in columns if not col["id"].startswith("Valid_")]
    
    # Récupérer les enregistrements
    records_data = await client._request("GET", f"/docs/{doc_id}/tables/{form_id}/records")
    records = records_data.get("records", [])
    
    if format_type == "records":
        return {
            "form_id": form_id,
            "responses_count": len(records),
            "columns": [col["id"] for col in columns if not col["id"].startswith("Valid_")],
            "responses": records
        }
    
    elif format_type == "summary":
        # Préparer un résumé avec les champs principaux
        summary = []
        for record in records:
            record_summary = {}
            for col in columns:
                if not col["id"].startswith("Valid_") and col["id"] != "Timestamp":
                    record_summary[col["id"]] = record["fields"].get(col["id"])
            if "Timestamp" in record["fields"]:
                record_summary["Soumis le"] = record["fields"]["Timestamp"]
            summary.append(record_summary)
        
        return {
            "form_id": form_id,
            "responses_count": len(records),
            "summary": summary
        }
    
    elif format_type == "stats":
        # Calculer des statistiques sur les réponses
        stats = {
            "total_responses": len(records),
            "fields_stats": {}
        }
        
        for col in columns:
            if col["id"].startswith("Valid_") or col["id"] == "Timestamp":
                continue
            
            col_type = col["fields"].get("type", "").split(":")[0]
            values = [record["fields"].get(col["id"]) for record in records]
            values = [v for v in values if v is not None]
            
            if col_type in ["Int", "Numeric"]:
                # Statistiques numériques
                if values:
                    stats["fields_stats"][col["id"]] = {
                        "avg": sum(values) / len(values) if values else 0,
                        "min": min(values) if values else None,
                        "max": max(values) if values else None,
                        "count": len(values)
                    }
            elif col_type in ["Choice", "ChoiceList"]:
                # Comptage des choix
                choice_counts = {}
                for value in values:
                    if isinstance(value, list):  # ChoiceList
                        for choice in value:
                            choice_counts[choice] = choice_counts.get(choice, 0) + 1
                    else:  # Choice
                        choice_counts[value] = choice_counts.get(value, 0) + 1
                
                stats["fields_stats"][col["id"]] = {
                    "count": len(values),
                    "distribution": choice_counts
                }
            else:
                # Comptage simple pour les autres types
                stats["fields_stats"][col["id"]] = {
                    "count": len(values)
                }
        
        return stats
    
    else:
        raise ValueError(f"Format non reconnu: {format_type}. Utilisez 'records', 'summary' ou 'stats'")

async def get_form_structure(
    client,
    doc_id: str,
    form_id: str
) -> Dict[str, Any]:
    """
    Récupère la structure d'un formulaire existant.
    
    Args:
        client: Client Grist API
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        
    Returns:
        La structure complète du formulaire
    """
    # Récupérer les colonnes du formulaire
    columns_data = await client._request("GET", f"/docs/{doc_id}/tables/{form_id}/columns")
    columns = columns_data.get("columns", [])
    
    # Séparer les colonnes normales et de validation
    form_columns = []
    validation_columns = []
    
    for col in columns:
        if col["id"].startswith("Valid_"):
            validation_columns.append(col)
        elif col["id"] != "Timestamp":
            form_columns.append(col)
    
    # Extraire les champs du formulaire
    fields = []
    for col in form_columns:
        # Extraire les options de widget
        widget_options = {}
        if "widgetOptions" in col["fields"]:
            try:
                widget_options = json.loads(col["fields"]["widgetOptions"])
            except:
                widget_options = {}
        
        field = {
            "name": col["id"],
            "label": col["fields"].get("label", col["id"]),
            "type": col["fields"].get("type", "Text"),
            "widget": widget_options.get("widget", "TextBox"),
            "required": widget_options.get("formRequired", False),
            "description": col["fields"].get("description", "")
        }
        
        if widget_options.get("choices"):
            field["options"] = {"choices": widget_options["choices"]}
        
        fields.append(field)
    
    # Reconstruire les règles de validation
    validation_rules = {}
    for col in validation_columns:
        if col["id"].startswith("Valid_"):
            parts = col["id"].split("_")
            if len(parts) >= 3:
                field_name = parts[1]
                validation_type = "_".join(parts[2:])
                
                if field_name not in validation_rules:
                    validation_rules[field_name] = []
                
                validation_rules[field_name].append({
                    "type": validation_type,
                    "error_message": col["fields"].get("label", f"Validation {validation_type}")
                })
    
    # Vérifier s'il y a une table de configuration
    config_table_id = f"{form_id}_Config"
    form_options = {}
    
    try:
        config_records = await client._request("GET", f"/docs/{doc_id}/tables/{config_table_id}/records")
        for record in config_records.get("records", []):
            option = record["fields"].get("Option")
            value = record["fields"].get("Value")
            if option and value is not None:
                if value.lower() == "true":
                    form_options[option] = True
                elif value.lower() == "false":
                    form_options[option] = False
                else:
                    form_options[option] = value
    except:
        pass
    
    # Vérifier s'il y a une table de description
    description_table_id = f"{form_id}_Description"
    
    try:
        description_records = await client._request("GET", f"/docs/{doc_id}/tables/{description_table_id}/records")
        if description_records.get("records"):
            form_options["description"] = description_records["records"][0]["fields"].get("Description", "")
    except:
        pass
    
    return {
        "form_id": form_id,
        "document_id": doc_id,
        "fields": fields,
        "validation_rules": validation_rules,
        "form_options": form_options
    }

async def update_form(
    client,
    doc_id: str,
    form_id: str,
    fields_to_add: Optional[List[Union[Dict[str, Any], FormField]]] = None,
    fields_to_update: Optional[Dict[str, Dict[str, Any]]] = None,
    fields_to_remove: Optional[List[str]] = None,
    form_options: Optional[Union[Dict[str, Any], FormOptions]] = None
) -> Dict[str, Any]:
    """
    Met à jour un formulaire existant.
    
    Args:
        client: Client Grist API
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        fields_to_add: Nouveaux champs à ajouter
        fields_to_update: Champs à mettre à jour (par nom de champ)
        fields_to_remove: Champs à supprimer
        form_options: Nouvelles options de formulaire
        
    Returns:
        Informations sur la mise à jour
    """
    changes = {
        "added": [],
        "updated": [],
        "removed": [],
        "options_updated": False
    }
    
    # Ajouter de nouveaux champs
    if fields_to_add:
        columns_to_add = []
        for field in fields_to_add:
            if isinstance(field, dict):
                field = FormField(**field)
            
            # Configurer les options de widget
            widget_options = {
                "widget": field.widget,
                "alignment": "left",
                "formRequired": field.required,
                "question": f"{field.label}:"
            }
            
            # Ajouter des options spécifiques
            if field.options:
                widget_options.update(field.options)
            
            # Créer la colonne
            column = {
                "id": re.sub(r'[^a-zA-Z0-9_]', '_', field.name),
                "fields": {
                    "label": field.label,
                    "type": field.type,
                    "widgetOptions": json.dumps(widget_options),
                    "description": field.description or ""
                }
            }
            columns_to_add.append(column)
            changes["added"].append(field.name)
        
        if columns_to_add:
            columns_data = {"columns": columns_to_add}
            await client._request("POST", f"/docs/{doc_id}/tables/{form_id}/columns", json_data=columns_data)
    
    # Mettre à jour des champs existants
    if fields_to_update:
        for field_name, updates in fields_to_update.items():
            column_id = re.sub(r'[^a-zA-Z0-9_]', '_', field_name)
            
            # Récupérer la colonne existante
            try:
                column_data = await client._request("GET", f"/docs/{doc_id}/tables/{form_id}/columns")
                columns = column_data.get("columns", [])
                
                column = next((col for col in columns if col["id"] == column_id), None)
                if not column:
                    logger.warning(f"Colonne {column_id} non trouvée pour mise à jour")
                    continue
                
                # Préparer les mises à jour
                current_fields = column["fields"]
                
                # Mettre à jour le widget si nécessaire
                if "widget" in updates or "required" in updates or "options" in updates:
                    widget_options = {}
                    if "widgetOptions" in current_fields:
                        try:
                            widget_options = json.loads(current_fields["widgetOptions"])
                        except:
                            widget_options = {"widget": "TextBox", "alignment": "left"}
                    
                    if "widget" in updates:
                        widget_options["widget"] = updates["widget"]
                    
                    if "required" in updates:
                        widget_options["formRequired"] = updates["required"]
                    
                    if "options" in updates and updates["options"]:
                        widget_options.update(updates["options"])
                    
                    current_fields["widgetOptions"] = json.dumps(widget_options)
                
                # Mettre à jour d'autres propriétés
                if "label" in updates:
                    current_fields["label"] = updates["label"]
                
                if "type" in updates:
                    current_fields["type"] = updates["type"]
                
                if "description" in updates:
                    current_fields["description"] = updates["description"]
                
                # Envoyer la mise à jour
                update_data = {
                    "columns": [
                        {
                            "id": column_id,
                            "fields": current_fields
                        }
                    ]
                }
                
                await client._request("PATCH", f"/docs/{doc_id}/tables/{form_id}/columns", json_data=update_data)
                changes["updated"].append(field_name)
                
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour de {field_name}: {e}")
    
    # Supprimer des champs
    if fields_to_remove:
        for field_name in fields_to_remove:
            column_id = re.sub(r'[^a-zA-Z0-9_]', '_', field_name)
            try:
                await client._request("DELETE", f"/docs/{doc_id}/tables/{form_id}/columns/{column_id}")
                changes["removed"].append(field_name)
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {field_name}: {e}")
    
    # Mettre à jour les options du formulaire
    if form_options:
        if isinstance(form_options, dict):
            form_options = FormOptions(**form_options)
        
        config_table_id = f"{form_id}_Config"
        
        try:
            # Vérifier si la table de configuration existe
            try:
                await client._request("GET", f"/docs/{doc_id}/tables/{config_table_id}/records")
            except:
                # Créer la table si elle n'existe pas
                config_table = {
                    "tables": [{
                        "id": config_table_id,
                        "columns": [
                            {
                                "id": "Option",
                                "fields": {"label": "Option", "type": "Text"}
                            },
                            {
                                "id": "Value",
                                "fields": {"label": "Valeur", "type": "Text"}
                            }
                        ]
                    }]
                }
                
                await client._request("POST", f"/docs/{doc_id}/tables", json_data=config_table)
                
            # Mettre à jour ou ajouter les options
            # D'abord, récupérer les options existantes
            records_data = await client._request("GET", f"/docs/{doc_id}/tables/{config_table_id}/records")
            existing_records = records_data.get("records", [])
            
            # Identifier les options existantes
            existing_options = {}
            for record in existing_records:
                option = record["fields"].get("Option")
                if option:
                    existing_options[option] = record["id"]
            
            # Préparer les mises à jour et ajouts
            updates = []
            additions = []
            
            for key, value in form_options.dict().items():
                if value is not None:
                    str_value = str(value)
                    if key in existing_options:
                        # Mise à jour
                        updates.append({
                            "id": existing_options[key],
                            "fields": {"Value": str_value}
                        })
                    else:
                        # Ajout
                        additions.append({
                            "fields": {"Option": key, "Value": str_value}
                        })
            
            # Appliquer les mises à jour
            if updates:
                await client._request(
                    "PATCH",
                    f"/docs/{doc_id}/tables/{config_table_id}/records",
                    json_data={"records": updates}
                )
            
            # Appliquer les ajouts
            if additions:
                await client._request(
                    "POST",
                    f"/docs/{doc_id}/tables/{config_table_id}/records",
                    json_data={"records": additions}
                )
            
            changes["options_updated"] = True
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des options: {e}")
    
    return {
        "status": "success",
        "form_id": form_id,
        "document_id": doc_id,
        "changes": changes
    }

async def generate_form_url(
    client,
    doc_id: str,
    form_id: str,
    is_public: bool = True
) -> str:
    """
    Génère l'URL d'un formulaire Grist.
    
    Args:
        client: Client Grist API
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        is_public: Si l'URL doit être publique
        
    Returns:
        L'URL du formulaire
    """
    # Obtenir les informations du document
    try:
        doc_info = await client._request("GET", f"/docs/{doc_id}")
        
        # Construire l'URL de base dynamiquement
        base_url = get_base_url()
        
        if is_public:
            # URL pour formulaire public
            return f"{base_url}/s/{doc_id}/p/form-{form_id}"
        else:
            # URL pour formulaire avec accès restreint
            org_id = doc_info.get("workspace", {}).get("org", {}).get("id", "")
            return f"{base_url}/o/{org_id}/doc/{doc_id}#form/{form_id}"
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'URL: {e}")
        raise ValueError(f"Impossible de générer l'URL du formulaire: {str(e)}")

# Fonctions pour exposer via MCP

async def create_grist_form(
    doc_id: str,
    form_name: str,
    fields_json: str,
    form_options_json: Optional[str] = None,
    validation_rules_json: Optional[str] = None,
    ctx = None,
    _client = None
) -> Dict[str, Any]:
    """
    Crée un formulaire Grist avec tous les paramètres spécifiés.
    
    Args:
        doc_id: ID du document Grist
        form_name: Nom du formulaire
        fields_json: Définition des champs du formulaire. Peut être:
           - Une chaîne JSON: '[{"name":"Nom","label":"Votre nom","required":true}]'
           - Un objet Python: [{"name":"Nom","label":"Votre nom","required":True}]
        form_options_json: Options du formulaire (optionnel). Peut être JSON ou objet Python.
        validation_rules_json: Règles de validation (optionnel). Peut être JSON ou objet Python.
        ctx: Contexte MCP (optionnel)
        _client: Client Grist pré-configuré (pour tests, optionnel)
        
    Returns:
        Informations sur le formulaire créé
        
    Exemple:
        Pour un agent IA qui utiliserait cet outil:
        ```
        fields = [
            {"name": "Nom", "label": "Votre nom", "required": true},
            {"name": "Email", "label": "Email", "required": true},
            {"name": "Message", "label": "Votre message", "widget": "TextArea"}
        ]
        
        options = {
            "description": "Formulaire de contact",
            "success_message": "Merci pour votre message!"
        }
        
        create_grist_form("abc123", "Formulaire Contact", JSON.stringify(fields), JSON.stringify(options))
        ```
    """
    try:
        client = get_grist_client(ctx, _client)
        
        # Traitement des entrées
        try:
            raw_fields = parse_json_safely(fields_json, default=[], field_name="fields_json")
            # Nouvelle étape: validation et normalisation des champs
            fields = validate_form_fields(raw_fields, field_name="fields_json")
            logger.debug(f"Champs du formulaire validés: {len(fields)} champs")
        except Exception as e:
            logger.error(f"Erreur lors du traitement des champs: {e}")
            raise ValueError(f"Format de champs invalide: {str(e)}")
        
        # Traitement de form_options_json
        try:
            form_options = parse_json_safely(form_options_json, default=None, field_name="form_options_json")
            logger.debug(f"Options du formulaire parsées: {form_options}")
        except Exception as e:
            logger.error(f"Erreur lors du parsing des options: {e}")
            form_options = None
        
        # Traitement de validation_rules_json
        try:
            validation_rules = parse_json_safely(validation_rules_json, default=None, field_name="validation_rules_json")
            logger.debug(f"Règles de validation parsées: {validation_rules}")
        except Exception as e:
            logger.error(f"Erreur lors du parsing des règles de validation: {e}")
            validation_rules = None
        
        # Création du formulaire
        result = await create_form(
            client,
            doc_id,
            form_name,
            fields,
            form_options,
            validation_rules
        )
        
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la création du formulaire: {e}")
        raise ValueError(f"Erreur lors de la création du formulaire: {str(e)}")

async def create_grist_form_from_template(
    doc_id: str,
    form_name: str,
    template_type: str,
    custom_fields_json: Optional[str] = None,
    form_options_json: Optional[str] = None,
    ctx = None,
    _client = None
) -> Dict[str, Any]:
    """
    Crée un formulaire Grist à partir d'un template prédéfini.
    
    Args:
        doc_id: ID du document Grist
        form_name: Nom du formulaire
        template_type: Type de template (event_registration, survey, contact, application)
        custom_fields_json: JSON ou chaîne JSON des champs personnalisés à ajouter (optionnel)
        form_options_json: JSON ou chaîne JSON des options du formulaire (optionnel)
        ctx: Contexte MCP (optionnel)
        _client: Client Grist pré-configuré (pour tests, optionnel)
        
    Returns:
        Informations sur le formulaire créé
        
    Exemple:
        Pour un agent IA qui utiliserait cet outil:
        ```
        // Création d'un formulaire de type "contact" avec des champs personnalisés
        var custom_fields = [
            {"name": "Entreprise", "label": "Nom de votre entreprise", "required": true}
        ];
        
        var options = {
            "description": "Formulaire de contact professionnel",
            "success_message": "Merci de nous avoir contactés!"
        };
        
        create_grist_form_from_template(
            "abc123", 
            "Contact Pro", 
            "contact", 
            JSON.stringify(custom_fields), 
            JSON.stringify(options)
        );
        ```
    """
    try:
        client = get_grist_client(ctx, _client)
        
        # Traitement des entrées
        try:
            # Vérification du type de template
            if template_type not in FORM_TEMPLATES:
                raise ValueError(f"Type de template non reconnu: {template_type}. Disponibles: {', '.join(FORM_TEMPLATES.keys())}")
            
            # Traitement de custom_fields_json
            try:
                custom_fields = None
                if custom_fields_json:
                    custom_fields = parse_json_safely(custom_fields_json, field_name="custom_fields_json")
                    logger.debug(f"Champs personnalisés parsés: {custom_fields}")
            except Exception as e:
                logger.error(f"Erreur lors du parsing des champs personnalisés: {e}")
                custom_fields = None
            
            # Traitement de form_options_json
            try:
                form_options = None
                if form_options_json:
                    form_options = parse_json_safely(form_options_json, field_name="form_options_json")
                    logger.debug(f"Options du formulaire parsées: {form_options}")
            except Exception as e:
                logger.error(f"Erreur lors du parsing des options: {e}")
                form_options = None
            
            # Création du formulaire
            result = await create_form_from_template(
                client,
                doc_id,
                form_name,
                template_type,
                custom_fields,
                form_options
            )
            
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la création du formulaire: {e}")
            raise ValueError(f"Erreur lors de la création du formulaire: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur d'initialisation du client: {e}")
        raise ValueError(f"Erreur lors de la création du formulaire: {str(e)}")

async def get_grist_form_responses(
    doc_id: str,
    form_id: str,
    format_type: str = "records",
    include_validation: bool = False,
    ctx = None,
    _client = None
) -> Dict[str, Any]:
    """
    Récupère les réponses d'un formulaire Grist.
    
    Args:
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        format_type: Format de sortie ("records", "summary", "stats")
        include_validation: Inclure les colonnes de validation
        ctx: Contexte MCP (optionnel)
        _client: Client Grist pré-configuré (pour tests, optionnel)
        
    Returns:
        Les réponses du formulaire dans le format demandé
        
    Exemple:
        ```
        // Récupération des réponses en format résumé
        var responses = get_grist_form_responses("abc123", "Contact_Form", "summary");
        
        // Récupération des statistiques sur les réponses
        var stats = get_grist_form_responses("abc123", "Contact_Form", "stats");
        ```
    """
    try:
        client = get_grist_client(ctx, _client)
        
        result = await get_form_responses(
            client,
            doc_id,
            form_id,
            format_type,
            include_validation
        )
        
        return result
    
    except Exception as e:
        raise ValueError(f"Erreur lors de la récupération des réponses: {str(e)}")

async def get_grist_form_structure(
    doc_id: str,
    form_id: str,
    ctx = None,
    _client = None
) -> Dict[str, Any]:
    """
    Récupère la structure d'un formulaire Grist existant.
    
    Args:
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        ctx: Contexte MCP (optionnel)
        _client: Client Grist pré-configuré (pour tests, optionnel)
        
    Returns:
        La structure complète du formulaire
        
    Exemple:
        ```
        // Récupération de la structure du formulaire pour inspection ou modification
        var formStructure = get_grist_form_structure("abc123", "Contact_Form");
        
        // Analyse des champs et règles de validation
        console.log("Champs: ", formStructure.fields);
        console.log("Règles de validation: ", formStructure.validation_rules);
        ```
    """
    try:
        client = get_grist_client(ctx, _client)
        
        result = await get_form_structure(
            client,
            doc_id,
            form_id
        )
        
        return result
    
    except Exception as e:
        raise ValueError(f"Erreur lors de la récupération de la structure: {str(e)}")

async def update_grist_form(
    doc_id: str,
    form_id: str,
    fields_to_add_json: Optional[str] = None,
    fields_to_update_json: Optional[str] = None,
    fields_to_remove_json: Optional[str] = None,
    form_options_json: Optional[str] = None,
    ctx = None,
    _client = None
) -> Dict[str, Any]:
    """
    Met à jour un formulaire Grist existant.
    
    Args:
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        fields_to_add_json: JSON des nouveaux champs à ajouter
        fields_to_update_json: JSON des champs à mettre à jour
        fields_to_remove_json: JSON des noms de champs à supprimer
        form_options_json: JSON des nouvelles options de formulaire
        ctx: Contexte MCP (optionnel)
        _client: Client Grist pré-configuré (pour tests, optionnel)
        
    Returns:
        Informations sur la mise à jour effectuée
        
    Exemple:
        ```
        // Ajouter un nouveau champ
        var fieldsToAdd = [
            {"name": "Telephone", "label": "Téléphone", "required": false}
        ];
        
        // Mettre à jour un champ existant
        var fieldsToUpdate = {
            "Email": {"required": true, "label": "Email (obligatoire)"}
        };
        
        // Supprimer un champ
        var fieldsToRemove = ["CommentairesOptionnels"];
        
        // Mise à jour des options
        var options = {
            "success_message": "Merci pour votre réponse! Nous vous contacterons bientôt."
        };
        
        update_grist_form(
            "abc123",
            "Contact_Form",
            JSON.stringify(fieldsToAdd),
            JSON.stringify(fieldsToUpdate),
            JSON.stringify(fieldsToRemove),
            JSON.stringify(options)
        );
        ```
    """
    try:
        client = get_grist_client(ctx, _client)
        
        # Utiliser notre fonction de parsing sécurisé
        fields_to_add = parse_json_safely(fields_to_add_json, default=None, field_name="fields_to_add_json")
        fields_to_update = parse_json_safely(fields_to_update_json, default=None, field_name="fields_to_update_json")
        fields_to_remove = parse_json_safely(fields_to_remove_json, default=None, field_name="fields_to_remove_json")
        form_options = parse_json_safely(form_options_json, default=None, field_name="form_options_json")
        
        result = await update_form(
            client,
            doc_id,
            form_id,
            fields_to_add,
            fields_to_update,
            fields_to_remove,
            form_options
        )
        
        return result
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Erreur dans le format JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"Erreur lors de la mise à jour du formulaire: {str(e)}")

async def generate_grist_form_url(
    doc_id: str,
    form_id: str,
    is_public: bool = True,
    ctx = None,
    _client = None
) -> Dict[str, str]:
    """
    Génère l'URL d'un formulaire Grist.
    
    Args:
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        is_public: Si l'URL doit être publique
        ctx: Contexte MCP (optionnel)
        _client: Client Grist pré-configuré (pour tests, optionnel)
        
    Returns:
        L'URL du formulaire
        
    Exemple:
        ```
        // Générer une URL publique pour le formulaire
        var urlInfo = generate_grist_form_url("abc123", "Contact_Form", true);
        console.log("URL du formulaire: ", urlInfo.form_url);
        
        // Générer une URL privée (accès restreint)
        var privateUrlInfo = generate_grist_form_url("abc123", "Contact_Form", false);
        ```
    """
    try:
        client = get_grist_client(ctx, _client)
        
        url = await generate_form_url(
            client,
            doc_id,
            form_id,
            is_public
        )
        
        return {"form_url": url}
    
    except Exception as e:
        raise ValueError(f"Erreur lors de la génération de l'URL: {str(e)}")

# Pour utilisation avec MCP server
def register_form_tools(mcp_server, prefix=""):
    """
    Enregistre les outils de formulaire sur le serveur MCP
    
    Args:
        mcp_server: Instance du serveur MCP
        prefix: Préfixe optionnel à ajouter aux noms des fonctions
    """
    functions = [
        create_grist_form,
        create_grist_form_from_template,
        get_grist_form_responses,
        get_grist_form_structure,
        update_grist_form,
        generate_grist_form_url,
        get_form_help  # Ajout de la nouvelle fonction
    ]
    
    for func in functions:
        if prefix:
            # Crée un wrapper avec le préfixe
            @mcp_server.tool(name=f"{prefix}{func.__name__}")
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
        else:
            mcp_server.tool()(func)

def validate_form_fields(fields, field_name="fields"):
    """
    Valide que les champs de formulaire ont le bon format avant de les convertir en FormField.
    
    Args:
        fields: Liste de champs à valider
        field_name: Nom du champ pour les messages d'erreur
        
    Returns:
        Liste de champs validés et normalisés
    """
    if not isinstance(fields, list):
        raise ValueError(f"{field_name} doit être une liste de champs")
    
    normalized_fields = []
    required_keys = {"name", "label"}
    
    for i, field in enumerate(fields):
        if not isinstance(field, dict):
            raise ValueError(f"Champ #{i+1} doit être un objet (dictionnaire)")
        
        # Vérifier les clés requises
        missing_keys = required_keys - set(field.keys())
        if missing_keys:
            raise ValueError(f"Champ #{i+1} : clés requises manquantes: {', '.join(missing_keys)}")
        
        # Normaliser les types de données
        if "required" in field and isinstance(field["required"], str):
            field["required"] = field["required"].lower() in ("true", "1", "yes", "oui")
        
        # Vérifier que le nom est valide pour Grist (alphanumérique + underscore)
        if not re.match(r'^[a-zA-Z0-9_]+$', field["name"]):
            field["name"] = re.sub(r'[^a-zA-Z0-9_]', '_', field["name"])
            logger.warning(f"Nom de champ '{field['name']}' normalisé pour Grist (caractères spéciaux remplacés par _)")
        
        # Vérifier et normaliser le type
        if "type" in field:
            valid_types = {"Text", "Int", "Bool", "Date", "DateTime", "Choice", "ChoiceList", "Attachments", "Ref", "Numeric"}
            if field["type"] not in valid_types:
                logger.warning(f"Type de champ '{field['type']}' non reconnu, utilisation de 'Text' par défaut")
                field["type"] = "Text"
        
        normalized_fields.append(field)
    
    return normalized_fields

def validate_form_options(options, field_name="options"):
    """
    Valide et normalise les options de formulaire.
    
    Args:
        options: Options à valider (dict)
        field_name: Nom du champ pour les messages d'erreur
        
    Returns:
        Options validées et normalisées
    """
    if not isinstance(options, dict):
        raise ValueError(f"{field_name} doit être un objet (dictionnaire)")
    
    # Convertir les valeurs booléennes
    if "allow_multiple" in options and isinstance(options["allow_multiple"], str):
        options["allow_multiple"] = options["allow_multiple"].lower() in ("true", "1", "yes", "oui")
    
    # S'assurer que les champs textuels sont bien des chaînes
    for text_field in ["description", "success_message", "notification_email", "theme"]:
        if text_field in options and not isinstance(options[text_field], str):
            options[text_field] = str(options[text_field])
    
    return options

# Ajouter cette fonction pour aider les agents IA à générer des entrées JSON correctes

async def get_form_help(format_type: str = "all", ctx = None) -> Dict[str, Any]:
    """
    Renvoie des exemples d'utilisation et de la documentation sur les formulaires Grist.
    
    Args:
        format_type: Type d'aide ("fields", "options", "validation", "templates", "all")
        ctx: Contexte MCP (optionnel)
        
    Returns:
        Documentation et exemples d'utilisation
    """
    help_data = {
        "fields": {
            "description": "Structure des champs de formulaire",
            "required_props": ["name", "label"],
            "optional_props": ["type", "widget", "required", "options", "description"],
            "example": [
                {"name": "Nom", "label": "Votre nom", "required": True},
                {"name": "Email", "label": "Email", "required": True},
                {"name": "Message", "label": "Votre message", "widget": "TextArea"}
            ]
        },
        "options": {
            "description": "Options globales du formulaire",
            "props": ["description", "success_message", "allow_multiple", "notification_email", "theme"],
            "example": {
                "description": "Formulaire de contact",
                "success_message": "Merci pour votre message!",
                "allow_multiple": True
            }
        },
        "validation": {
            "description": "Règles de validation des champs",
            "rules": list(VALIDATION_FORMULAS.keys()),
            "example": {
                "Email": [
                    {"type": "email_format", "error_message": "Format d'email invalide"}
                ],
                "Age": [
                    {"type": "min_value", "params": {"min_value": 18}, "error_message": "Vous devez avoir au moins 18 ans"}
                ]
            }
        },
        "templates": {
            "description": "Templates prédéfinis de formulaires",
            "available": list(FORM_TEMPLATES.keys()),
            "example_usage": "create_grist_form_from_template('abc123', 'Inscription', 'event_registration')"
        }
    }
    
    if format_type == "all":
        return {
            "help": JSON_FORMAT_HELP,
            **help_data
        }
    elif format_type in help_data:
        return {
            "help": JSON_FORMAT_HELP,
            format_type: help_data[format_type]
        }
    else:
        return {
            "error": f"Type d'aide inconnu: {format_type}",
            "available_types": ["all", "fields", "options", "validation", "templates"]
        }

def get_grist_client(ctx=None, _client=None):
    """
    Obtient un client Grist approprié, soit à partir des arguments, soit en l'important du module principal.
    
    Args:
        ctx: Contexte MCP (optionnel)
        _client: Client Grist pré-configuré (pour tests, optionnel)
        
    Returns:
        Client Grist
    """
    # Si un client est fourni, l'utiliser directement
    if _client is not None:
        return _client
        
    # Essayer d'importer get_client depuis le module principal
    try:
        from grist_mcp_server import get_client
        client = get_client(ctx)
        logger.debug("Utilisation du client Grist du module principal")
        return client
    except ImportError:
        logger.warning("Module principal non trouvé, vérifiez si grist_mcp_server.py est accessible")
        # Créer un client mock pour les tests
        class MockClient:
            async def _request(self, method, endpoint, json_data=None, params=None):
                logger.warning(f"Appel simulé à {method} {endpoint}")
                return {"mock": True}
        return MockClient()
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du client Grist: {e}")
        raise ValueError(f"Erreur d'initialisation du client Grist: {str(e)}")