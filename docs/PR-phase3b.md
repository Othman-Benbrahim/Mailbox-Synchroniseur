# Texte de la PR — phase 3, lot 3b

Titre : Phase 3 (lot 3b) : découverte des dossiers et proposition de correspondance

- Découverte en lecture seule des dossiers des deux comptes : une commande IMAP `LIST`
  par compte via `imaplib`, TLS vérifié (chaîne et nom d'hôte, TLS direct ou STARTTLS
  sans repli en clair). Aucun transfert : imapsync reste le seul moteur de copie.
  Écart consigné dans ROADMAP.md et docs/ARCHITECTURE.md.
- Proposition de correspondance avec raison par ligne (identique, rôle par SPECIAL-USE ou
  alias FR/EN, casse, parent renommé, séparateur adapté, à créer) ; exclusions explicites
  (`\Noselect`, `\All`, conflit). Le tableau reste modifiable, la simulation obligatoire.
- Décodage UTF-7 modifié, lecteur `LIST` robuste, worker hors du fil d'interface.
- Retrait de `ci-results/` commité par erreur (PR #5) ; `.gitignore` complété.

Validation locale Linux : 131 tests de socle. Essai IMAP réel de découverte + copie
pilotée par la proposition, variante pymap, réussi contre imapsync 2.314
(`docs/validation-3b-pymap.xml`). Variante GreenMail et socle Windows à valider par ce
run : **exiger 131 / 131 / 20 passed, aucun ignoré, avant de fusionner.**
