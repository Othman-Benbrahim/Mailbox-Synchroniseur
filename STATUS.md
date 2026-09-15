# État du projet — 0.3.0 alpha 1

Mise à jour du 15 septembre 2026. **La phase 2 est terminée pour le périmètre de
validation sur comptes de test isolés.** **La phase 3 est commencée : le lot 3a
(filtres par dates et taille, estimation du volume) est implémenté, testé sur le
socle et vérifié localement contre imapsync 2.314 réel en STARTTLS (pymap) ; la
variante GreenMail/TLS direct et la CI Windows attendent le run GitHub de sa PR.**

Le projet reprend le commit initial `eedaa95843118c4d2ed23ec791cf50f319ce00ae`.
La PR #1 a été fusionnée dans `3d5b7de9c94f347aceba4ae839c9284fe93b52c7`, puis
la PR #2 (quota strict) dans `92064b430aa3f8f14d504728b013ca013b3f83b0`.
Le lot 3a est livré par la PR #4 (branche `phase-3/filtres`).

| Phase | État | Preuve / suite |
| --- | --- | --- |
| 0 — Cadrage | Terminée | Roadmap, architecture, licence et structure initiales conservées |
| 1 — Application exécutable | Socle alpha validé | Tests du socle/interface sous Linux et Windows |
| 2 — Migrations vérifiées | Terminée sur comptes de test isolés | 14 essais IMAP réels, dont refus de quota strict et reprise |
| 3 — Fonctions avancées | Lot 3a implémenté ; validation partielle locale, complète après run de la PR #4 | 111 tests de socle et 2 essais IMAP réels (variante STARTTLS/pymap) réussis localement ; variante GreenMail et Windows en attente |
| 4 — OAuth et fournisseurs | À faire | Google / Microsoft non validés |
| 5 — Automatisation | À faire | Aucun service en arrière-plan |
| 6 — Distribution autonome | À faire | Aucun installateur ou moteur embarqué livré |

## Lot 3a — ce qui est livré

- Filtres par dates (bornes incluses, appliquées par le serveur sur la date interne
  IMAP via `--search "SINCE … BEFORE …"`) et par taille (`--maxsize`, `--minsize`
  en octets), jamais pour le test des accès.
- Onglet « Filtres », résumé dans la ligne de périmètre et dans la confirmation de
  copie ; toute modification invalide la simulation. Inversion des comptes conservée.
- Profils JSON v3 avec filtres ; lecture v1 et v2 maintenue.
- Bilan de simulation : messages à copier (`could be N without --dry mode`), volume
  estimé par différence entre `Host1 Total size` et `Total bytes skipped`.
  Bilan de copie : `Total bytes transferred`. Compteurs absents : « non communiqué ».
- Messages exclus par le filtre de taille comptés séparément (lignes `skipped
  (… exceeds maxsize …)`) ; ils expliquent les « absents à destination » sans être
  cachés et ne font pas échouer une copie par ailleurs complète.
- Code de sortie 121 (échec de la recherche IMAP) traduit.

## Ce que le lot 3a ne fait pas

- La simulation n'applique pas le filtre de taille : imapsync ne télécharge pas les
  messages en mode `--dry` (`dry1`), donc l'estimation est un maximum lorsque ce filtre
  est actif, et le bilan l'indique. L'option `--nodry1` le permettrait au prix d'un
  téléchargement complet de la source pendant la simulation ; non retenue.
- Pas de progression ni de temps restant : le moteur publie une ETA, mais elle
  dépend de `foldersizes` et n'est pas jugée fiable pour l'affichage.
- Pas de correspondance automatique, de miroir/déplacement, d'historique ni de
  limites de débit : lots suivants de la phase 3.

## Preuves

Correctif après le premier run de la PR #4 (run 34915336379) : la tâche
`unit (windows-latest)` a échoué alors que Linux passait. Cause reproduite
localement : le moteur et QProcess livrent des fins de ligne CRLF sous Windows, et
la reconnaissance des lignes `msg … skipped (… exceeds maxsize …)` exigeait une fin
de ligne LF ; une copie avec filtre de taille était alors marquée en échec sous
Windows. `report.feed` normalise désormais les fins de ligne ; trois tests CRLF
ajoutés, dont le faux moteur du runner qui écrit explicitement en CRLF.

Socle : 111 tests réussis localement sous Linux (Python 3.12, PySide6 6.11.2,
pytest 9.1.1) sur le code du lot 3a, dont 55 nouveaux dans `tests/test_phase3.py`.
Ces tests utilisent un faux moteur ; ils ne valident aucune migration réelle.

IMAP réel : deux essais ajoutés dans `tests/integration/test_migration.py`,
chacun paramétré sur GreenMail (TLS direct) et pymap (STARTTLS) :
`test_date_filter_selects_by_internal_date_and_estimates_volume` et
`test_size_filter_skips_large_messages_and_accounts_for_them`. Ils exigent, avec
imapsync 2.314 réel, que seuls les messages sélectionnés soient copiés, que
l'estimation de simulation égale le volume réellement transféré (filtre de dates),
que le message exclu par taille soit compté comme tel et que la copie reste confirmée.

Exécution locale du 15 septembre 2026 : les variantes STARTTLS de ces deux essais,
plus `test_starttls_copy`, ont réussi contre imapsync 2.314 (SHA-256 épinglé,
Mail::IMAPClient 3.43) et pymap 0.36.7, hors de la fixture de session du dépôt
(GreenMail n'est pas téléchargeable dans ce runtime) ; rapport conservé dans
`docs/validation-3a-pymap.xml`. Les variantes GreenMail n'ont pas encore été
exécutées. Le jalon du lot 3a n'est validé qu'après réussite complète de la tâche
`imap` (18 essais) et des tâches de socle du run GitHub de la PR #4 ; un test
ignoré ne vaut pas réussite.

Le lecteur des compteurs a été écrit d'après la source imapsync épinglée
(commit `93654c6025ff7814f983ab74dd300f9bed9282d9`, SHA-256 identique à celui de
`scripts/prepare_integration.py`) : libellés `Host1 Total size`, `Total bytes
skipped`, `Total bytes transferred`, `could be N without --dry mode`, et lignes
`msg … skipped (… exceeds maxsize limit … bytes)`. Le comportement `dry1` et le
comptage des messages filtrés parmi les absents proviennent de cette lecture ; les
essais IMAP en sont la vérification.

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
Voir [INTEGRATION.md](docs/INTEGRATION.md) et [QUOTA-STRICT.md](docs/QUOTA-STRICT.md).

## Fonctionnalités présentes

- Source/destination en TLS direct ou STARTTLS ; test d'accès, simulation, copie et arrêt.
- Sélection explicite et correspondance des dossiers Unicode et imbriqués.
- Filtres par dates et taille ; estimation du volume après simulation.
- Profils JSON v3 sans mots de passe, lecture des profils v1 et v2 maintenue.
- Invalidation de la simulation dès qu'un compte, un secret, le périmètre ou un filtre change.
- Bilan des copiés, ignorés, erreurs, absents et volumes, avec confirmation conditionnelle
  de présence à destination ; compteurs absents affichés « non communiqué ».
- Journal filtré ; expunges, suppressions et resynchronisation des états désactivés.

## Limites conservées

- Les migrations réelles sous Windows, macOS et les grands volumes restent à qualifier.
- Gmail, Microsoft 365 et leurs particularités ne sont pas validés ; OAuth relève de la phase 4.
- Aucun installateur autonome ni moteur imapsync embarqué n'est fourni.
- Les tests Windows du socle ne constituent pas une qualification complète de l'application sur Windows.
- Les comparaisons SHA-256 appartiennent aux tests. Le bilan de l'application
  confirme la présence des messages identifiés par imapsync dans le périmètre choisi.
- Un arrêt ou une erreur n'annule pas les messages déjà copiés.
- Le filtre par dates dépend de la commande SEARCH du serveur ; un serveur qui la
  refuse fait échouer l'opération (code 121), il n'y a pas de repli côté application.

## Prochaine action

1. Suivre la PR #4, attendre le run GitHub ; si la tâche `imap` échoue sur les
   nouveaux essais, corriger le lecteur de compteurs avant toute fusion.
2. Reporter ici le numéro du run et le commit testé, puis fusionner.
3. Lot 3b : correspondance automatique des dossiers proposée puis validée par
   l'utilisateur. Lot 3c : historique local et export de rapports sans secrets.
   Lot 3d : déplacement et miroir, désactivés par défaut, avec aperçu et confirmation
   séparés des suppressions, testés sur comptes jetables avant validation.
