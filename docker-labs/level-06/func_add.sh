#!/bin/bash
# func_add.sh - Fonction qui additionne deux nombres

add() {
    echo $(( $1 + $2 ))
}

add 3 4