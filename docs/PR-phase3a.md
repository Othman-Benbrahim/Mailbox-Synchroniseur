# Texte de la PR #4 — phase 3, lot 3a

Titre : Phase 3 (lot 3a) : filtres par dates et taille, estimation du volume

La phase 2 est fermée par le run 34911811074. Cette PR ouvre la phase 3 avec le
premier lot de ROADMAP.md, sans code de suppression.

- Filtres par dates (`--search SINCE/BEFORE`, bornes incluses, date interne IMAP)
  et par taille (`--maxsize`/`--minsize` en octets), jamais pour `--justlogin`.
- Onglet « Filtres » ; résumé dans le périmètre et la confirmation ; invalidation
  de la simulation à chaque modification ; profils JSON v3, lecture v1/v2 maintenue.
- Bilan : messages à copier et volume estimé après simulation, volume transféré
  après copie, compteurs absents affichés « non communiqué ».
- Les messages exclus par le filtre de taille sont comptés séparément : ils
  expliquent les absents à destination sans faire échouer une copie complète.
- Code de sortie 121 (échec SEARCH) traduit.

Validation locale Linux : 111 tests de socle réussis (faux moteur). Deux essais
IMAP réels ajoutés (filtre par dates, filtre par taille), paramétrés GreenMail et
pymap ; variantes pymap réussies localement contre imapsync 2.314 réel
(`docs/validation-3a-pymap.xml`). Variantes GreenMail et socle Windows à valider
par ce run. **Ne pas fusionner si la tâche `imap` échoue ou ignore ces essais.**

Limites : la simulation n'applique pas le filtre de taille (imapsync `dry1`), donc
l'estimation est alors un maximum, signalé dans le bilan. Pas de progression, de
correspondance automatique, d'historique ni de miroir dans ce lot.
