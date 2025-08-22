#!/usr/bin/env python3
"""
Script pour exécuter tous les tests du MCP Server Grist.
"""
import unittest
import sys
import os
import argparse

# Ajouter le répertoire parent au chemin pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_tests(test_type=None, verbosity=2):
    """
    Exécute les tests spécifiés.
    
    Args:
        test_type: Le type de tests à exécuter ('unit', 'integration', 'all')
        verbosity: Niveau de détail des rapports de test (1=minimal, 2=normal, 3=détaillé)
    """
    if test_type == 'unit':
        # Exécuter uniquement les tests unitaires
        test_suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py', top_level_dir='tests')
        # Exclure les tests d'intégration
        filtered_suite = unittest.TestSuite()
        for suite in test_suite:
            for test in suite:
                if 'test_integration' not in str(test):
                    filtered_suite.addTest(test)
        unittest.TextTestRunner(verbosity=verbosity).run(filtered_suite)
    
    elif test_type == 'integration':
        # Exécuter uniquement les tests d'intégration
        test_suite = unittest.defaultTestLoader.discover('.', pattern='test_integration.py', top_level_dir='tests')
        unittest.TextTestRunner(verbosity=verbosity).run(test_suite)
    
    else:  # 'all'
        # Exécuter tous les tests
        test_suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py', top_level_dir='tests')
        unittest.TextTestRunner(verbosity=verbosity).run(test_suite)

if __name__ == '__main__':
    # Configurer les arguments de ligne de commande
    parser = argparse.ArgumentParser(description='Exécuter les tests pour le MCP Server Grist.')
    parser.add_argument(
        '--type',
        choices=['unit', 'integration', 'all'],
        default='all',
        help='Type de tests à exécuter (unit, integration, all)'
    )
    parser.add_argument(
        '--verbosity',
        type=int,
        choices=[1, 2, 3],
        default=2,
        help='Niveau de détail des rapports de test (1=minimal, 2=normal, 3=détaillé)'
    )
    
    args = parser.parse_args()
    
    # Exécuter les tests
    run_tests(args.type, args.verbosity)
