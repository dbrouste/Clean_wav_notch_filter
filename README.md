# Nettoyage WAV – notch adaptatif (NiceGUI)

Version intégrant la fonction `clean_wav_adaptive_notch` fournie par l'utilisateur, et non le notch fixe du prototype antérieur.

## Installation
Décompresser le dossier `wav-oscillation` dans `C:\Python-Toolbox\apps\`.
Si un dossier `wav-oscillation` existe déjà, en faire une copie de sauvegarde puis remplacer ses fichiers.
Relancer Python Toolbox, actualiser, puis lancer « Nettoyage WAV – notch adaptatif ».

## Exécution indépendante
Dans PowerShell :

```powershell
cd C:\Python-Toolbox\apps\wav-oscillation
uv run python app.py
```

## Fonctionnement
* Paramètres avancés initialisés aux valeurs du dernier exemple Colab transmis.
* Fonction d'origine préservée (suppression de l'exécution `/content/test.wav` ; imports ajoutés ; `display()` remplacé par `print()` pour usage Windows).
* Ne réécrit jamais le WAV source. Refuse aussi d'écraser un résultat déjà présent.
* Exporte WAV dans le même sous-type PCM/FLOAT que l'original, avec risque de quantification si format PCM.
* Exporte rapport CSV, corrélations CSV, résumé JSON et spectrogrammes PNG.

## Limites
* Traitement en mémoire (STFT et masque complet) : fichiers longs potentiellement gourmands en RAM.
* L'algorithme peut ne trouver aucune raie stable ; dans ce cas l'erreur est affichée.
* Les spectrogrammes PNG utilisent une échelle commune fixe -120 à -30 dB. Ils servent à la vérification visuelle ; pas de zoom interactif dans cette V1.
* Sur des signaux scientifiques, conserver l'original et vérifier que des signaux utiles ne sont pas supprimés.

## Mode répertoire (V4)
Choisir « Répertoire » puis cliquer sur « Parcourir… » ou saisir le chemin Windows. Le programme traite les WAV à la racine du dossier, sans parcourir les sous-dossiers. Chaque résultat et ses rapports/spectrogrammes sont enregistrés dans `<dossier>/nettoyes/`. Les sorties existantes ne sont pas écrasées et les fichiers en échec n’interrompent pas le lot. Une barre de progression et un tableau récapitulatif sont affichés.


## GitHub et mises à jour

Voir [INSTALL_GITHUB.md](INSTALL_GITHUB.md). Le bouton de mise à jour est dans l’onglet **Mises à jour** et requiert un clone Git (pas une extraction ZIP).


Dépôt officiel : https://github.com/dbrouste/Clean_wav_notch_filter

## Optimisation 0.3.0

- La STFT de suivi est calculée une seule fois par taille FFT et partagée entre les oscillations suivies.
- Le filtre spectral est appliqué uniquement autour de chaque raie parasite, sans allouer un grand masque dense pour chaque canal.
- La méthode de détection, les garde-fous et les paramètres de l’algorithme restent inchangés.
- Tests de non-régression sur deux WAV mono 384 kHz / 5 s : différence maximale de sortie inférieure à 3e-14 entre V2 et V3, mêmes notchs activés.
- Temps mesurés sur environnement de test (moteur uniquement) : 1.86 -> 1.49 s, puis 1.89 -> 0.69 s. Mesures indicatives.
