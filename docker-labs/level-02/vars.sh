#!/bin/bash
# vars.sh - Affiche le premier argument passé au script

if [ -z "$1" ]; then
    echo "Aucun argument fourni"
    exit 1
fi

echo "La valeur est: $1"