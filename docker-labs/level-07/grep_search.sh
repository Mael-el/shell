#!/bin/bash
# grep_search.sh - Recherche des lignes contenant ERROR dans un dossier

if [ -z "$1" ]; then
    echo "Usage: $0 <dossier>"
    exit 1
fi

grep -r "ERROR" "$1"