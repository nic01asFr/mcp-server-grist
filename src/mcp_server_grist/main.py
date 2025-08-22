"""
Point d'entrée principal du serveur MCP Grist.

Ce module contient la fonction main() qui analyse les arguments
de la ligne de commande et lance le serveur MCP avec le transport approprié.
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Dict, Optional, Union

from .server import create_mcp_server

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")


def parse_args():
    """
    Analyse les arguments de la ligne de commande.
    
    Returns:
        Les arguments analysés.
    """
    parser = argparse.ArgumentParser(description='Serveur MCP pour l\'API Grist')
    
    # Options de transport
    parser.add_argument(
        '--transport',
        choices=['stdio', 'streamable-http', 'sse'],
        default='stdio',
        help='Type de transport à utiliser (default: stdio)'
    )
    
    # Options pour les transports HTTP
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Hôte pour les transports HTTP (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port pour les transports HTTP (default: 8000)'
    )
    
    # Options spécifiques aux différents transports HTTP
    parser.add_argument(
        '--path',
        default='/mcp',
        help='Chemin pour streamable-http (default: /mcp)'
    )
    parser.add_argument(
        '--mount-path',
        default='/sse',
        help='Chemin pour SSE (default: /sse)'
    )
    
    # Autres options
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Active le mode debug'
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Fonction principale qui démarre le serveur MCP.
    
    Cette fonction analyse les arguments, initialise le serveur MCP
    et le lance avec le transport spécifié. Elle prend en charge
    les transports stdio, streamable-http et sse (déprécié).
    
    Returns:
        Code de sortie : 0 en cas de succès, autre valeur en cas d'erreur.
    """
    args = parse_args()
    
    try:
        # Récupérer les paramètres MCP depuis l'environnement
        parameters = {}
        if os.environ.get("MCP_PARAMETERS"):
            import json
            try:
                parameters = json.loads(os.environ.get("MCP_PARAMETERS", "{}"))
            except json.JSONDecodeError:
                logger.warning("Impossible de décoder les paramètres MCP")
        
        # Créer le serveur MCP
        mcp = create_mcp_server(debug=args.debug, parameters=parameters)
        
        # Configurer et lancer le transport approprié
        if args.transport == 'stdio':
            logger.info("Démarrage du serveur MCP avec transport stdio")
            asyncio.run(mcp.run())
            return 0
        
        elif args.transport == 'streamable-http':
            # Avertissement de sécurité pour 0.0.0.0
            if args.host == '0.0.0.0':
                logger.warning(
                    "AVERTISSEMENT DE SÉCURITÉ: Utilisation de host='0.0.0.0'. "
                    "Cela expose le serveur à tous les réseaux. "
                    "Utilisez '127.0.0.1' pour limiter l'accès au localhost."
                )
            
            logger.info(
                f"Démarrage du serveur MCP avec transport streamable-http "
                f"sur {args.host}:{args.port}{args.path}"
            )
            asyncio.run(mcp.run(
                transport="streamable-http",
                host=args.host,
                port=args.port,
                path=args.path
                # validate_origin n'est pas supporté dans cette version de FastMCP
            ))
            return 0
        
        elif args.transport == 'sse':
            # Avertissement de dépréciation pour SSE
            logger.warning(
                "Le transport SSE est déprécié selon les dernières spécifications MCP. "
                "Envisagez d'utiliser streamable-http à la place."
            )
            
            # Avertissement de sécurité pour 0.0.0.0
            if args.host == '0.0.0.0':
                logger.warning(
                    "AVERTISSEMENT DE SÉCURITÉ: Utilisation de host='0.0.0.0'. "
                    "Cela expose le serveur à tous les réseaux. "
                    "Utilisez '127.0.0.1' pour limiter l'accès au localhost."
                )
            
            logger.info(
                f"Démarrage du serveur MCP avec transport SSE (déprécié) "
                f"sur {args.host}:{args.port}{args.mount_path}"
            )
            asyncio.run(mcp.run(
                transport="sse",
                host=args.host,
                port=args.port,
                mount_path=args.mount_path
                # validate_origin n'est pas supporté dans cette version de FastMCP
            ))
            return 0
        
        else:
            logger.error(f"Transport non pris en charge: {args.transport}")
            return 1
        
    except KeyboardInterrupt:
        logger.info("Arrêt du serveur MCP (interruption clavier)")
        return 0
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du serveur MCP: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())