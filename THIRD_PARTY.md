# Composants tiers

Le code original de Mailbox Synchroniseur est sous licence MIT.

- imapsync, Gilles Lamiral : moteur externe non inclus dans cette archive.
  Licence NLPL, https://imapsync.lamiral.info/LICENSE ; sources :
  https://github.com/imapsync/imapsync . Les licences de ses dépendances restent
  applicables lors d'une future redistribution du moteur.
- PySide6 / Qt for Python : installé séparément par pip ; licences LGPLv3/GPLv3
  ou commerciales selon les composants. Cette application utilise QtCore,
  QtGui et QtWidgets. https://doc.qt.io/qtforpython-6/licenses.html
- Python et bibliothèque standard : licence PSF, https://docs.python.org/3/license.html
- pytest : dépendance de développement, MIT, https://github.com/pytest-dev/pytest

## Composants distribués dans l'installateur Windows

La livraison de sources n'embarque aucun binaire tiers. L'installateur Windows
construit par `.github/workflows/package.yml` en distribue, avec leurs obligations :

- **imapsync** (Gilles Lamiral), licence NLPL, dont le texte intégral est :
  « No limits to do anything with this work and this license. » La redistribution
  d'un binaire construit soi-même est donc explicitement permise. Le binaire est
  construit par `packaging/build-engine.ps1` à partir du commit amont épinglé
  `93654c6025ff7814f983ab74dd300f9bed9282d9`, vérifié par empreinte SHA-256.
- **Perl et les modules CPAN** nécessaires à imapsync, embarqués par PAR::Packer
  dans le binaire du moteur. Perl est sous double licence Artistic 1.0 / GPL-1.0+ ;
  les modules CPAN portent leurs licences respectives, majoritairement identiques.
  La liste des modules installés figure dans `packaging/build-engine.ps1`.
- **Python** et sa bibliothèque standard, embarqués par PyInstaller, licence PSF.
- **PySide6 / Qt** sous LGPLv3. L'application est empaquetée en mode dossier
  (« onedir »), jamais en fichier unique : les bibliothèques Qt restent des fichiers
  distincts, visibles et remplaçables par l'utilisateur, ce qui satisfait l'exigence
  de relink de la LGPLv3. Seuls QtCore, QtGui et QtWidgets sont utilisés, et la
  construction installe `PySide6-Essentials`. Sources amont :
  https://download.qt.io/official_releases/QtForPython/
- **OpenSSL**, embarqué via les modules TLS de Perl, licence Apache 2.0.

Le fichier LICENSE du projet et ce fichier sont installés à côté de l'application,
et l'installateur les présente avant et après l'installation.

Pour obtenir les sources d'un composant distribué ou une version modifiée de Qt,
se reporter aux adresses ci-dessus ; le projet ne modifie aucun de ces composants.

Dépendances des essais IMAP uniquement, téléchargées séparément :

- GreenMail standalone 2.1.3, Apache-2.0 : https://github.com/greenmail-mail-test/greenmail
- pymap 0.36.7, MIT : https://github.com/icgood/pymap
- Java / OpenJDK et OpenSSL : outils du système de test, non embarqués.

Les sources et empreintes des téléchargements du moteur et de GreenMail sont dans
`scripts/prepare_integration.py`. Ces outils ne sont ni installés ni exécutés par
le lancement normal de l'application. Aucun serveur IMAP ne fait partie du produit.

- Dovecot 2.3.21 : serveur des tests de quota strict, installé séparément depuis
  Ubuntu 24.04, jamais embarqué dans l'application. Sources et licences :
  https://github.com/dovecot/core/tree/2.3.21 ; notices du paquet Ubuntu applicables.
