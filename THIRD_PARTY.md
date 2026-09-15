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

Aucun binaire tiers n'est embarqué dans la livraison de sources v0.2. La phase de
packaging devra fournir les notices, textes et obligations correspondant aux
composants effectivement distribués.

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
