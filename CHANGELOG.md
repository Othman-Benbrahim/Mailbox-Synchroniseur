# Journal des versions

## 0.6.0 — 15 septembre 2026

Première version publiée. Application de bureau en français pour copier des messages
d'une boîte IMAP vers une autre, en pilotant le moteur libre imapsync.

### Ce qui est vérifié

Les migrations sont testées contre de vrais serveurs IMAP jetables — GreenMail 2.1.3,
pymap 0.36.7 et Dovecot 2.3.21 — avec imapsync 2.314 réel, à chaque intégration continue :

- contenu MIME et pièces jointes comparés par SHA-256, dates internes et états conservés ;
- dossiers Unicode et imbriqués, sélection exacte, renommage à destination ;
- aucune suppression inattendue, aucune recopie lors d'un second passage ;
- reprise après coupure TCP réelle, refus de quota strict puis reprise après relèvement ;
- certificats non fiables et noms d'hôte incorrects refusés, sans repli en clair ;
- filtres par dates et par taille, découverte des dossiers et proposition de correspondance ;
- miroir : suppressions uniquement à destination, jamais à la source.

L'installateur Windows a été installé et utilisé sur une machine dépourvue de Python et de
Perl : le paquet est autonome. Il embarque un moteur imapsync construit depuis la source
amont épinglée, vérifié par empreinte SHA-256.

223 tests de socle sous Linux et Windows, 23 essais IMAP réels sous Linux.

### Ce qui n'est pas vérifié

- macOS, les très gros volumes, et les migrations Windows au-delà de l'essai d'installation.
- Gmail et Microsoft 365 en conditions réelles : aucune compatibilité fournisseur n'est
  annoncée.
- Les binaires ne sont **ni signés ni notariés** : Windows affiche un avertissement
  SmartScreen. Aucune signature n'est revendiquée.
- La désinstallation propre n'a pas été vérifiée méthodiquement.

### Ce qui n'a pas de chemin praticable

**Outlook.com et Microsoft 365.** Microsoft n'accepte plus le mot de passe sur IMAP, et
l'inscription d'application nécessaire à OAuth exige un tenant Entra qu'un compte personnel
n'a pas — la voie officielle passe par la création d'un compte Azure. La connexion OAuth
existe dans l'application et fonctionne pour qui dispose déjà d'un tenant, mais elle n'a été
validée contre aucun serveur réel. Voir `docs/OAUTH.md`.

Pour Gmail, le mot de passe d'application fonctionne, avec la validation en deux étapes
activée sur le compte.

### Limites de conception, assumées

- Copie dans un seul sens ; pas de synchronisation bidirectionnelle.
- Une simulation réussie est obligatoire avant toute copie, et toute modification l'invalide.
- Les mots de passe ne sont jamais enregistrés : ni dans les profils, ni dans l'historique,
  ni dans le journal, ni sur la ligne de commande.
- Le miroir est la seule fonction capable de supprimer, uniquement à destination, désactivé
  par défaut, et il exige une confirmation saisie au clavier.
- Pas de planification, pas de contacts ni de calendriers, pas de coffre système.

### Installation

Windows : télécharger l'installateur de cette version et l'exécuter. Rien d'autre n'est
nécessaire. Linux et macOS : lancer depuis les sources, avec Python 3.11 ou plus récent et
un imapsync fonctionnel ; aucun paquet n'est fourni.

### Licences

Code original sous licence MIT. Le paquet Windows distribue imapsync (NLPL), Perl et des
modules CPAN, Python, Qt/PySide6 (LGPLv3, bibliothèques remplaçables) et OpenSSL.
Voir `THIRD_PARTY.md`.
