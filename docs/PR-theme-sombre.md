# Texte de la PR — lisibilité sous thème sombre

Titre : Correctif : interface illisible sous un système en thème sombre

Signalé en usage réel sous Windows : l'application s'affichait en texte sombre sur fond
sombre, au point de ne plus pouvoir lire les libellés ni vérifier ce qui allait être copié.

Cause : Qt suit la palette de la plateforme, et la feuille de style ne fixait de fond clair
que sur une partie des widgets. Tout le reste — onglets, tableaux, listes, listes
déroulantes, calendrier des filtres, boîtes de dialogue — héritait du fond sombre du système
tout en conservant la couleur de texte sombre de la feuille de style.

- `theme.py` : palette claire complète (groupes actif, inactif, désactivé) et style Fusion,
  appliqués au démarrage.
- Feuille de style complétée : chaque famille de widgets utilisée énonce son fond et sa
  couleur de texte. Le journal garde son fond sombre volontaire, désigné par `objectName`.
- 14 tests (`tests/test_theme.py`) : remplacement d'une palette système sombre, rapports de
  contraste WCAG pour le texte courant, le texte désactivé et les lignes sélectionnées,
  et absence de famille de widgets laissée sans couleurs.

Aucun changement fonctionnel. Validation locale : 212 tests de socle.
Limite consignée : l'application impose un thème clair, elle ne suit pas le thème sombre.
