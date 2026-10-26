#!/bin/bash
# func_ret.sh - Fonction qui retourne une valeur

add() {
    local result=$(( $1 + $2 ))
    echo $result
}

result=$(add 3 4)
echo "Resultat: $result"
echo "Exit code: 0"