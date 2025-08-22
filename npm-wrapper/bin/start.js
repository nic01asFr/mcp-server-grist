#!/usr/bin/env node

const { spawn } = require('child_process');

// Fonction pour envoyer des messages formatés en JSON
function logMessage(level, message, metadata = {}) {
  // Format compatible avec le protocole MCP
  const logObj = {
    jsonrpc: "2.0",
    method: "log",
    params: {
      level,
      message,
      metadata
    }
  };
  
  // Envoyer en tant que JSON sur stderr pour éviter de perturber le protocole MCP
  console.error(JSON.stringify(logObj));
}

// Utiliser les fonctions de log formatées
logMessage("info", "Démarrage du serveur MCP Grist...");

// Vérifier que les variables d'environnement nécessaires sont définies
if (!process.env.GRIST_API_KEY) {
  logMessage("error", "La variable d'environnement GRIST_API_KEY n'est pas définie. Définissez-la dans la configuration MCP de Claude Desktop.");
  process.exit(1);
}

// Utiliser l'URL par défaut si non spécifiée
const apiUrl = process.env.GRIST_API_URL || 'https://docs.getgrist.com/api';

// Préparer l'environnement pour le processus Python
const env = {
  ...process.env,
  GRIST_API_KEY: process.env.GRIST_API_KEY,
  GRIST_API_URL: apiUrl
};

// Lancer le serveur Python directement avec le transport stdio
logMessage("info", "Démarrage du serveur MCP Grist avec transport stdio");

// Lancer le serveur Python en mode stdio pour une communication directe
const server = spawn('python', [
  '-m', 'mcp_server_grist',
  '--transport', 'stdio'
], { 
  env,
  stdio: ['pipe', 'pipe', 'pipe'] // stdin, stdout, stderr
});

// Connecter les flux stdin/stdout entre Claude Desktop et le serveur Python
// Transférer les messages de Claude Desktop vers le serveur Python
process.stdin.pipe(server.stdin);

// Transférer les messages du serveur Python vers Claude Desktop
server.stdout.pipe(process.stdout);

// Gérer les logs du serveur Python
server.stderr.on('data', (data) => {
  const errorMsg = data.toString().trim();
  if (errorMsg.includes("ERROR") || errorMsg.includes("CRITICAL")) {
    logMessage("error", `Erreur Python: ${errorMsg}`);
  } else if (errorMsg.includes("INFO")) {
    logMessage("info", `Info Python: ${errorMsg}`);
  } else if (errorMsg.includes("DEBUG")) {
    logMessage("debug", `Debug Python: ${errorMsg}`);
  }
});

// Gérer la fermeture du serveur
server.on('close', (code) => {
  if (code !== 0) {
    logMessage("error", `Le serveur s'est arrêté avec le code ${code}`);
    process.exit(code);
  }
});

// Informer que le serveur est prêt
logMessage("info", "Serveur MCP Grist démarré avec succès en mode stdio");

// Gérer les signaux pour arrêter proprement le serveur
process.on('SIGINT', () => {
  logMessage("info", "Arrêt du serveur MCP Grist...");
  server.kill('SIGINT');
  process.exit(0);
});

process.on('SIGTERM', () => {
  logMessage("info", "Arrêt du serveur MCP Grist...");
  server.kill('SIGTERM');
  process.exit(0);
});

// Gérer la déconnexion du client
process.on('disconnect', () => {
  logMessage("info", "Client déconnecté, arrêt du serveur MCP Grist...");
  server.kill('SIGTERM');
  process.exit(0);
});

// Gérer la fermeture de stdin (le client se déconnecte)
process.stdin.on('close', () => {
  logMessage("info", "Connexion stdin fermée, arrêt du serveur MCP Grist...");
  server.kill('SIGTERM');
  process.exit(0);
});

// Gérer les erreurs non capturées
process.on('uncaughtException', (err) => {
  logMessage("error", `Erreur non capturée: ${err.message}`, { stack: err.stack });
  server.kill('SIGTERM');
  process.exit(1);
});

// Gérer les rejets de promesses non capturés
process.on('unhandledRejection', (reason, promise) => {
  logMessage("error", `Rejet de promesse non géré: ${reason}`, { promise });
  server.kill('SIGTERM');
  process.exit(1);
});
