"""
Modèles de données pour le serveur MCP Grist.

Ce module définit les modèles Pydantic utilisés pour valider et
structurer les données échangées avec l'API Grist et les clients MCP.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# Modèles pour les réponses MCP
class MCP_Response(BaseModel):
    """Format de réponse standard pour tous les outils MCP."""
    success: bool = Field(..., description="Indique si l'opération a réussi")
    message: str = Field(..., description="Message de succès ou d'erreur")


# Modèles pour les objets Grist
class GristOrgFields(BaseModel):
    """Champs d'une organisation Grist."""
    name: str = Field(..., description="Nom de l'organisation")
    domain: Optional[str] = Field(None, description="Domaine de l'organisation")
    owner: Optional[Dict[str, Any]] = Field(None, description="Propriétaire de l'organisation")
    access_token_required: Optional[bool] = Field(None, description="Indique si un token d'accès est requis")


class GristOrg(BaseModel):
    """Organisation Grist."""
    id: Union[int, str] = Field(..., description="ID de l'organisation")
    name: Optional[str] = Field(None, description="Nom de l'organisation")
    domain: Optional[str] = Field(None, description="Domaine de l'organisation")
    createdAt: Optional[Union[datetime, str]] = Field(None, description="Date de création")
    updatedAt: Optional[Union[datetime, str]] = Field(None, description="Date de mise à jour")
    fields: Optional[Dict[str, Any]] = Field(None, description="Champs supplémentaires")


class GristWorkspaceFields(BaseModel):
    """Champs d'un espace de travail Grist."""
    name: str = Field(..., description="Nom de l'espace de travail")


class GristWorkspace(BaseModel):
    """Espace de travail Grist."""
    id: int = Field(..., description="ID de l'espace de travail")
    name: Optional[str] = Field(None, description="Nom de l'espace de travail")
    org: Optional[Union[int, str]] = Field(None, description="ID de l'organisation")
    createdAt: Optional[Union[datetime, str]] = Field(None, description="Date de création")
    updatedAt: Optional[Union[datetime, str]] = Field(None, description="Date de mise à jour")
    docs: Optional[List[Dict[str, Any]]] = Field(None, description="Liste des documents")
    fields: Optional[Dict[str, Any]] = Field(None, description="Champs supplémentaires")


class GristDocumentFields(BaseModel):
    """Champs d'un document Grist."""
    name: str = Field(..., description="Nom du document")
    isPinned: Optional[bool] = Field(False, description="Indique si le document est épinglé")


class GristDocument(BaseModel):
    """Document Grist."""
    id: str = Field(..., description="ID du document")
    name: Optional[str] = Field(None, description="Nom du document")
    workspace: Optional[int] = Field(None, description="ID de l'espace de travail")
    createdAt: Optional[Union[datetime, str]] = Field(None, description="Date de création")
    updatedAt: Optional[Union[datetime, str]] = Field(None, description="Date de mise à jour")
    fields: Optional[Dict[str, Any]] = Field(None, description="Champs supplémentaires")


class GristTableFields(BaseModel):
    """Champs d'une table Grist."""
    tableId: str = Field(..., description="ID de la table")
    summarySourceTable: Optional[str] = Field(None, description="Table source pour résumé")
    primaryViewId: Optional[int] = Field(None, description="ID de la vue principale")
    onDemand: Optional[bool] = Field(False, description="Indique si la table est à la demande")


class GristTable(BaseModel):
    """Table Grist."""
    id: str = Field(..., description="ID de la table")
    fields: Optional[Dict[str, Any]] = Field(None, description="Champs de la table")


class GristColumnFields(BaseModel):
    """Champs d'une colonne Grist."""
    label: str = Field(..., description="Libellé de la colonne")
    type: str = Field(..., description="Type de données de la colonne")
    formula: Optional[str] = Field(None, description="Formule pour les colonnes calculées")
    isFormula: Optional[bool] = Field(False, description="Indique si la colonne utilise une formule")
    widgetOptions: Optional[Dict[str, Any]] = Field(None, description="Options d'affichage")


class GristColumn(BaseModel):
    """Colonne Grist."""
    id: str = Field(..., description="ID de la colonne")
    fields: Optional[Dict[str, Any]] = Field(None, description="Champs de la colonne")


class GristRecord(BaseModel):
    """Enregistrement Grist."""
    id: int = Field(..., description="ID de l'enregistrement")
    fields: Dict[str, Any] = Field(..., description="Champs de l'enregistrement")