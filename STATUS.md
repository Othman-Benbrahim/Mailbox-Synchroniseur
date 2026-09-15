# État du projet — 0.2.0 alpha 1

Mise à jour du 15 septembre 2026. **La phase 2 est terminée pour le périmètre de
validation sur comptes de test isolés.** La phase 3 est la prochaine étape ; son
implémentation n'a pas commencé.

Le projet reprend le commit initial `eedaa95843118c4d2ed23ec791cf50f319ce00ae`.
La PR #1 a été fusionnée dans `3d5b7de9c94f347aceba4ae839c9284fe93b52c7`, puis
la PR #2 (quota strict) dans `92064b430aa3f8f14d504728b013ca013b3f83b0`.

| Phase | État | Preuve / suite |
| --- | --- | --- |
| 0 — Cadrage | Terminée | Roadmap, architecture, licence et structure initiales conservées |
| 1 — Application exécutable | Socle alpha validé | Tests du socle/interface sous Linux et Windows |
| 2 — Migrations vérifiées | Terminée sur comptes de test isolés | 14 essais IMAP réels, dont refus de quota strict et reprise |
| 3 — Fonctions avancées | Prochaine phase, non commencée | Filtres dates/taille et estimation du volume, puis suite de la roadmap |
| 4 — OAuth et fournisseurs | À faire | Google / Microsoft non validés |
| 5 — Automatisation | À faire | Aucun service en arrière-plan |
| 6 — Distribution autonome | À faire | Aucun installateur ou moteur embarqué livré |

## Preuve de fermeture du jalon 2

Le [run GitHub 34911811074](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34911811074)
a réussi sur le commit `0eb09bfabda1a082bed6d9e881810373383f0324` de la PR #2,
ensuite intégré à main. Il ne faut pas confondre ce commit testé et le commit de fusion.

| Tâche | Environnement | Couverture de la suite | Résultat |
| --- | --- | --- | --- |
| [Socle Windows](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34911811074/job/104200749399) | windows-latest, Python 3.12 | 56 tests du socle/interface | Succès |
| [Socle Linux](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34911811074/job/104200749447) | Ubuntu 24.04, Python 3.12 | Les mêmes 56 tests du socle/interface | Succès |
| [Intégration IMAP](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34911811074/job/104200749475) | Ubuntu 24.04, Python 3.12 | 14 essais avec imapsync 2.314 réel | Succès |

Les serveurs de test sont GreenMail 2.1.3, pymap 0.36.7 et Dovecot 2.3.21.
Le scénario Dovecot exige un refus APPEND `OVERQUOTA`, un échec de copie sans perte,
puis une nouvelle simulation et une copie réussie après relèvement du quota,
sans recopie lors d'un lancement supplémentaire. Le mode `count` utilise
`quota_vsizes = yes`. Le rapport `imap-results.xml` est attaché au run GitHub.

Voir [INTEGRATION.md](docs/INTEGRATION.md) pour la reproduction et
[QUOTA-STRICT.md](docs/QUOTA-STRICT.md) pour le scénario du dernier critère.

## Fonctionnalités présentes

- Source/destination en TLS direct ou STARTTLS ; test d'accès, simulation, copie et arrêt.
- Sélection explicite et correspondance des dossiers Unicode et imbriqués.
- Profils JSON v2 sans mots de passe, lecture des profils v1 maintenue.
- Invalidation de la simulation dès qu'un compte, un secret ou le périmètre change.
- Bilan des copiés, ignorés, erreurs et absents, avec confirmation conditionnelle
  de présence à destination ; compteurs absents affichés « non communiqué ».
- Journal filtré ; expunges, suppressions et resynchronisation des états désactivés.

Les tests couvrent l'intégrité MIME/pièces jointes par SHA-256, dates, états,
conservation des anciens messages, reprise après coupure, absence de recopies,
refus TLS, erreurs d'identifiants et quota strict.

## Historique des preuves locales

La première validation locale sous Linux comptait 69 tests en 68,49 s : 56 tests
socle/interface et 13 essais IMAP, avant ajout du scénario Dovecot. Son rapport
`docs/validation-phase2.xml` est conservé comme preuve historique, pas comme rapport
de fermeture. Le serveur Dovecot n'a pas pu démarrer dans ce runtime, où les sockets
Unix sont bloqués ; sa validation réelle provient de GitHub Actions.

## Limites conservées

- Les migrations réelles sous Windows, macOS et les grands volumes restent à qualifier.
- Gmail, Microsoft 365 et leurs particularités ne sont pas validés ; OAuth relève de la phase 4.
- Aucun installateur autonome ni moteur imapsync embarqué n'est fourni.
- Les tests Windows du socle ne constituent pas une qualification complète de l'application sur Windows.
- Les comparaisons SHA-256 appartiennent aux tests. Le bilan de l'application
  confirme la présence des messages identifiés par imapsync dans le périmètre choisi.
- Un arrêt ou une erreur n'annule pas les messages déjà copiés.

## Prochaine action

Commencer la phase 3 dans l'ordre de ROADMAP.md : filtres par dates et taille,
estimation du volume, puis les autres fonctionnalités prévues. Les futurs modes de
suppression devront rester désactivés par défaut, avoir un aperçu et une confirmation
séparés, et être testés sur comptes jetables avant toute validation.
