# GitHub et mises à jour (Windows)

## 1. Dépôt GitHub existant

Dans GitHub, crée un dépôt **privé** nommé `wav-adaptive-notch`, sans README automatique.

## 2. Publier la source

Dans PowerShell, place-toi dans ce dossier (décompressé séparément, hors de `apps`) :

```powershell
git init -b main
git add .
git commit -m "Initial NiceGUI adaptive-notch application"
git remote add origin https://github.com/dbrouste/Clean_wav_notch_filter.git
git push -u origin main
```

Remplace TON_COMPTE par ton identifiant GitHub. Vérifie que Git et l'authentification GitHub sont installés.

## 3. Installer une copie suivie par Git

IMPORTANT : une installation faite en décompressant un ZIP ne contient pas de dossier `.git`.
Sauvegarde ou renomme le précédent dossier `C:\Python-Toolbox\apps\wav-oscillation`, puis :

```powershell
cd C:\Python-Toolbox\apps
git clone https://github.com/dbrouste/Clean_wav_notch_filter.git wav-oscillation
cd wav-oscillation
uv sync
uv run python app.py
```

Le catalogue Toolbox peut démarrer ce clone comme avant.

## 4. Utilisation

Dans l'onglet **Mises à jour**, appuie sur **Vérifier les mises à jour**, puis **Installer la mise à jour** si de nouveaux commits sont proposés. Ferme et rouvre l'application après la mise à jour.

Ce mécanisme :
- ne télécharge que la branche `origin` suivie par Git;
- ne fait aucun `reset --hard` et aucun `git clean`;
- refuse les modifications locales et les branches divergentes;
- récupère le code avec `git fetch` puis `git merge --ff-only`, et actualise les dépendances via `uv sync`;
- n'installe pas en silence : il demande une confirmation.

Ne modifie pas le code localement si tu veux continuer à bénéficier des mises à jour automatiques sans résolution manuelle des conflits. Les fichiers d'entrée/sortie WAV doivent rester hors du dépôt (ignorés par Git).

**Sécurité** : un dépôt privé limite la diffusion du code, mais les mises à jour restent de l'exécution de code. N'utilise que ton dépôt de confiance et protège ton compte GitHub.
