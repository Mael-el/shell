#!/bin/bash
# hello.sh - Affiche un message de bienvenue

if [ -z "$1" ]; then
    echo "Usage: $0 <nom>"
    exit 1
fi

echo "Bonjour $1 !"