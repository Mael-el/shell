#!/bin/bash
# check.sh - Vérifie si un fichier existe

if [ -f "$1" ]; then
    echo "$1 existe"
else
    echo "$1 n'existe pas"
fi