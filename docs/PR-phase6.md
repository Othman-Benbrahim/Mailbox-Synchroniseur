# Texte de la PR — phase 6 : empaquetage Windows

Titre : Phase 6 : chaine d'empaquetage Windows (moteur, application, installateur)

Condition de possibilite verifiee d'abord : la licence NLPL d'imapsync se resume a
« No limits to do anything with this work and this license » et autorise donc
explicitement la redistribution d'un binaire construit soi-meme.

- `packaging/build-engine.ps1` : imapsync.exe construit avec PAR::Packer depuis le commit
  amont epingle, apres installation des modules CPAN ; echec si le binaire ne repond pas
  exactement 2.314 a --version.
- `packaging/mailbox-synchroniseur.spec` : PyInstaller en mode dossier. Exigence LGPLv3
  pour Qt (bibliotheques remplacables), pas un choix de confort.
- `packaging/installer.iss` : Inno Setup ; LICENSE et THIRD_PARTY.md installes a cote de
  l'application ; historique local non supprime a la desinstallation.
- `.github/workflows/package.yml` : les trois constructions sur windows-latest, avec
  verification que l'executable demarre, que le moteur annonce la bonne version, et que
  l'application detecte le moteur embarque.
- `bundle.py` + option `--version` : contrat entre le format du paquet et l'application.
  Le moteur livre est preselectionne et reste remplacable.
- THIRD_PARTY.md enumere les composants reellement distribues et leurs obligations.

Validation locale : 223 tests de socle, dont 11 nouveaux sur le contrat d'empaquetage.
L'empaquetage PyInstaller a ete verifie sous Linux (executable produit, --version correct).

**Rien de la chaine Windows n'a jamais ete execute** : pas de Windows, pas de Strawberry
Perl, pas d'Inno Setup dans l'environnement de developpement. La construction du moteur par
PAR::Packer est le point le plus incertain. Ce premier run est un test, pas une validation ;
STATUS.md le consigne et n'annonce aucun installateur eprouve.
