#!/bin/bash
# sed_replace.sh - Remplace tous les "old" par "new" dans un fichier

FILE="text.txt"
echo "Ancien contenu :"
cat $FILE

sed -i 's/old/new/g' $FILE

echo "Nouveau contenu :"
cat $FILE