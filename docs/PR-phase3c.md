# Texte de la PR — phase 3, lot 3c

Titre : Phase 3 (lot 3c) : historique local et export de rapports

- Historique local : un fichier JSON par opération terminée, dans le dossier de données
  utilisateur (`MAILBOX_HISTORY_DIR` le remplace). Écriture atomique, version explicite,
  purge au-delà de 200 entrées, fichier illisible ignoré sans casser la liste.
- Contenu limité à ce que le bilan affiche : horodatages, mode, résultat, comptes,
  périmètre, filtres, compteurs, code de sortie. Aucun mot de passe, aucun journal de session.
- Onglet « Historique » : liste, rapport détaillé, export texte, reprise du périmètre et des
  filtres d'une exécution passée (jamais les comptes ni les secrets), suppression.
- Un échec d'écriture est signalé dans le journal et n'interrompt pas l'opération.
- Les tests écrivent dans un dossier temporaire : aucun ne touche l'historique réel.

Format JSON retenu plutôt que SQLite, après discussion : volume faible, aucune requête
nécessaire, contenu lisible et supprimable fichier par fichier. Motifs dans
docs/ARCHITECTURE.md.

Validation locale Linux : 144 tests de socle, sous trois fuseaux horaires. Essai IMAP
d'historique sur copie réelle exécuté localement avec pymap substitué à GreenMail
(`docs/validation-3c-pymap.xml`) ; la fixture GreenMail est validée par ce run.
**Exiger 144 / 144 / 21 passed, aucun ignoré, avant de fusionner.**
