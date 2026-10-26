#!/bin/bash
# email_grep.sh - Trouve des adresses email dans un fichier en utilisant regex

if [ -z "$1" ]; then
    echo "Usage: $0 <fichier>"
    exit 1
fi

grep -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" "$1"