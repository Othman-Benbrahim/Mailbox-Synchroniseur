# Essais IMAP de la phase 2

La suite lance **imapsync 2.314 réel**, sans remplacer sa commande de transfert,
contre des comptes jetables locaux. GreenMail standalone 2.1.3 sert le TLS direct ;
pymap 0.36.7 sert STARTTLS ; Dovecot 2.3.21 applique le quota strict.
Les serveurs sont des dépendances de test externes au
produit. Aucun accès utilisateur ni serveur de messagerie externe n'est utilisé.

## Reproduire sous Ubuntu 24.04

Python 3.12, Java 17 avec `keytool`, OpenSSL et Perl sont nécessaires.
Depuis la racine du dépôt :

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends openjdk-17-jdk-headless openssl libegl1 libgl1 dovecot-imapd \
  libdigest-hmac-perl libencode-imaputf7-perl libfile-copy-recursive-perl \
  libio-socket-ssl-perl libio-tee-perl libmail-imapclient-perl \
  libterm-readkey-perl libunicode-string-perl libreadonly-perl \
  libsys-meminfo-perl libregexp-common-perl libfile-tail-perl
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,integration]'
.venv/bin/python scripts/prepare_integration.py
export MAILBOX_INTEGRATION=1
export MAILBOX_DOVECOT=/usr/sbin/dovecot
export MAILBOX_IMAPSYNC="$PWD/.test-tools/imapsync"
export MAILBOX_GREENMAIL_JAR="$PWD/.test-tools/greenmail-2.1.3.jar"
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Le test Dovecot doit être lancé avec un utilisateur ordinaire, sans sudo. Il crée
ses propres processus, ports et dossiers : voir [QUOTA-STRICT.md](QUOTA-STRICT.md).
Sans MAILBOX_DOVECOT, ce test seul est ignoré ; la CI renseigne obligatoirement cette variable.

Les téléchargements vérifient leurs SHA-256. La fixture vérifie également le moteur,
le JAR et la version pymap avant de démarrer. Les certificats de test expirent après
2 jours et sont régénérés à chaque session ; aucun certificat ou secret de test
n'est installé globalement. `SSL_CERT_FILE` est limité aux processus de test.
Les serveurs écoutent sur des ports aléatoires de boucle locale, puis sont arrêtés.
Lancer les tests séquentiellement, sans pytest-xdist.

Les versions amont utilisées sont identifiées dans `scripts/prepare_integration.py` :

| Dépendance | Référence |
| --- | --- |
| imapsync 2.314 | commit `93654c6025ff7814f983ab74dd300f9bed9282d9` |
| SHA-256 imapsync | `89faed96f7c389723ddd7e78a00421b90d5b85bf79407fcf1b11209f3d4d7416` |
| GreenMail 2.1.3 | Maven Central, distribution standalone |
| SHA-256 GreenMail | `9457fdaf45ded6c87bf84a321a5ced4b4b5e72b1d03686b778df381378afc4c8` |
| pymap | paquet Python `pymap==0.36.7` |
| Dovecot | version 2.3.21, paquet Ubuntu 24.04 `dovecot-imapd` |

## Ce qui est réellement vérifié

| Cas | Observation exigée |
| --- | --- |
| Simulation | Source et destination inchangées |
| Copie TLS direct | SHA-256 des messages MIME complets identiques, pièce jointe binaire incluse |
| Dates et états | INTERNALDATE, Seen, Flagged, Answered conservés ; Deleted non propagé |
| Absence de suppression | Source inchangée, ancien message de destination conservé |
| Deuxième copie | Zéro message transféré, destination identique |
| Dossiers | Nom Unicode et imbriqué, sélection exacte, renommage, INBOX hors sélection inchangée |
| Identifiants erronés | Refus réel côté source et côté destination |
| Certificats | Certificat non fiable et nom d'hôte incorrect refusés en TLS direct et STARTTLS |
| STARTTLS | Copie réelle et intégrité ; serveur sans STARTTLS refusé sans repli en clair |
| Quota annoncé plein | Erreur réelle d'imapsync, échec dans QProcess, aucune confirmation de migration complète |
| Quota strict Dovecot | Refus APPEND OVERQUOTA, zéro transfert et aucune perte ; après relèvement du quota, nouvelle simulation et copie intègre sans recopies |
| QProcess | Lancement du véritable moteur depuis le runner, bilan issu de ses sorties |
| Coupure réseau | Fermeture réelle d'un relais TCP opaque après le premier transfert, état partiel vérifié, nouvelle simulation et reprise sans recopies |
| Filtre par dates (lot 3a, TLS direct et STARTTLS) | Seul le message dont la date interne est dans l'intervalle est copié ; nombre à copier et volume estimé égaux au RFC822.SIZE annoncé ; volume transféré égal aux octets réels du message (égal à l'estimation sur pymap, qui annonce des tailles exactes ; GreenMail les annonce sans en-têtes) ; élargissement sans recopie |
| Filtre par taille (lot 3a, TLS direct et STARTTLS) | Message au-dessus de `--maxsize` non copié, compté par imapsync comme ignoré et absent, identifié comme exclu par le filtre ; copie confirmée ; simulation annoncée comme maximum ; copie sans filtre ensuite sans recopie |
| Découverte et proposition (lot 3b, TLS direct et STARTTLS) | `LIST` réel sur les deux comptes avec certificat vérifié ; mauvais mot de passe et mauvais nom d'hôte refusés ; rien d'écrit par la découverte ; proposition `Envoyés → Sent Items`, dossier Unicode imbriqué conservé ; copie réelle pilotée par la proposition, contenu vérifié par SHA-256 |
| Historique d'une copie réelle (lot 3c) | L'entrée JSON d'une copie réelle reprend les compteurs du moteur, ne contient ni le mot de passe ni `IMAPSYNC_PASSWORD`, et son rapport exporté non plus |

Dans le test de coupure uniquement, le débit est limité à un message par seconde
pour couper avant la fin. Le processus est ensuite arrêté pour borner ses tentatives
de reconnexion. Le relais ne déchiffre pas TLS et ne fabrique aucune réponse IMAP.
La reprise est un nouveau lancement du moteur, pas la reprise automatique d'un UID
mémorisé par l'application.

## Deux tests de quota complémentaires

GreenMail annonce le quota et son utilisation, mais accepte encore APPEND quand
la limite est dépassée. Ce premier test vérifie le statut d'échec et la conservation
des anciens messages ; il ne constitue pas, à lui seul, une preuve de refus serveur.

Le test `test_dovecot_strict_quota_refuses_append_and_resumes` utilise Dovecot 2.3.21.
Il exige le refus APPEND `OVERQUOTA`, puis vérifie la copie après augmentation du quota.
Il a réussi dans le run de fermeture ci-dessous. Voir [QUOTA-STRICT.md](QUOTA-STRICT.md).
Un échec de copie ne doit toujours pas être interprété comme une annulation des copies.

## Lot 3a — état de validation

Les deux essais de filtres sont paramétrés sur les deux familles de serveurs
(GreenMail en TLS direct, pymap en STARTTLS), soit 18 essais IMAP au total.
Les variantes pymap ont réussi localement contre le moteur réel le 15 septembre
2026 (`docs/validation-3a-pymap.xml`, exécution hors de la fixture de session du
dépôt faute d'accès à GreenMail). Les variantes GreenMail ont été validées par le
[run 34916209481](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34916209481) sur le commit `10637f2c862acba1758a7ee351f24b9a42f16c27` : 18 essais réussis, aucun ignoré.
Ce run a aussi révélé que GreenMail annonce un `RFC822.SIZE` sans en-têtes ; les
essais distinguent depuis la taille annoncée et les octets réellement transférés. Ces essais encodent des
lectures de la source imapsync (comptage des messages filtrés par taille parmi
les absents, non-application du filtre de taille en `--dry`) confirmées par cette
exécution locale.

## Lot 3b — état de validation

L'essai `test_discovery_lists_folders_over_verified_tls_and_proposal_drives_a_real_copy`
est paramétré GreenMail/pymap (20 essais IMAP au total). La variante pymap a réussi
localement contre imapsync 2.314 réel le 15 septembre 2026 (`docs/validation-3b-pymap.xml`),
la variante GreenMail par le [run 34917709552](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34917709552) sur le commit `7065672cc367272950aca0d502ba1cb998ce80f9`, dont les trois
tâches sont au vert.

## Lot 3c — état de validation

L'essai `test_history_of_a_real_run_carries_no_secret_and_matches_the_engine` utilise la
fixture GreenMail `pair` et le Runner réel. Il a été exécuté localement avec pymap
substitué à GreenMail (indisponible dans ce runtime), rapport
`docs/validation-3c-pymap.xml` : cette exécution vaut pour la logique de l'essai, pas pour
la fixture GreenMail elle-même, qui est validée par le run GitHub de la PR du lot 3c.
Les essais écrivent leur historique dans un dossier temporaire (`MAILBOX_HISTORY_DIR`) :
aucun test ne touche l'historique réel de l'utilisateur.

## Résultat de fermeture — 15 septembre 2026

Le [run 34911811074](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34911811074) a réussi
sur le commit `0eb09bfabda1a082bed6d9e881810373383f0324` de la PR #2 :
56 tests du socle/interface sous Ubuntu 24.04, les mêmes 56 sous windows-latest,
et 14 essais IMAP réels sous Ubuntu 24.04. Python 3.12 est configuré pour chaque tâche.
La tâche IMAP active explicitement MAILBOX_INTEGRATION et MAILBOX_DOVECOT :
le test de quota strict fait partie du jalon, il ne doit pas être ignoré.
Le rapport `imap-results.xml` est conservé dans l'artefact du run GitHub.
La phase 2 est donc fermée pour ce périmètre ; STATUS.md en consigne les limites.

## Preuve locale historique

Avant ajout de Dovecot, la suite avait réussi sous Linux, Python 3.12,
PySide6 6.11.2 et pytest 9.1.1 : 69 tests en 68,49 s, dont 13 essais IMAP et
56 tests du socle. `docs/validation-phase2.xml` contient ce résultat historique.
Ce fichier n'est pas le rapport des 14 essais de fermeture : cette preuve vient
de GitHub Actions, car les sockets Unix de Dovecot sont interdits dans le runtime local.

Les migrations Windows/macOS, Gmail/Microsoft 365 et les grands volumes ne sont
pas qualifiés. Les tests couvrent des fixtures déterministes, pas toutes les
heuristiques d'identification/dédoublonnage ni les particularités des fournisseurs.

Sources des dépendances et contrats consultés :
- https://github.com/imapsync/imapsync/tree/93654c6025ff7814f983ab74dd300f9bed9282d9
- https://github.com/greenmail-mail-test/greenmail
- https://github.com/icgood/pymap
- https://github.com/dovecot/core/tree/2.3.21
