#!/bin/bash
# length.sh - Affiche la longueur du premier argument

if [ -z "$1" ]; then
    echo "Usage: $0 <mot>"
    exit 1
fi

echo "${#1}"