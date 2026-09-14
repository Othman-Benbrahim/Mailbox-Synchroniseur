# Essais IMAP de la phase 2

La suite lance **imapsync 2.314 réel**, sans remplacer sa commande de transfert,
contre des comptes jetables locaux. GreenMail standalone 2.1.3 sert le TLS direct ;
pymap 0.36.7 sert STARTTLS. Les serveurs sont des dépendances de test externes au
produit. Aucun accès utilisateur ni serveur de messagerie externe n'est utilisé.

## Reproduire sous Ubuntu 24.04

Python 3.12, Java 17 avec `keytool`, OpenSSL et Perl sont nécessaires.
Depuis la racine du dépôt :

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends openjdk-17-jdk-headless openssl \
  libdigest-hmac-perl libencode-imaputf7-perl libfile-copy-recursive-perl \
  libio-socket-ssl-perl libio-tee-perl libmail-imapclient-perl \
  libterm-readkey-perl libunicode-string-perl libreadonly-perl \
  libsys-meminfo-perl libregexp-common-perl libfile-tail-perl
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,integration]'
.venv/bin/python scripts/prepare_integration.py
export MAILBOX_INTEGRATION=1
export MAILBOX_IMAPSYNC="$PWD/.test-tools/imapsync"
export MAILBOX_GREENMAIL_JAR="$PWD/.test-tools/greenmail-2.1.3.jar"
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

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
| QProcess | Lancement du véritable moteur depuis le runner, bilan issu de ses sorties |
| Coupure réseau | Fermeture réelle d'un relais TCP opaque après le premier transfert, état partiel vérifié, nouvelle simulation et reprise sans recopies |

Dans le test de coupure uniquement, le débit est limité à un message par seconde
pour couper avant la fin. Le processus est ensuite arrêté pour borner ses tentatives
de reconnexion. Le relais ne déchiffre pas TLS et ne fabrique aucune réponse IMAP.
La reprise est un nouveau lancement du moteur, pas la reprise automatique d'un UID
mémorisé par l'application.

## Limite précise du test de quota

GreenMail annonce le quota d'INBOX et son utilisation, mais accepte encore APPEND
quand la limite est dépassée. Le test garantit que l'avertissement réel du moteur
produit un échec et que les anciens messages restent intacts. Il ne prouve **pas**
le traitement d'un refus APPEND `OVERQUOTA` par un serveur à quota strict.
Ce cas reste nécessaire pour fermer complètement le jalon 2. La phase 3 ne commence
pas dans cette livraison. Ne pas interpréter l'échec comme une annulation des copies.

## Résultat de cette livraison

Sous Linux, Python 3.12, PySide6 6.11.2, pytest 9.1.1 : **69 tests réussis en 68,49 s**,
dont 13 essais d'intégration réelle et 56 tests du socle/interface. Le rapport JUnit
est conservé dans `docs/validation-phase2.xml`. Le moteur utilisait des modules Perl
installés depuis CPAN dans un répertoire de test local ; l'installation des paquets
apt ci-dessus et le workflow GitHub Actions n'ont pas été exécutés dans ce runtime.

Ni Windows/macOS, ni Gmail/Microsoft 365, ni un grand volume de messages n'ont été
qualifiés. Les tests couvrent des fixtures déterministes, pas toutes les heuristiques
d'identification/dédoublonnage d'imapsync ni les particularités de chaque fournisseur.

Sources des dépendances et contrats consultés :
- https://github.com/imapsync/imapsync/tree/93654c6025ff7814f983ab74dd300f9bed9282d9
- https://github.com/greenmail-mail-test/greenmail
- https://github.com/icgood/pymap
