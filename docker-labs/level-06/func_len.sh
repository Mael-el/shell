#!/bin/bash
# func_len.sh - Affiche la longueur du premier argument

if [ -z "$1" ]; then
    echo "Usage: $0 <chaîne>"
    exit 1
fi

echo "${#1}"