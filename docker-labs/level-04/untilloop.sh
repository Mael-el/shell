#!/bin/bash
# untilloop.sh - Compte jusqu'à 5 en utilisant une boucle until

compteur=0
until [ $compteur -ge 5 ]; do
    compteur=$((compteur+1))
done
echo "Compteur: $compteur"