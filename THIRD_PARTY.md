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

Aucun binaire tiers n'est embarqué dans la livraison de sources v0.1. La phase de
packaging devra fournir les notices, textes et obligations correspondant aux
composants effectivement distribués.
