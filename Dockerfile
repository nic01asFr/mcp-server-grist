FROM python:3.10-slim

# Définir des variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV LOG_LEVEL=INFO

# Créer et définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances et installer les dépendances
COPY requirements.txt .
COPY pyproject.toml .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Exposer les ports pour les modes HTTP
EXPOSE 8000

# Définir les variables d'environnement pour la configuration de Grist
ENV GRIST_API_KEY=""
ENV GRIST_API_HOST="https://grist.numerique.gouv.fr/api"

# Point d'entrée avec support des différents modes de transport
ENTRYPOINT ["python", "-m", "grist_mcp_server"]

# Par défaut, utiliser le mode stdio
CMD ["--transport", "stdio"]

# Exemples d'utilisation du conteneur:
# Mode stdio (par défaut):
#   docker run --rm -i -e GRIST_API_KEY=your_key mcp/grist-mcp-server
# 
# Mode streamable-http:
#   docker run --rm -p 8000:8000 -e GRIST_API_KEY=your_key mcp/grist-mcp-server --transport streamable-http
#
# Mode SSE:
#   docker run --rm -p 8000:8000 -e GRIST_API_KEY=your_key mcp/grist-mcp-server --transport sse