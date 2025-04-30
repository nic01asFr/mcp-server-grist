"""
MCP Tool pour créer facilement des commandes de Noël dans Grist
"""

import os
import logging
import json
import datetime
from typing import Dict, Any, List, Optional, Union

# Configuration du logging
logger = logging.getLogger("christmas_order_tool")

# Configuration
DOC_ID = "w7mifgMvYQUAXxzwgmvUV7"  # ID du document contenant la table Commandes_Noel
TABLE_ID = "Commandes_Noel"        # ID de la table

# Types de commandes disponibles
TYPES_COMMANDE = [
    "🎁 Cadeau simple",
    "🎮 Jouet électronique",
    "📚 Livre/Culture",
    "🧸 Peluche/Doudou",
    "🚲 Jeu d'extérieur",
    "🎨 Activité créative"
]

# Statuts de commande
STATUTS_COMMANDE = [
    "📝 Lettre reçue",
    "👀 En cours d'étude",
    "🏭 En fabrication",
    "✨ En test qualité",
    "🎁 Prêt pour emballage",
    "🛷 Prêt pour livraison",
    "🎄 Livré"
]

# Zones de livraison
ZONES_LIVRAISON = [
    "🏔️ Pôle Nord",
    "🌍 Europe",
    "🌎 Amériques",
    "🌏 Asie-Pacifique",
    "🌍 Afrique"
]

# Délais de livraison
DELAIS_LIVRAISON = [
    "🚨 Urgent",
    "Normal"
]

# Moyens de transport
MOYENS_TRANSPORT = [
    "🛷 Traîneau standard",
    "✈️ Traîneau supersonique",
    "🚁 Mini-traîneau héliporté",
    "🦌 Renne solo"
]

# Équipes de lutins
EQUIPES_LUTINS = [
    "🧪 Atelier test qualité",
    "🎮 Atelier high-tech",
    "📚 Atelier culture",
    "🔨 Atelier jouets bois",
    "🎨 Atelier créatif",
    "🧸 Atelier peluches"
]

# Niveaux de sagesse
NIVEAUX_SAGESSE = [
    "😇 Très sage",
    "😊 Sage",
    "😐 Quelques bêtises",
    "😅 À surveiller"
]

# Priorités de livraison
PRIORITES_LIVRAISON = [
    "⭐ Ultra prioritaire (enfants malades)",
    "🌟 Très prioritaire (bonnes actions)",
    "✨ Priorité normale",
    "💫 Non urgent"
]

# Fonctions helper
def format_date(date_str: Optional[str] = None) -> int:
    """Convertit une date au format YYYY-MM-DD en timestamp Unix (minuit)"""
    if not date_str:
        # Utiliser la date du jour
        return int(datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    except ValueError:
        logger.error(f"Format de date invalide: {date_str}. Utilisation de la date actuelle.")
        return int(datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

async def get_next_id(client) -> int:
    """Récupère le prochain ID de commande disponible"""
    try:
        records = await client.list_records(
            doc_id=DOC_ID,
            table_id=TABLE_ID,
            sort="-id_commande",
            limit=1
        )
        
        if records and len(records) > 0:
            max_id = records[0].fields.get("id_commande", 0)
            return max_id + 1
        return 1
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du prochain ID: {e}")
        return 999  # Valeur par défaut en cas d'erreur

# Fonction d'initialisation qui sera appelée par le module principal
def init_christmas_tools(mcp, get_client_func):
    """
    Initialise les outils de commandes de Noël
    
    Args:
        mcp: L'objet FastMCP principal
        get_client_func: La fonction pour obtenir un client Grist
    """
    logger.info("Initialisation des outils de commandes de Noël")
    
    @mcp.tool()
    async def create_christmas_order(
        nom_enfant: str,
        type_commande: str,
        zone_livraison: str,
        niveau_sagesse: str,
        lutin_responsable: Optional[str] = None,
        delai_livraison: Optional[str] = "Normal",
        points_bonus: Optional[int] = 0,
        budget_matieres: Optional[int] = 100,
        budget_lutins: Optional[int] = 50,
        notes: Optional[str] = "",
        ctx = None
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle commande de Noël dans le système du Père Noël.
        
        Args:
            nom_enfant: Nom complet de l'enfant
            type_commande: Type de cadeau demandé
            zone_livraison: Zone géographique de livraison
            niveau_sagesse: Niveau de sagesse de l'enfant
            lutin_responsable: Lutin assigné à la fabrication (optionnel)
            delai_livraison: Urgence de la commande (optionnel)
            points_bonus: Points de bonus pour bonnes actions (optionnel)
            budget_matieres: Budget alloué aux matières premières (optionnel)
            budget_lutins: Budget alloué au temps des lutins (optionnel)
            notes: Notes supplémentaires sur la commande (optionnel)
            
        Returns:
            Informations sur la commande créée
        """
        logger.info(f"Création d'une nouvelle commande de Noël pour: {nom_enfant}")
        
        # Validation des données
        if not nom_enfant or not type_commande or not zone_livraison or not niveau_sagesse:
            return {
                "success": False,
                "message": "Les champs obligatoires ne peuvent pas être vides",
                "required_fields": ["nom_enfant", "type_commande", "zone_livraison", "niveau_sagesse"]
            }
        
        # Validation des choix
        if type_commande not in TYPES_COMMANDE:
            return {
                "success": False,
                "message": f"Type de commande invalide: {type_commande}. Valeurs possibles: {', '.join(TYPES_COMMANDE)}"
            }
        
        if zone_livraison not in ZONES_LIVRAISON:
            return {
                "success": False,
                "message": f"Zone de livraison invalide: {zone_livraison}. Valeurs possibles: {', '.join(ZONES_LIVRAISON)}"
            }
        
        if niveau_sagesse not in NIVEAUX_SAGESSE:
            return {
                "success": False,
                "message": f"Niveau de sagesse invalide: {niveau_sagesse}. Valeurs possibles: {', '.join(NIVEAUX_SAGESSE)}"
            }
        
        if delai_livraison not in DELAIS_LIVRAISON:
            return {
                "success": False,
                "message": f"Délai de livraison invalide: {delai_livraison}. Valeurs possibles: {', '.join(DELAIS_LIVRAISON)}"
            }
        
        try:
            # Récupération du client Grist
            client = get_client_func(ctx)
            
            # Récupération du prochain ID de commande
            next_id = await get_next_id(client)
            
            # Date actuelle pour la réception et la mise à jour
            today = format_date()
            
            # Déterminer l'équipe de lutins en fonction du type de commande
            equipe_lutins = None
            if "Jouet électronique" in type_commande:
                equipe_lutins = "🎮 Atelier high-tech"
            elif "Livre/Culture" in type_commande:
                equipe_lutins = "📚 Atelier culture"
            elif "Jeu d'extérieur" in type_commande:
                equipe_lutins = "🔨 Atelier jouets bois"
            elif "Peluche/Doudou" in type_commande:
                equipe_lutins = "🧸 Atelier peluches"
            elif "Activité créative" in type_commande:
                equipe_lutins = "🎨 Atelier créatif"
            else:
                equipe_lutins = "🧪 Atelier test qualité"
            
            # Priorité en fonction du niveau de sagesse
            priorite_livraison = "✨ Priorité normale"
            if niveau_sagesse == "😇 Très sage":
                priorite_livraison = "🌟 Très prioritaire (bonnes actions)"
            elif niveau_sagesse == "😅 À surveiller":
                priorite_livraison = "💫 Non urgent"
            
            # Préparation des données
            new_record = {
                "id_commande": next_id,
                "nom_enfant": nom_enfant,
                "type_commande": type_commande,
                "statut_commande": "📝 Lettre reçue",  # Statut initial
                "date_reception": today,
                "date_maj": today,
                "zone_livraison": zone_livraison,
                "delai_livraison": delai_livraison,
                "moyen_transport": "🛷 Traîneau standard",  # Valeur par défaut
                "equipe_lutins": equipe_lutins,
                "lutin_responsable": lutin_responsable or "",
                "lutin_assistant": "",
                "renne_assigne": False,
                "budget_matieres": budget_matieres,
                "budget_lutins": budget_lutins,
                "notes_budget": notes,
                "alerte_budget": "",
                "niveau_sagesse": niveau_sagesse,
                "points_bonus": points_bonus,
                "priorite_livraison": priorite_livraison
            }
            
            # Appel à l'API Grist pour ajouter l'enregistrement
            record_ids = await client.add_records(DOC_ID, TABLE_ID, [new_record])
            
            if record_ids and len(record_ids) > 0:
                return {
                    "success": True,
                    "message": f"Commande de Noël créée avec succès pour {nom_enfant}",
                    "order_id": next_id,
                    "record_id": record_ids[0],
                    "status": "📝 Lettre reçue",
                    "details": new_record
                }
            else:
                return {
                    "success": False,
                    "message": "Erreur lors de la création de la commande: aucun ID retourné",
                    "attempted_data": new_record
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de la création de la commande: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la création de la commande: {str(e)}"
            }

    @mcp.tool()
    async def update_christmas_order_status(
        id_commande: int,
        statut_commande: str,
        lutin_responsable: Optional[str] = None,
        notes: Optional[str] = None,
        ctx = None
    ) -> Dict[str, Any]:
        """
        Met à jour le statut d'une commande de Noël existante.
        
        Args:
            id_commande: ID de la commande à mettre à jour
            statut_commande: Nouveau statut de la commande
            lutin_responsable: Lutin responsable (optionnel)
            notes: Notes à ajouter (optionnel)
            
        Returns:
            Informations sur la mise à jour
        """
        logger.info(f"Mise à jour du statut de la commande {id_commande} vers {statut_commande}")
        
        # Validation du statut
        if statut_commande not in STATUTS_COMMANDE:
            return {
                "success": False,
                "message": f"Statut de commande invalide: {statut_commande}. Valeurs possibles: {', '.join(STATUTS_COMMANDE)}"
            }
        
        try:
            # Récupération du client Grist
            client = get_client_func(ctx)
            
            # Recherche de la commande existante
            filter_data = {"id_commande": [id_commande]}
            
            records = await client.list_records(
                doc_id=DOC_ID,
                table_id=TABLE_ID,
                filter_data=filter_data
            )
            
            if not records or len(records) == 0:
                return {
                    "success": False,
                    "message": f"Aucune commande trouvée avec l'ID: {id_commande}"
                }
            
            # Récupération de l'enregistrement existant
            record_id = records[0].id
            existing_data = records[0].fields
            
            # Préparation des données à mettre à jour
            update_data = {
                "id": record_id,
                "fields": {
                    "statut_commande": statut_commande,
                    "date_maj": format_date()
                }
            }
            
            # Ajout des champs optionnels
            if lutin_responsable:
                update_data["fields"]["lutin_responsable"] = lutin_responsable
            
            if notes:
                # Si des notes existent déjà, les ajouter aux nouvelles
                existing_notes = existing_data.get("notes_budget", "")
                if existing_notes:
                    update_data["fields"]["notes_budget"] = f"{existing_notes}\n{notes}"
                else:
                    update_data["fields"]["notes_budget"] = notes
            
            # Mise à jour automatique du renne assigné pour les commandes prêtes à livrer
            if statut_commande == "🛷 Prêt pour livraison":
                update_data["fields"]["renne_assigne"] = True
            
            # Appel à l'API Grist pour mettre à jour l'enregistrement
            updated_ids = await client.update_records(DOC_ID, TABLE_ID, [update_data])
            
            if updated_ids and len(updated_ids) > 0:
                return {
                    "success": True,
                    "message": f"Statut de la commande {id_commande} mis à jour avec succès vers '{statut_commande}'",
                    "order_id": id_commande,
                    "record_id": record_id,
                    "new_status": statut_commande,
                    "updated_fields": update_data["fields"]
                }
            else:
                return {
                    "success": False,
                    "message": "Erreur lors de la mise à jour de la commande: aucun ID retourné",
                    "attempted_data": update_data
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la commande: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la mise à jour de la commande: {str(e)}"
            }

    @mcp.tool()
    async def quick_create_christmas_order(
        nom_enfant: str,
        type_cadeau: str,
        region: str = "Europe",
        sagesse: str = "Sage",
        urgence: bool = False,
        ctx = None
    ) -> Dict[str, Any]:
        """
        Crée rapidement une commande de Noël avec un minimum d'informations.
        
        Args:
            nom_enfant: Nom de l'enfant
            type_cadeau: Description simple du cadeau
            region: Région de livraison (par défaut: Europe)
            sagesse: Niveau de sagesse (par défaut: Sage)
            urgence: Si la commande est urgente (par défaut: False)
            
        Returns:
            Informations sur la commande créée
        """
        logger.info(f"Création rapide d'une commande pour {nom_enfant}: {type_cadeau}")
        
        # Mappage rapide des types de cadeaux
        type_commande = "🎁 Cadeau simple"
        if "livre" in type_cadeau.lower() or "culture" in type_cadeau.lower():
            type_commande = "📚 Livre/Culture"
        elif "électronique" in type_cadeau.lower() or "jeu vidéo" in type_cadeau.lower() or "console" in type_cadeau.lower():
            type_commande = "🎮 Jouet électronique"
        elif "peluche" in type_cadeau.lower() or "doudou" in type_cadeau.lower():
            type_commande = "🧸 Peluche/Doudou"
        elif "vélo" in type_cadeau.lower() or "extérieur" in type_cadeau.lower() or "sport" in type_cadeau.lower():
            type_commande = "🚲 Jeu d'extérieur"
        elif "créa" in type_cadeau.lower() or "art" in type_cadeau.lower() or "dessin" in type_cadeau.lower():
            type_commande = "🎨 Activité créative"
        
        # Mappage des régions
        zone_livraison = "🌍 Europe"
        if "afrique" in region.lower():
            zone_livraison = "🌍 Afrique"
        elif "amérique" in region.lower():
            zone_livraison = "🌎 Amériques"
        elif "asie" in region.lower() or "pacifique" in region.lower():
            zone_livraison = "🌏 Asie-Pacifique"
        elif "pôle" in region.lower() or "pole" in region.lower() or "nord" in region.lower():
            zone_livraison = "🏔️ Pôle Nord"
        
        # Mappage des niveaux de sagesse
        niveau_sagesse = "😊 Sage"
        if "très" in sagesse.lower() and "sage" in sagesse.lower():
            niveau_sagesse = "😇 Très sage"
        elif "bêtise" in sagesse.lower() or "betise" in sagesse.lower():
            niveau_sagesse = "😐 Quelques bêtises"
        elif "surveiller" in sagesse.lower() or "attention" in sagesse.lower():
            niveau_sagesse = "😅 À surveiller"
        
        # Délai de livraison
        delai_livraison = "🚨 Urgent" if urgence else "Normal"
        
        # Utilisation de l'outil principal
        return await create_christmas_order(
            nom_enfant=nom_enfant,
            type_commande=type_commande,
            zone_livraison=zone_livraison,
            niveau_sagesse=niveau_sagesse,
            delai_livraison=delai_livraison,
            points_bonus=3 if niveau_sagesse == "😇 Très sage" else 1,
            budget_matieres=150,
            budget_lutins=100,
            notes=f"Commande créée rapidement pour {type_cadeau}",
            ctx=ctx
        )

    @mcp.tool()
    async def get_christmas_orders_summary(ctx = None) -> Dict[str, Any]:
        """
        Obtient un résumé des commandes de Noël en cours.
        
        Returns:
            Résumé des commandes par statut et zone
        """
        logger.info("Récupération du résumé des commandes de Noël")
        
        try:
            # Récupération du client Grist
            client = get_client_func(ctx)
            
            records = await client.list_records(
                doc_id=DOC_ID,
                table_id=TABLE_ID
            )
            
            if not records:
                return {
                    "success": True,
                    "message": "Aucune commande trouvée",
                    "total_orders": 0
                }
            
            # Comptage des commandes par statut
            status_counts = {}
            zone_counts = {}
            type_counts = {}
            total_budget = 0
            
            for record in records:
                fields = record.fields
                
                # Comptage par statut
                status = fields.get("statut_commande", "Inconnu")
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Comptage par zone
                zone = fields.get("zone_livraison", "Inconnu")
                zone_counts[zone] = zone_counts.get(zone, 0) + 1
                
                # Comptage par type
                type_cmd = fields.get("type_commande", "Inconnu")
                type_counts[type_cmd] = type_counts.get(type_cmd, 0) + 1
                
                # Budget total
                budget = fields.get("budget_total", "0")
                try:
                    total_budget += float(budget)
                except (ValueError, TypeError):
                    pass
            
            return {
                "success": True,
                "message": f"Résumé de {len(records)} commandes de Noël",
                "total_orders": len(records),
                "by_status": status_counts,
                "by_zone": zone_counts,
                "by_type": type_counts,
                "total_budget": total_budget
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé des commandes: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la récupération du résumé: {str(e)}"
            }
    
    logger.info("Outils de commandes de Noël enregistrés avec succès")
    return {
        "create_christmas_order": create_christmas_order,
        "update_christmas_order_status": update_christmas_order_status,
        "quick_create_christmas_order": quick_create_christmas_order,
        "get_christmas_orders_summary": get_christmas_orders_summary
    }
