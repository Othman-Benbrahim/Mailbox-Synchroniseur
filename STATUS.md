# État du projet — 0.3.0 alpha 3

Mise à jour du 15 septembre 2026. **La phase 2 est terminée pour le périmètre de
validation sur comptes de test isolés.** **La phase 3 est en cours : le lot 3a (filtres, estimation du volume) est validé et
fusionné ; les lots 3b (découverte et correspondance) et 3c (historique local et export) sont
livrés ; 3b est validé et fusionné, 3c est testé sur le socle et vérifié localement, sa
validation GreenMail et Windows attend le run GitHub de sa PR.** Lot 3d à faire.

Le projet reprend le commit initial `eedaa95843118c4d2ed23ec791cf50f319ce00ae`.
La PR #1 a été fusionnée dans `3d5b7de9c94f347aceba4ae839c9284fe93b52c7`, puis
la PR #2 (quota strict) dans `92064b430aa3f8f14d504728b013ca013b3f83b0`.
Le lot 3a a été livré par la PR #4 (branche `phase-3/filtres`) et fusionné dans
`1f3ddf5987369f87b8a49722655f4d77d67ae48f`.

| Phase | État | Preuve / suite |
| --- | --- | --- |
| 0 — Cadrage | Terminée | Roadmap, architecture, licence et structure initiales conservées |
| 1 — Application exécutable | Socle alpha validé | Tests du socle/interface sous Linux et Windows |
| 2 — Migrations vérifiées | Terminée sur comptes de test isolés | 14 essais IMAP réels, dont refus de quota strict et reprise |
| 3 — Fonctions avancées | Lots 3a et 3b validés et fusionnés ; lot 3c livré, validation en attente ; 3d à faire | Lot 3a : run 34916209481. Lot 3b : run 34917709552. Lot 3c : 144 tests de socle locaux |
| 4 — OAuth et fournisseurs | À faire | Google / Microsoft non validés |
| 5 — Automatisation | À faire | Aucun service en arrière-plan |
| 6 — Distribution autonome | À faire | Aucun installateur ou moteur embarqué livré |

## Lot 3c — ce qui est livré

- Historique local : un fichier JSON par opération terminée, dans le dossier de données
  utilisateur (`MAILBOX_HISTORY_DIR` le remplace). Écriture atomique, version explicite,
  purge au-delà de 200 entrées, fichier illisible ignoré sans faire échouer la liste.
- Contenu limité à ce que le bilan affiche : horodatages, mode, résultat, comptes,
  périmètre, filtres, compteurs, code de sortie. **Aucun mot de passe, aucun journal.**
- Onglet « Historique » : liste, rapport détaillé, export en fichier texte, reprise du
  périmètre et des filtres d'une exécution passée (jamais les comptes ni les secrets),
  suppression d'une entrée ou de la totalité.
- Un échec d'écriture de l'historique est signalé dans le journal et n'interrompt pas
  l'opération.

Preuves : 144 tests de socle réussis localement (13 nouveaux, `tests/test_phase3c.py`),
sous trois fuseaux horaires différents. Essai IMAP
`test_history_of_a_real_run_carries_no_secret_and_matches_the_engine` réussi localement,
avec pymap substitué à GreenMail faute d'accès à ce dernier dans ce runtime
(`docs/validation-3c-pymap.xml`) ; la variante GreenMail et le socle Windows sont à
valider par le run GitHub de la PR du lot 3c. Un test ignoré ne vaut pas réussite.

Limites du lot 3c : l'historique est en clair sur le disque et contient adresses, serveurs
et noms de dossiers ; il n'est pas chiffré et n'est pas protégé contre un autre processus
local. Pas de limite de débit livrée : elle est reportée au lot 3d ou sera consignée comme
abandonnée.

## Lot 3b — ce qui est livré

- Bouton « Découvrir et proposer… » dans l'onglet des dossiers : un `LIST` IMAP par compte,
  lecture seule, TLS vérifié (chaîne et nom d'hôte, TLS direct ou STARTTLS sans repli).
- Proposition de correspondance avec raison par ligne : nom identique, rôle (attributs
  SPECIAL-USE ou alias usuels français/anglais), casse, sous-dossier d'un parent renommé,
  séparateur adapté, dossier à créer. Exclusions explicites : non sélectionnable, « tous
  les messages », conflit de destination. Toute proposition satisfait `Plan.validate`.
- Le tableau reste modifiable ; la proposition invalide la simulation ; la copie reste
  conditionnée à une simulation réussie. Découverte hors du fil d'interface, contrôles
  bloqués pendant son exécution, mots de passe libérés à la fin, jamais dans les messages.
- Décodage UTF-7 modifié tolérant ; lecteur `LIST` pour noms cités, atomes, littéraux.
- Retrait du dossier `ci-results/` commité par erreur dans la PR #5 ; ajouté au `.gitignore`.

### Preuve de validation du lot 3b

Le [run GitHub 34917709552](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34917709552) a réussi sur le commit `7065672cc367272950aca0d502ba1cb998ce80f9` de la PR #6,
ensuite fusionné dans `74c1b706e60019a02cca078674c0ec378c462072`. Ses trois tâches sont au vert : socle sous Ubuntu 24.04
et sous windows-latest (131 tests chacune), et intégration IMAP sous Ubuntu 24.04
(20 essais avec imapsync 2.314 réel, GreenMail, pymap et Dovecot). Le rapport
`imap-results.xml` est attaché au run.

Avant ce run, l'essai
`test_discovery_lists_folders_over_verified_tls_and_proposal_drives_a_real_copy`
avait été exécuté localement en variante pymap/STARTTLS contre imapsync 2.314 réel
(`docs/validation-3b-pymap.xml`) ; la variante GreenMail a été validée par la CI.

Limites du lot 3b : la découverte utilise le magasin de certificats de Python, la copie
celui de Perl ; les rôles reconnus par nom couvrent le français et l'anglais usuels, pas
toutes les langues ; les attributs SPECIAL-USE ne sont pas fournis par tous les serveurs
(GreenMail et pymap n'en publient pas dans les essais).

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

## Preuve de validation du lot 3a

Le [run GitHub 34916209481](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34916209481) a réussi sur le commit `10637f2c862acba1758a7ee351f24b9a42f16c27` de la PR #4,
ensuite fusionné dans `1f3ddf5987369f87b8a49722655f4d77d67ae48f`. Il ne faut pas confondre le commit testé et le commit
de fusion.

| Tâche | Environnement | Couverture | Résultat |
| --- | --- | --- | --- |
| Socle Ubuntu | Ubuntu 24.04, Python 3.12 | 111 tests du socle/interface | Succès, 111 passed |
| Socle Windows | windows-latest, Python 3.12 | Les mêmes 111 tests | Succès, 111 passed |
| Intégration IMAP | Ubuntu 24.04, Python 3.12 | 18 essais avec imapsync 2.314 réel (GreenMail, pymap, Dovecot) | Succès, 18 passed, 0 ignoré |

Le rapport `imap-results.xml` est attaché à ce run. Cette validation porte sur des
comptes de test isolés ; elle ne qualifie ni les fournisseurs réels, ni macOS, ni les
grands volumes.

## Historique des correctifs de la PR #4

Correctif après le premier run de la PR #4 (run 34915336379) : la tâche
`unit (windows-latest)` a échoué alors que Linux passait. Cause reproduite
localement : le moteur et QProcess livrent des fins de ligne CRLF sous Windows, et
la reconnaissance des lignes `msg … skipped (… exceeds maxsize …)` exigeait une fin
de ligne LF ; une copie avec filtre de taille était alors marquée en échec sous
Windows. `report.feed` normalise désormais les fins de ligne ; trois tests CRLF
ajoutés, dont le faux moteur du runner qui écrit explicitement en CRLF.

Second correctif après le run 34915655530 : socle Linux et Windows verts, 16 essais
IMAP sur 18 réussis ; les deux variantes GreenMail des essais de filtres échouaient
sur les seules comparaisons d'octets. Cause établie par les valeurs du run : GreenMail
annonce un `RFC822.SIZE` sans en-têtes (22830 et 38 octets) alors que les messages
transférés font 23145 et 351 octets, exactement la longueur des messages injectés et
exactement ce que pymap annonce. Les essais distinguent désormais la taille annoncée
par le serveur (base de l'estimation et de la décision `--maxsize`) et les octets
réels transférés ; l'égalité des deux n'est exigée que sur pymap, qui annonce des
tailles exactes. Le code de l'application n'a pas changé pour ce correctif.
Conséquence documentée : l'estimation vaut ce que vaut le `RFC822.SIZE` du serveur.

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
`docs/validation-3a-pymap.xml`. Les variantes GreenMail ont ensuite été validées par le run GitHub ci-dessus. Le jalon du lot 3a est validé par le run 34916209481, où les 18 essais ont été exécutés,
aucun ignoré.

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
- L'estimation du volume et le filtre de taille reposent sur le `RFC822.SIZE` annoncé
  par le serveur source. Un serveur qui l'annonce inexactement (GreenMail l'annonce
  sans en-têtes) fausse l'estimation d'autant ; le volume transféré affiché après copie
  reste, lui, mesuré sur les octets réels.

## Prochaine action

Ouvrir la PR du lot 3c et exiger 144 + 144 + 21 sans ignoré. Lot 3d ensuite : déplacement
et miroir, désactivés par défaut, avec aperçu et confirmation séparés des suppressions,
testés sur comptes jetables avant validation.

Rappel de l'ordre initial des lots (lot 3b : correspondance automatique des dossiers proposée puis validée par
   l'utilisateur. Lot 3c : historique local et export de rapports sans secrets.
   Lot 3d : déplacement et miroir, désactivés par défaut, avec aperçu et confirmation
   séparés des suppressions, testés sur comptes jetables avant validation.
