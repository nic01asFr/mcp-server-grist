"""
Module d'intégration entre grist_form_tools et le serveur MCP.
Optimisé pour faciliter l'utilisation par les agents IA.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Union

from grist_mcp_server import get_client

from grist_form_tools import (
    create_grist_form as create_form,
    create_grist_form_from_template as create_form_from_template,
    get_grist_form_responses as get_form_responses,
    get_grist_form_structure as get_form_structure,
    update_grist_form as update_form,
    generate_grist_form_url as generate_form_url,
    parse_json_safely, get_base_url, JSON_FORMAT_HELP,
    FORM_TEMPLATES, VALIDATION_FORMULAS
)

from pydantic import BaseModel, RootModel

logger = logging.getLogger("grist_form_integration")

# Documentation d'aide améliorée avec exemples concrets pour l'agent
JSON_FORMAT_GUIDE = """
GUIDE FORMATS JSON POUR LES FORMULAIRES:
---------------------------------------

IMPORTANT: Utilisez le format JSON standard sans échappement supplémentaire.

➡️ Pour les champs de formulaire:
```json
[
  {"name": "Nom", "label": "Votre nom", "required": true},
  {"name": "Email", "label": "Email", "required": true}
]
```

➡️ Pour les options de formulaire:
```json
{
  "description": "Formulaire de contact",
  "success_message": "Merci pour votre message!"
}
```

EXEMPLE CONCRET:
--------------
Pour créer un formulaire, vous devez convertir vos objets en chaînes JSON:

```javascript
// Définition des champs
const fields = [
  {"name": "Nom", "label": "Votre nom", "required": true},
  {"name": "Email", "label": "Email", "required": true}
];

// Conversion en chaîne JSON
const fieldsJson = JSON.stringify(fields);

// Appel de l'outil avec la chaîne JSON
create_grist_form("doc_123", "Mon Formulaire", fieldsJson);
```
"""

# Définir les templates si nécessaire
FORM_TEMPLATES = {
    "contact": "Formulaire de contact",
    "survey": "Enquête de satisfaction",
    "event_registration": "Inscription à un événement",
    "application": "Formulaire de candidature"
}

# Définir les règles de validation si nécessaire
VALIDATION_FORMULAS = {
    "email_format": r"REGEX_MATCH([field], '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')",
    "required": "NOT(ISBLANK([field]))",
    "min_length": "LEN([field]) >= [min_length]",
    "max_length": "LEN([field]) <= [max_length]",
    "min_value": "[field] >= [min_value]",
    "max_value": "[field] <= [max_value]",
    "is_number": "ISNUMBER([field])"
}

def super_safe_json_parser(input_value: Any, default=None, allow_raw_objects=True) -> Any:
    """
    Parser JSON ultra-robuste qui accepte presque n'importe quel format d'entrée.
    
    Gère automatiquement:
    - Objets Python natifs (dictionnaires, listes)
    - Chaînes JSON valides
    - Chaînes JSON avec échappement
    - Chaînes booléennes ("true"/"false")
    - Chaînes numériques ("123")
    - None, undefined, null
    
    Args:
        input_value: La valeur à parser
        default: Valeur par défaut si parsing impossible
        allow_raw_objects: Accepter les objets Python non-JSON
        
    Returns:
        L'objet Python parsé ou la valeur par défaut
    """
    if input_value is None:
        return default
        
    # Si c'est déjà un dict ou une liste et qu'on accepte les objets bruts, le retourner tel quel
    if allow_raw_objects and isinstance(input_value, (dict, list)):
        logger.debug(f"Utilisation directe d'un objet Python: {type(input_value).__name__}")
        return input_value
    
    # Si c'est une chaîne
    if isinstance(input_value, str):
        # Nettoyer la chaîne
        input_str = input_value.strip()
        
        # Vérifier les valeurs spéciales
        if input_str.lower() in ("", "undefined", "null", "none"):
            return default
            
        # Vérifier les booléens
        if input_str.lower() == "true":
            return True
        if input_str.lower() == "false":
            return False
            
        # Vérifier les nombres
        if re.match(r'^-?\d+(\.\d+)?$', input_str):
            try:
                if '.' in input_str:
                    return float(input_str)
                else:
                    return int(input_str)
            except:
                pass
        
        # Tentative 1: JSON standard
        try:
            return json.loads(input_str)
        except json.JSONDecodeError:
            pass
            
        # Tentative 2: JSON avec échappement
        if input_str.startswith('"') and input_str.endswith('"'):
            try:
                inner_str = json.loads(input_str)  # Désérialiser la chaîne externe
                if isinstance(inner_str, str):
                    try:
                        return json.loads(inner_str)  # Désérialiser la chaîne interne
                    except:
                        return inner_str
            except:
                pass
                
        # Tentative 3: Remplacement des quotes simples par doubles
        if "'" in input_str and '"' not in input_str:
            try:
                fixed_str = input_str.replace("'", '"')
                return json.loads(fixed_str)
            except:
                pass
        
        # Si toutes les tentatives échouent, retourner la chaîne telle quelle
        logger.warning(f"Impossible de parser comme JSON: {input_str[:50]}...")
        return input_str
    
    # Pour les autres types, retourner tels quels
    return input_value

# Améliorations pour fonctionner avec n'importe quel format d'entrée JSON
async def create_grist_form_robust(
    doc_id: str,
    form_name: str,
    fields_json: Any,  # Accepte n'importe quel format
    form_options_json: Any = None,
    validation_rules_json: Any = None,
    debug_mode: bool = False,
    ctx = None
) -> Dict[str, Any]:
    """
    Crée un formulaire Grist avec une gestion robuste des formats d'entrée.
    
    Args:
        doc_id: ID du document Grist
        form_name: Nom du formulaire
        fields_json: Champs du formulaire (chaîne JSON, liste d'objets, ou tout format analysable)
        form_options_json: Options du formulaire (chaîne JSON, dict, ou tout format analysable)
        validation_rules_json: Règles de validation (chaîne JSON, dict, ou tout format analysable)
        debug_mode: Activer le mode debug pour voir le format des données
        ctx: Contexte MCP
        
    Returns:
        Informations sur le formulaire créé
        
    Examples:
        ```python
        # Exemple 1: Format JSON standard
        fields_json = '[{"name":"Nom","label":"Votre nom","required":true}]'
        form_options_json = '{"description":"Formulaire de contact"}'
        
        # Exemple 2: Objets Python (aussi supportés)
        fields_json = [{"name":"Nom","label":"Votre nom","required":True}]
        form_options_json = {"description":"Formulaire de contact"}
        
        result = create_grist_form_robust("abc123", "Contact", fields_json, form_options_json)
        ```
    """
    try:
        client = get_client(ctx)
        
        # Utilisation directe des objets ou parsing si besoin
        fields = super_safe_json_parser(fields_json, default=[])
        form_options = super_safe_json_parser(form_options_json, default=None)
        validation_rules = super_safe_json_parser(validation_rules_json, default=None)
        
        # Mode debug: montrer le format d'entrée pour aider au diagnostic
        if debug_mode:
            logger.info(f"Format d'entrée fields: {type(fields).__name__} = {fields}")
            logger.info(f"Format d'entrée options: {type(form_options).__name__} = {form_options}")
            
            return {
                "debug_info": {
                    "fields_input_type": type(fields_json).__name__,
                    "fields_parsed_type": type(fields).__name__,
                    "fields_parsed": fields,
                    "options_input_type": type(form_options_json).__name__,
                    "options_parsed_type": type(form_options).__name__,
                    "options_parsed": form_options
                },
                "format_guide": JSON_FORMAT_GUIDE
            }
        
        # Valider le format des champs
        if not isinstance(fields, list):
            raise ValueError(f"Les champs doivent être une liste. Reçu: {type(fields).__name__}")
        
        if len(fields) == 0:
            raise ValueError("La liste des champs ne peut pas être vide")
            
        # Vérifier que chaque champ a au moins name et label
        for i, field in enumerate(fields):
            if not isinstance(field, dict):
                raise ValueError(f"Le champ #{i+1} doit être un objet. Reçu: {type(field).__name__}")
            
            if "name" not in field:
                raise ValueError(f"Le champ #{i+1} doit avoir une propriété 'name'")
                
            if "label" not in field:
                raise ValueError(f"Le champ #{i+1} doit avoir une propriété 'label'")
        
        # Créer le formulaire
        result = await create_form(
            client,
            doc_id,
            form_name,
            fields,
            form_options,
            validation_rules
        )
        
        # Ajouter des informations utiles dans la réponse
        result["success"] = True
        result["num_fields"] = len(fields)
        
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la création du formulaire: {e}")
        # Retourner une erreur formatée avec des exemples d'aide
        return {
            "success": False,
            "error": f"Erreur: {str(e)}",
            "format_guide": JSON_FORMAT_GUIDE,
            "example": {
                "fields": [
                    {"name": "Nom", "label": "Votre nom", "required": True},
                    {"name": "Email", "label": "Email", "required": True}
                ],
                "options": {
                    "description": "Formulaire de contact",
                    "success_message": "Merci pour votre message!"
                }
            }
        }

async def create_form_from_template_wrapper(
    doc_id: str,
    form_name: str,
    template_type: str,
    custom_fields_json: Union[str, List, Dict] = None,
    form_options_json: Union[str, List, Dict] = None,
    debug_mode: bool = False,
    ctx = None
):
    """Wrapper qui accepte n'importe quel format pour les arguments JSON"""
    logger.info(f"Création de formulaire depuis template: doc={doc_id}, nom={form_name}, template={template_type}")
    
    # Vérifier directement si le template est valide
    if template_type not in FORM_TEMPLATES:
        available = list(FORM_TEMPLATES.keys())
        error_msg = f"Type de template invalide: {template_type}. Templates disponibles: {', '.join(available)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "available_templates": available
        }
    
    try:
        # Parser les données JSON
        custom_fields = super_safe_json_parser(custom_fields_json, default=[])
        form_options = super_safe_json_parser(form_options_json, default={})
        
        # Valider les champs personnalisés si présents
        if custom_fields:
            is_valid, field_errors = validate_form_fields(custom_fields)
            if not is_valid:
                return {
                    "success": False,
                    "error": "Structure des champs personnalisés invalide",
                    "field_errors": field_errors,
                    "guide": JSON_FORMAT_GUIDE
                }
                
        # Utiliser directement get_client sans l'importer à nouveau
        client = get_client(ctx) if ctx else None
        
        # Tracer les valeurs pour débogage
        if debug_mode:
            logger.info(f"Template: {template_type}")
            logger.info(f"Valeurs des champs: {custom_fields}")
            logger.info(f"Valeurs des options: {form_options}")
        
        # Appeler la fonction avec les arguments dans le bon ordre
        return await create_form_from_template(
            client,
            doc_id,
            form_name,
            template_type,
            custom_fields,
            form_options
        )
    except Exception as e:
        logger.error(f"Erreur lors de la création du formulaire depuis le template: {str(e)}")
        return {
            "success": False,
            "error": f"Erreur: {str(e)}",
            "available_templates": list(FORM_TEMPLATES.keys()),
            "format_guide": JSON_FORMAT_GUIDE,
            "example": {
                "custom_fields": [{"name": "Entreprise", "label": "Nom de votre entreprise"}],
                "options": {
                    "description": "Formulaire de contact",
                    "success_message": "Merci pour votre message!"
                }
            }
        }

async def update_form_wrapper(
    doc_id: str,
    form_id: str,
    fields_json: Union[str, List, Dict] = None,
    form_options_json: Union[str, List, Dict] = None,
    validation_rules_json: Union[str, List, Dict] = None,
    debug_mode: bool = False,
    ctx = None
):
    """Wrapper qui accepte n'importe quel format pour les arguments JSON"""
    try:
        # Parser les données JSON
        fields = super_safe_json_parser(fields_json, default=None)
        form_options = super_safe_json_parser(form_options_json, default=None)
        validation_rules = super_safe_json_parser(validation_rules_json, default=None)
        
        # Valider les champs si présents
        if fields is not None:
            is_valid, field_errors = validate_form_fields(fields)
            if not is_valid:
                return {
                    "success": False,
                    "error": "Structure des champs invalide pour la mise à jour",
                    "field_errors": field_errors,
                    "guide": JSON_FORMAT_GUIDE
                }
        
        # Tracer les valeurs pour débogage
        if debug_mode:
            if fields: logger.info(f"Valeurs des champs: {fields}")
            if form_options: logger.info(f"Valeurs des options: {form_options}")
            if validation_rules: logger.info(f"Valeurs des validations: {validation_rules}")
        
        client = get_client(ctx)
        
        return await update_form(
            client,
            doc_id,
            form_id,
            fields,
            form_options,
            validation_rules
        )
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du formulaire: {str(e)}")
        return {
            "success": False,
            "error": f"Erreur: {str(e)}",
            "format_guide": JSON_FORMAT_GUIDE
        }

async def generate_form_url_mcp(
    doc_id: str,
    form_id: str,
    is_public: bool = True,
    ctx = None
) -> Dict[str, str]:
    """
    Génère l'URL d'un formulaire Grist.
    
    Args:
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        is_public: Si l'URL doit être publique
        ctx: Contexte MCP
        
    Returns:
        L'URL du formulaire
    """
    try:
        client = get_client(ctx)
        
        url = await generate_form_url(
            client,
            doc_id,
            form_id,
            is_public
        )
        
        return {"form_url": url}
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'URL: {e}")
        return {"error": f"Erreur: {str(e)}"}

# 1. Créer des modèles Pydantic pour accepter tous les formats
class FormFieldsInput(RootModel[Union[str, List[Dict[str, Any]], None]]):
    """Modèle pour accepter différents formats de champs"""
    
    def get_value(self):
        return self.root

class FormOptionsInput(RootModel[Union[str, Dict[str, Any], None]]):
    """Modèle pour accepter différents formats d'options"""
    
    def get_value(self):
        return self.root

# 2. Créer des wrappers pour les fonctions MCP
async def create_grist_form_wrapper(
    doc_id: str,
    form_name: str,
    fields_json: Any,
    form_options_json: Any = None,
    validation_rules_json: Any = None,
    debug_mode: bool = False,
    ctx = None
):
    """Wrapper qui accepte n'importe quel format pour les arguments JSON"""
    try:
        # Parser les données JSON
        fields = super_safe_json_parser(fields_json, default=[])
        form_options = super_safe_json_parser(form_options_json, default={})
        validation_rules = super_safe_json_parser(validation_rules_json, default={})
        
        # Valider la structure des champs
        is_valid, field_errors = validate_form_fields(fields)
        if not is_valid:
            return {
                "success": False,
                "error": "Structure de champs invalide",
                "field_errors": field_errors,
                "guide": JSON_FORMAT_GUIDE,
                "example": {
                    "fields": [{"name": "Nom", "label": "Votre nom", "required": True}]
                }
            }
        
        # Tracer le format des données pour le débogage
        if debug_mode:
            logger.info(f"Valeurs des champs: {fields}")
            logger.info(f"Valeurs des options: {form_options}")
            
        # Continuer avec la création du formulaire
        client = get_client(ctx)
        
        return await create_form(
            client,
            doc_id,
            form_name,
            fields,
            form_options,
            validation_rules
        )
    except Exception as e:
        logger.error(f"Erreur lors de la création du formulaire: {str(e)}")
        return {
            "success": False,
            "error": f"Erreur: {str(e)}",
            "format_guide": JSON_FORMAT_GUIDE
        }

# 3. Mettre à jour register_form_tools_to_mcp pour utiliser les wrappers
def register_form_tools_to_mcp(mcp_server):
    """Enregistre les outils de formulaire Grist optimisés"""
    logger.info("Enregistrement des outils de formulaire Grist optimisés")
    
    # Descriptions améliorées avec exemples de format
    mcp_server.tool(
        name="create_grist_form",
        description="""
        Crée un formulaire Grist avec une gestion robuste des formats d'entrée.
        
        Args:
            doc_id: ID du document Grist
            form_name: Nom du formulaire
            fields_json: Champs du formulaire (chaîne JSON, liste d'objets, ou tout format analysable)
            form_options_json: Options du formulaire (chaîne JSON, dict, ou tout format analysable)
            validation_rules_json: Règles de validation (chaîne JSON, dict, ou tout format analysable)
            debug_mode: Activer le mode debug pour voir le format des données
            ctx: Contexte MCP
            
        Returns:
            Informations sur le formulaire créé
            
        Examples:
            ```python
            # Exemple 1: Format JSON standard
            fields_json = '[{"name":"Nom","label":"Votre nom","required":true}]'
            form_options_json = '{"description":"Formulaire de contact"}'
            
            # Exemple 2: Objets Python (aussi supportés)
            fields_json = [{"name":"Nom","label":"Votre nom","required":True}]
            form_options_json = {"description":"Formulaire de contact"}
            
            result = create_grist_form("abc123", "Contact", fields_json, form_options_json)
            ```
        """
    )(create_grist_form_wrapper)
    
    mcp_server.tool(
        name="create_grist_form_from_template",
        description="""
        Crée un formulaire Grist à partir d'un template avec gestion robuste des formats.
        
        Args:
            doc_id: ID du document Grist
            form_name: Nom du formulaire
            template_type: Type de template (event_registration, survey, contact, application)
            custom_fields_json: Champs personnalisés (tout format accepté)
            form_options_json: Options du formulaire (tout format accepté)
            debug_mode: Activer le mode debug pour voir le format des données
            ctx: Contexte MCP
            
        Returns:
            Informations sur le formulaire créé
            
        Examples:
            ```python
            # Exemple avec chaîne JSON
            custom_fields = '[{"name":"Entreprise","label":"Nom de votre entreprise"}]'
            
            # Exemple avec objet Python
            custom_fields = [{"name":"Entreprise","label":"Nom de votre entreprise"}]
            
            result = create_grist_form_from_template(
                "abc123", 
                "Contact Pro", 
                "contact",     # Type de template valide
                custom_fields
            )
            ```
        """
    )(create_form_from_template_wrapper)
    
    mcp_server.tool(
        name="update_grist_form",
        description="""
        Met à jour un formulaire Grist existant avec gestion robuste des formats.
        
        Args:
            doc_id: ID du document Grist
            form_id: ID du formulaire à mettre à jour
            fields_json: Nouveaux champs (tout format accepté)
            form_options_json: Nouvelles options (tout format accepté)
            validation_rules_json: Nouvelles règles de validation (tout format accepté)
            debug_mode: Activer le mode debug
            ctx: Contexte MCP
            
        Returns:
            Informations sur le formulaire mis à jour
            
        Examples:
            ```python
            # Mise à jour des options du formulaire
            options = {"description":"Nouveau formulaire de contact mis à jour"}
            
            result = update_grist_form("abc123", "form1", form_options_json=options)
            ```
        """
    )(update_form_wrapper)
    
    # Descriptions améliorées pour les autres outils
    mcp_server.tool(
        name="get_grist_form_responses",
        description="Récupère les réponses d'un formulaire Grist. Args: doc_id, form_id, format_type ('records', 'summary', 'stats')"
    )(get_form_responses_mcp)
    
    mcp_server.tool(
        name="get_grist_form_structure",
        description="Récupère la structure complète d'un formulaire Grist. Args: doc_id, form_id"
    )(get_form_structure_mcp)
    
    mcp_server.tool(
        name="generate_grist_form_url",
        description="Génère l'URL publique ou privée d'un formulaire Grist. Args: doc_id, form_id, is_public (True/False)"
    )(generate_form_url_mcp)
    
    mcp_server.tool(
        name="get_grist_form_help",
        description="""
        Fournit de l'aide et des exemples sur l'utilisation des formulaires Grist.
        
        Args:
            help_type: Type d'aide ("fields", "options", "validation", "templates", "examples", "all")
            
        Returns:
            Documentation d'aide et exemples
        """
    )(get_form_help_mcp)
    
    mcp_server.tool(
        name="debug_grist_form_input",
        description="""
        Outil de débogage qui analyse un JSON et indique comment il sera traité.
        Utile pour tester si votre format JSON sera correctement interprété.
        
        Args:
            input_json: JSON à analyser (tout format)
            
        Returns:
            Résultat du parsing et informations de débogage
        """
    )(debug_grist_form_input)
    
    logger.info("Outils de formulaire Grist optimisés enregistrés avec succès")

async def get_form_responses_mcp(
    doc_id: str,
    form_id: str,
    format_type: str = "records",
    include_validation: bool = False,
    ctx = None
) -> Dict[str, Any]:
    """
    Récupère les réponses d'un formulaire Grist.
    
    Args:
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        format_type: Format de sortie ("records", "summary", "stats")
        include_validation: Inclure les colonnes de validation
        ctx: Contexte MCP
        
    Returns:
        Les réponses du formulaire dans le format demandé
    """
    try:
        client = get_client(ctx)
        
        return await get_form_responses(
            client,
            doc_id,
            form_id,
            format_type,
            include_validation
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réponses: {e}")
        return {"error": f"Erreur: {str(e)}"}

async def get_form_structure_mcp(
    doc_id: str,
    form_id: str,
    ctx = None
) -> Dict[str, Any]:
    """
    Récupère la structure d'un formulaire Grist existant.
    
    Args:
        doc_id: ID du document Grist
        form_id: ID du formulaire (table)
        ctx: Contexte MCP
        
    Returns:
        La structure complète du formulaire
    """
    try:
        client = get_client(ctx)
        
        return await get_form_structure(
            client,
            doc_id,
            form_id
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la structure: {e}")
        return {"error": f"Erreur: {str(e)}"}

async def get_form_help_mcp(
    help_type: str = "all",
    ctx = None
) -> Dict[str, Any]:
    """
    Fournit de l'aide et des exemples pour l'utilisation des outils de formulaire.
    
    Args:
        help_type: Type d'aide demandée ("fields", "options", "validation", 
                  "templates", "examples", "all")
        ctx: Contexte MCP
        
    Returns:
        Aide et exemples formatés
    """
    help_data = {
        "format_examples": JSON_FORMAT_GUIDE,
        "fields": {
            "description": "Structure des champs de formulaire",
            "required_props": ["name", "label"],
            "optional_props": ["type", "widget", "required", "options", "description"],
            "examples": [
                {"name": "Nom", "label": "Votre nom", "required": True},
                {"name": "Email", "label": "Email", "required": True},
                {"name": "Message", "label": "Votre message", "widget": "TextArea"}
            ],
            "json_example": '[{"name":"Nom","label":"Votre nom","required":true}]'
        },
        "options": {
            "description": "Options globales du formulaire",
            "props": ["description", "success_message", "allow_multiple", "notification_email", "theme"],
            "example": {
                "description": "Formulaire de contact",
                "success_message": "Merci pour votre message!",
                "allow_multiple": True
            },
            "json_example": '{"description":"Formulaire de contact","success_message":"Merci!"}'
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
        },
        "examples": {
            "create_simple_form": {
                "description": "Créer un formulaire de contact simple",
                "code": """
                // Préparer les champs
                var fields = [
                    {"name": "Nom", "label": "Votre nom", "required": true},
                    {"name": "Email", "label": "Email", "required": true},
                    {"name": "Message", "label": "Message", "widget": "TextArea"}
                ];
                
                // Préparer les options
                var options = {
                    "description": "Formulaire de contact",
                    "success_message": "Merci pour votre message!"
                };
                
                // Créer le formulaire
                create_grist_form(
                    "abc123",  // ID du document
                    "Contact", // Nom du formulaire
                    JSON.stringify(fields),
                    JSON.stringify(options)
                );
                """
            },
            "create_form_with_template": {
                "description": "Créer un formulaire à partir d'un template",
                "code": """
                // Utiliser le template 'contact' avec un champ personnalisé
                var custom_fields = [
                    {"name": "Entreprise", "label": "Nom de votre entreprise"}
                ];
                
                create_grist_form_from_template(
                    "abc123",      // ID du document
                    "Contact Pro", // Nom du formulaire
                    "contact",     // Type de template
                    JSON.stringify(custom_fields)
                );
                """
            }
        }
    }
    
    if help_type == "all":
        return help_data
    elif help_type in help_data:
        return {help_type: help_data[help_type]}
    else:
        return {
            "error": f"Type d'aide inconnu: {help_type}",
            "available_types": list(help_data.keys())
        }

async def debug_grist_form_input(input_json: Any, ctx=None) -> Dict[str, Any]:
    """
    Outil de débogage pour tester le parsing JSON.
    
    Args:
        input_json: JSON à analyser (tout format)
        ctx: Contexte MCP (non utilisé)
        
    Returns:
        Résultats du parsing et informations de débogage
    """
    try:
        parsed = super_safe_json_parser(input_json)
        
        return {
            "parsed": parsed,
            "original_type": type(input_json).__name__,
            "guide": JSON_FORMAT_GUIDE
        }
    except Exception as e:
        return {
            "error": f"Erreur lors du parsing: {str(e)}",
            "original": input_json,
            "original_type": type(input_json).__name__
        }

def validate_form_fields(fields, return_errors=True):
    """
    Valide que les champs de formulaire ont une structure correcte.
    
    Args:
        fields: Liste de champs parsée
        return_errors: Si True, retourne les erreurs détaillées
        
    Returns:
        (bool, list) - (est_valide, liste_erreurs)
    """
    if not isinstance(fields, list):
        return False, ["Les champs doivent être une liste"]
        
    errors = []
    
    for i, field in enumerate(fields):
        if not isinstance(field, dict):
            errors.append(f"Le champ #{i+1} doit être un objet")
            continue
            
        # Vérifier les propriétés obligatoires
        for prop in ["name", "label"]:
            if prop not in field:
                errors.append(f"Le champ #{i+1} doit avoir une propriété '{prop}'")
        
        # Vérifier les types
        if "type" in field and field["type"] not in ["Text", "Choice", "Numeric", "Date", "Checkbox", "choice", "numeric", "date", "checkbox", "text"]:
            errors.append(f"Le champ #{i+1} a un type invalide: {field['type']}")
            
        # Vérifier les choix pour les champs de type choix
        if ("type" in field and field["type"].lower() == "choice") and "choices" not in field:
            errors.append(f"Le champ #{i+1} est de type Choice mais n'a pas de liste de choix")
    
    return len(errors) == 0, errors
