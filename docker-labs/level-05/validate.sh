#!/bin/bash
# validate.sh - Valide la réponse de l'utilisateur pour le challenge redirections

set -e

CHALLENGE_NUM=5
PASS=0
FAIL=0

echo "=== SHELLFORGE - Validation du Challenge $CHALLENGE_NUM ==="
echo ""

# Vérifier que le fichier errors.log existe
if [ ! -f errors.log ]; then
    echo "❌ ÉCHEC : Le fichier errors.log n'existe pas"
    echo "   Vous n'avez pas redirigé stderr vers errors.log"
    FAIL=$((FAIL + 1))
else
    echo "✓ Le fichier errors.log existe"
    
    # Vérifier le contenu du fichier
    EXPECTED="[ERROR] Permission denied"
    ACTUAL=$(cat errors.log)
    
    if [ "$ACTUAL" = "$EXPECTED" ]; then
        echo "✓ Le contenu de errors.log est correct : $ACTUAL"
        PASS=$((PASS + 1))
    else
        echo "❌ ÉCHEC : Le contenu de errors.log est incorrect"
        echo "   Attendu : $EXPECTED"
        echo "   Obtenu   : $ACTUAL"
        FAIL=$((FAIL + 1))
    fi
    
    # Vérifier que stdout n'a pas de messages d'erreur
    # On réexécute et on vérifie que 2>&1 ne contient pas d'erreurs non désirées
    OUTPUT=$(/home/shadow/shellforge/docker-labs/level-05/challenge.sh 2>&1)
    if echo "$OUTPUT" | grep -q "ERROR"; then
        echo "⚠️ Avertissement : La sortie standard contient des messages d'erreur"
        echo "   Cela peut arriver si la redirection n'est pas propre"
    else
        echo "✓ La sortie standard est propre (pas d'erreurs mélangées)"
    fi
fi

# Vérifier que challenge.sh est exécutable
if [ ! -x challenge.sh ]; then
    echo "❌ ÉCHEC : challenge.sh n'est pas exécutable"
    FAIL=$((FAIL + 1))
else
    echo "✓ challenge.sh est exécutable"
    PASS=$((PASS + 1))
fi

echo ""
echo "=== Résultat : $PASS succès, $FAIL échec ==="

if [ $FAIL -eq 0 ]; then
    echo "🎉 FÉLICITATIONS ! Vous avez validé le challenge $CHALLENGE_NUM"
    exit 0
else
    echo "❌ Continuez à vous entraîner"
    exit 1
fi