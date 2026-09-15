# État du projet — 0.6.0 alpha 1

Mise à jour du 15 septembre 2026. **La phase 2 est terminée pour le périmètre de
validation sur comptes de test isolés.** **La phase 3 est en cours : le lot 3a (filtres, estimation du volume) est validé et
fusionné ; les lots 3b (découverte et correspondance) et 3c (historique local et export) sont
validés et fusionnés, et **la phase 3 est terminée** : le lot 3d (miroir) est validé et
fusionné.** Le déplacement, les limites de débit et l'affichage d'une progression sont
écartés du périmètre, avec leurs motifs dans ROADMAP.md. **La phase 4 est suspendue après le lot 4a** : la
connexion OAuth est fusionnée après un run vert, mais elle n'a été validée contre aucun
serveur IMAP réel, et l'inscription d'application côté Microsoft s'est révélée hors de
portée du public visé. Motif et conséquences ci-dessous. Une CI verte ne vaut pas ici
compatibilité fournisseur.

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
| 3 — Fonctions avancées | Terminée : lots 3a, 3b, 3c et 3d validés et fusionnés | Un run vert par lot, détaillés ci-dessous |
| 4 — OAuth et fournisseurs | Lot 4a fusionné, non validé contre un serveur réel ; **suite suspendue** | Run de la PR #12 : 198 tests de socle Linux et Windows, 23 essais IMAP ; aucun essai IMAP OAuth |
| 5 — Automatisation | À faire | Aucun service en arrière-plan |
| 6 — Distribution autonome | Chaîne écrite, **non éprouvée** | Trois constructions Windows en CI, jamais exécutées à ce jour |

## Correctif 0.4.0 alpha 2 — lisibilité sous thème sombre

Signalé en usage réel : sous un système en thème sombre, l'interface s'affichait en texte
sombre sur fond sombre, illisible. Cause : la feuille de style ne couvrait qu'une partie des
widgets, le reste héritant de la palette sombre de la plateforme. Correction : palette claire
complète déclarée par l'application (`theme.py`) avec le style Fusion, et feuille de style
énonçant fond et texte pour chaque famille de widgets. 14 tests ajoutés
(`tests/test_theme.py`), dont la vérification des rapports de contraste WCAG et le
remplacement effectif d'une palette système sombre.

Limite : l'application impose un thème clair ; elle ne suit pas encore le thème sombre du
système. Un vrai thème sombre est une évolution distincte, non planifiée à ce jour.

## Lot 4a — ce qui est livré

- Authentification par OAuth en plus du mot de passe, pour Microsoft et Google. Flux code +
  PKCE dans le navigateur système, redirection sur la boucle locale, vérification du `state`.
- **Aucune identité d'application embarquée** : l'utilisateur inscrit la sienne et fournit
  son `client_id` ; procédure complète dans `docs/OAUTH.md`.
- Le jeton est traité comme un mot de passe : masqué dans le journal, absent des profils et
  de l'historique, effacé à la fermeture et dès que l'identifiant, le `client_id` ou la
  méthode d'authentification changent.
- Le jeton n'est pas un argument de ligne de commande : il est écrit en 0600 dans le
  répertoire temporaire de l'opération et `--oauthaccesstoken{1,2}` reçoit ce chemin. Les
  variables `IMAPSYNC_PASSWORD` ne sont pas renseignées pour un compte OAuth.
- Profils : `auth` et `provider` enregistrés (ce ne sont pas des secrets) ; les profils
  antérieurs se relisent inchangés.

### Ce qui n'est PAS validé

**Aucune authentification XOAUTH2 réelle n'a été exercée.** GreenMail et pymap ne prennent
pas en charge ce mécanisme, et Dovecot ne démarre pas dans l'environnement de développement
local. Les 28 tests du lot vérifient la construction de la requête d'autorisation, le flux
complet sur un serveur de boucle locale réel, le refus d'un `state` falsifié, la traduction
des erreurs du fournisseur, et surtout le traitement du jeton comme secret — mais la
dernière étape, un serveur IMAP qui accepte réellement le jeton, n'est pas couverte.

En conséquence : **aucune compatibilité Gmail, Outlook.com ou Microsoft 365 n'est
annoncée**. Le lot 4b a pour seul objet de combler ce trou, avec un serveur de test validant
réellement le jeton, puis un essai manuel sur un compte réel.

Preuves disponibles : le run GitHub de la PR #12 a réussi sur le commit `41579c2`,
fusionné dans `431dabf` — 198 tests du socle sous Ubuntu 24.04 et sous windows-latest,
23 essais IMAP réels (inchangés : ce lot n'en ajoute aucun). Les 28 nouveaux tests sont dans
`tests/test_phase4.py` et comprennent l'exécution du flux complet contre un vrai serveur HTTP
de boucle locale. Ce que ce run prouve, c'est la mécanique du flux et le traitement du jeton
comme secret — pas qu'un serveur IMAP accepte ce jeton.

## Preuves de la phase 3

Chaque lot a été fusionné après un run GitHub vert sur ses trois tâches : socle sous
Ubuntu 24.04, le même socle sous windows-latest, et les essais IMAP réels sous Ubuntu 24.04
avec imapsync 2.314, GreenMail 2.1.3, pymap 0.36.7 et Dovecot 2.3.21. Le commit testé n'est
jamais le commit de fusion.

| Lot | Run | Commit testé | Fusion | Socle | Essais IMAP |
| --- | --- | --- | --- | --- | --- |
| 3a — filtres et volume | [34916209481](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34916209481) | `10637f2` | `1f3ddf5` | 111 | 18 |
| 3b — découverte et correspondance | [34917709552](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34917709552) | `7065672` | `74c1b70` | 131 | 20 |
| 3c — historique et export | [34918761935](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34918761935) | `b5b68cf` | `ffd4018` | 144 | 21 |
| 3d — miroir | run de la PR #10 | `562d67e` | `25750fc` | 170 | 23 |

Le lot 3d a été régénéré sur `1b38ef9` après un conflit documentaire ; son code est celui
déjà passé au run 34919944554, revalidé par le run de la PR #10 sur `562d67e`, dont
les six vérifications étaient au vert. Les rapports `imap-results.xml` sont attachés aux runs.

Ce que cette validation ne couvre pas, pour toute la phase : migrations réelles sous Windows
et macOS, grands volumes, Gmail et Microsoft 365, et toute particularité de fournisseur.
Les serveurs de test sont des fixtures déterministes.

## Lot 3d — ce qui est livré

Le miroir est la **seule** fonction du produit capable de supprimer des messages, et
uniquement à destination. `--nodelete1` est passé dans tous les modes : la boîte source
n'est jamais touchée.

- Suppression à destination de ce qui n'est plus à la source (`--delete2`), désactivée par
  défaut. Marquage `\Deleted` seulement ; imapsync viderait de lui-même, c'est explicitement
  désactivé (`--noexpunge2 --nouidexpunge2`). Vidage définitif derrière une option séparée.
- Quatre garde-fous cumulés : case décochée à chaque démarrage et jamais enregistrée dans un
  profil ; simulation réussie du même plan **miroir déjà armé** (armer invalide la simulation
  précédente) ; aperçu du nombre exact de suppressions issu de cette simulation ;
  confirmation par saisie de `SUPPRIMER`, un clic ne suffit pas.
- Miroir refusé avec un filtre actif : un message masqué par un filtre serait vu comme absent
  de la source et supprimé à destination. Refus explicite, jamais un contournement silencieux.
- Bilan et historique indiquent le caractère destructif, le nombre de suppressions et leur
  réversibilité ; le rapport exporté écrit « Miroir : inactif » quand il ne l'était pas.

Preuves : 170 tests de socle réussis localement (26 nouveaux, `tests/test_phase3d.py`),
dont la vérification qu'aucun mode ne passe `--delete1` et qu'une confirmation mal saisie
ne lance rien. Deux essais IMAP réels (miroir par marquage, miroir avec vidage) réussis
localement avec pymap substitué à GreenMail (`docs/validation-3d-pymap.xml`) : ils exigent
que la simulation ne supprime rien, que seule la destination perde le message absent de la
source, et que la source reste identique. Les variantes GreenMail et le socle Windows ont ensuite été
validés par la CI ; voir le tableau des preuves ci-dessus.

Limites du lot 3d : le miroir n'est pas une synchronisation bidirectionnelle, la source fait
autorité. Un arrêt en cours laisse la destination partiellement mise en miroir. Les
suppressions ne sont pas annulables depuis l'application : c'est au client de messagerie de
l'utilisateur de restaurer des messages marqués, et rien n'est récupérable après un vidage.

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

### Preuve de validation du lot 3c

Le [run GitHub 34918761935](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34918761935) a réussi sur le commit `b5b68cfdef206c96dc86590e214cdc4e1ae6e0e8` de la PR #8,
ensuite fusionné dans `ffd4018e2c196aca1e9cd60a2e7c122652bf2e75` : 144 tests du socle sous Ubuntu 24.04, les mêmes 144 sous
windows-latest, et 21 essais IMAP réels sous Ubuntu 24.04, **aucun ignoré**. Le rapport
`imap-results.xml` est attaché au run.

Avant ce run, les 144 tests de socle avaient été exécutés localement sous trois fuseaux
horaires différents (le nom des fichiers d'historique dépend de l'heure locale), et l'essai
`test_history_of_a_real_run_carries_no_secret_and_matches_the_engine` avait été exécuté avec
pymap substitué à GreenMail faute d'accès à ce dernier (`docs/validation-3c-pymap.xml`) ;
la fixture GreenMail a été validée par la CI.

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

## Phase 6 — ce qui est livré

- `packaging/build-engine.ps1` : construction d'`imapsync.exe` avec PAR::Packer depuis le
  commit amont épinglé, après installation des modules CPAN. Le binaire doit répondre
  exactement `2.314` à `--version`, sinon la construction échoue.
- `packaging/mailbox-synchroniseur.spec` : empaquetage PyInstaller **en mode dossier**,
  exigence de conformité LGPLv3 pour Qt, pas un choix de confort.
- `packaging/installer.iss` : installateur Inno Setup, LICENSE et THIRD_PARTY.md installés
  à côté de l'application, historique local non supprimé à la désinstallation.
- `.github/workflows/package.yml` : les trois constructions sur `windows-latest`, avec
  vérification que l'exécutable démarre (`--version`), que le moteur produit annonce la
  bonne version, et que l'application détecte le moteur embarqué.
- `bundle.py` : localisation du moteur livré à côté de l'exécutable. Il est présélectionné
  et reste remplaçable ; la simulation préalable et les autres garanties sont inchangées.
- THIRD_PARTY.md énumère les composants réellement distribués et leurs obligations.

### Ce qui n'est PAS éprouvé

**Aucune de ces constructions n'a jamais été exécutée.** L'environnement de développement
n'a ni Windows, ni Strawberry Perl, ni Inno Setup. Seuls l'empaquetage PyInstaller sous
Linux et le contrat de détection du moteur ont été vérifiés localement ; 11 tests
(`tests/test_phase6.py`) couvrent ce contrat, 223 tests de socle au total.

La construction d'imapsync par PAR::Packer sous Windows est le point le plus incertain :
plusieurs modules CPAN n'ont pas de binaire Windows et dépendent d'OpenSSL. Le premier run
dira ce qui manque.

La phase 6 ne sera consignée comme validée qu'après un run vert **et** une installation
réussie sur une machine Windows sans Python ni Perl, avec une migration de référence.
Aucune signature ni notarisation n'est annoncée : il n'y en a pas.

## Pourquoi la phase 4 est suspendue

Le lot 4a repose sur une hypothèse qui s'est révélée fausse à l'épreuve : que l'utilisateur
puisse inscrire sa propre application chez le fournisseur.

Microsoft documente que la connexion au centre d'administration Entra avec un compte
personnel (Outlook.com, Hotmail) rattache au tenant « Microsoft Services », dans lequel
aucun annuaire ne permet d'agir. La création automatique d'un annuaire lié à un compte
personnel a été supprimée ; la voie officielle est de créer un compte Azure, donc un tenant.
L'inscription d'application reste gratuite, mais l'ouverture du compte Azure demande une
carte bancaire. Constaté en usage réel le 15 septembre 2026, erreur `AADSTS50020`.

Conséquence : pour le public visé — des particuliers qui migrent une boîte personnelle —
l'OAuth Microsoft de cette application n'est pas praticable. Poursuivre les lots 4b à 4d
(validation XOAUTH2 réelle, coffre système, particularités des fournisseurs) reviendrait à
perfectionner un chemin que ces utilisateurs ne peuvent pas emprunter.

Ce qui reste vrai et utilisable : Gmail continue de fonctionner avec un mot de passe
d'application, sans OAuth. Le code du lot 4a reste en place et fonctionnel pour qui dispose
déjà d'un tenant Entra — il n'est ni retiré ni désactivé, seulement non validé et non promis.

Ce qui rouvrirait la phase 4 : soit une identité d'application embarquée dans le projet et
inscrite au nom du mainteneur — décision non prise, elle l'engage personnellement — soit un
changement de politique de Microsoft.

## Prochaine action

Lancer le workflow « Paquet Windows » et corriger ce qu'il révèle, en commençant par la
construction du moteur. Puis installer le paquet produit sur une machine Windows dépourvue
de Python et de Perl, y faire une migration de référence, et consigner ici le résultat.
Tant que ces deux étapes ne sont pas franchies, l'installateur n'est pas annoncé.

Rappel du plan initial (lot 3d : déplacement
et miroir, désactivés par défaut, avec aperçu et confirmation séparés des suppressions,
testés sur comptes jetables avant validation.

Rappel de l'ordre initial des lots (lot 3b : correspondance automatique des dossiers proposée puis validée par
   l'utilisateur. Lot 3c : historique local et export de rapports sans secrets.
   Lot 3d : déplacement et miroir, désactivés par défaut, avec aperçu et confirmation
   séparés des suppressions, testés sur comptes jetables avant validation.
