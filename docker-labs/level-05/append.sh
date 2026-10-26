#!/bin/bash
# append.sh - Ajoute des messages à un fichier

echo "[ERREUR] Nouveau problème détecté" >> errors.log
echo "[INFO] Information en append" >> errors.log
cat errors.log