[SHELLFORGE] Lab Level 05 - Redirections
=========================================

Challenge C05 : Enregistrer les erreurs dans un fichier

Niveau : Intermédiaire
Points : 250
Catégorie : Redirections

Objectif :
Comprendre et utiliser les descripteurs de fichiers 
pour rediriger uniquement stderr (erreur standard) vers un fichier.

Contexte :
Le script challenge.sh génère deux types de sortie :
- stdout (standard output) : informations générales [INFO]
- stderr (standard error) : messages d'erreur [ERROR]

Votre tâche :
1. Exécutez challenge.sh et observez la sortie
2. Redirigez uniquement stderr vers un fichier errors.log
3. Vérifiez que errors.log contient uniquement les erreurs
4. Vérifiez que s'affiche toujours à l'écran uniquement stdout

Niveau de difficulté : Medium

Étapes :

1. Découverte
   ```bash
   ./challenge.sh
   # Devriez voir :
   # [INFO] Starting process...
   # [ERROR] Permission denied
   # [INFO] Process completed
   ```

2. Manipulation guidée
   ```bash
   # Redirigez uniquement stderr vers errors.log
   ./challenge.sh 2> errors.log
   
   # Vérifiez le contenu du fichier
   cat errors.log
   # Devriez voir :
   # [ERROR] Permission denied
   ```

3. Validation autonome
   ```bash
   # Essayez maintenant sans indices
   ./challenge.sh 2> errors.log && cat errors.log
   ```

Attentes :
- errors.log doit contenir exactement : [ERROR] Permission denied
- La sortie standard à l'écran ne doit contenir AUCUN message d'erreur
- Les messages [INFO] doivent toujours s'afficher à l'écran

Concepts clés :
- 1 : stdin (entrée standard)
- 2 : stdout (sortie standard)  
- 3 : stderr (sortie d'erreur standard)
- `2>` : redirige stderr vers un fichier
- `>` : redirige stdout vers un fichier
- `2>&1` : redirige stderr vers l'endroit où va stdout