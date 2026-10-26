#!/bin/bash
# length.sh - Affiche la longueur d'un mot

if [ -z "$1" ]; then
    echo "Usage: $0 <mot>"
    exit 1
fi

echo "${#1}"