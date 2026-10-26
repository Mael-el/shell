#!/bin/bash
# whileloop.sh - Compte de 0 à 3 en utilisant une boucle while

compteur=0
while [ $compteur -lt 4 ]; do
    echo $compteur
    compteur=$((compteur + 1))
done