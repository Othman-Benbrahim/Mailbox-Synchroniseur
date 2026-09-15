# Mailbox Synchroniseur — roadmap de référence

Version du plan : 1 — 14 septembre 2026.
Nom de travail : Mailbox Synchroniseur. Application de bureau libre, en français.
Windows prioritaire ; architecture compatible Linux et macOS.

## Règle de suivi

Respecter l'ordre des phases ci-dessous. À chaque livraison, actualiser STATUS.md
avec les fonctionnalités réellement présentes, les vérifications et le prochain
jalon. Une phase n'est validée que si ses critères sont satisfaits. Ne pas confondre
code implémenté et compatibilité vérifiée. Toute évolution de périmètre est consignée
ici avec sa raison ; un changement majeur est discuté avec l'utilisateur.

## Phase 0 — cadrage (v0.1)

- Définir périmètre, architecture et décisions dans docs/ARCHITECTURE.md.
- Publier roadmap, licence du code original et notices des dépendances.
- Séparer configuration, moteur de transfert et interface.

Validation : documentation et structure du projet présentes.

## Phase 1 — première application exécutable (v0.1 alpha)

- Interface PySide6 française avec source et destination clairement identifiées.
- Profils JSON ne contenant aucun mot de passe ; secrets limités à la session.
- Choix d'un exécutable imapsync déjà installé (le moteur n'est pas encore inclus).
- TLS obligatoire, certificats et nom d'hôte vérifiés, aucun repli en clair.
- Test des deux connexions, simulation, copie unidirectionnelle, arrêt.
- Simulation réussie obligatoire avant copie ; toute modification l'invalide.
- Aucun mode de suppression, aucune option shell libre.
- Journal de session filtré, interface utilisable pendant l'opération.
- Lanceurs Windows et Linux/macOS depuis les sources.

Validation : tests du contrat de commande, secrets, profils, cycle de vie des
processus et parcours UI ; ouverture effective de l'interface. Cette validation
ne vaut pas validation des migrations réelles (phase 2).

## Phase 2 — migrations vérifiées (v0.2)

- Installer une version précise d'imapsync et des serveurs IMAP de test isolés.
- Tester messages MIME, pièces jointes, dates, états, dossiers Unicode et imbriqués.
- Vérifier absence de suppression, reprise après coupure et absence de recopies.
- Tester certificat non fiable, mauvais nom d'hôte, refus d'identifiants, quota plein.
- Ajouter un bilan structuré : copiés, ignorés, erreurs et contrôle destination.
- Ajouter sélection et correspondance explicites des dossiers.

Validation : tests d'intégration réels reproductibles ; comparaison des messages
source/destination ; aucune suppression inattendue. Le MVP n'est recommandé pour
une migration importante qu'après ce jalon.

## Phase 3 — fonctionnalités avancées (v0.3)

- Filtres par dates et taille ; estimation du volume ; progression et temps restant
  uniquement quand les données du moteur permettent un calcul fiable.
- Correspondance automatique proposée et validée par l'utilisateur.
- Déplacement et miroir : aperçu explicite des suppressions, confirmation séparée.
- Historique local et export de rapports sans secrets ; limites de débit.

Validation : tests des filtres et suppressions sur comptes jetables ; actions
  destructrices désactivées par défaut et identifiées dans le bilan.

## Phase 4 — authentification et fournisseurs (v0.4)

- OAuth Google et Microsoft avec connexion dans le navigateur système.
- Renouvellement des jetons et stockage dans le coffre du système.
- Documentation des inscriptions d'applications et consentements nécessaires.
- Tests Gmail (labels) et Microsoft 365 ; erreurs et quotas propres aux fournisseurs.

Validation : connexions et renouvellements réellement testés ; aucune promesse de
compatibilité sur un fournisseur non testé. Authentification par mot de passe ou
mot de passe d'application uniquement avant ce jalon, si le fournisseur l'autorise.

## Phase 5 — automatisation locale (v0.5)

- Plusieurs profils, file d'attente, tâches planifiées et notifications.
- Intégration au coffre du système pour les tâches sans interaction.
- Pas d'exécutions concurrentes du même profil ; reprise et journalisation.

Validation : redémarrage, veille, réseau indisponible, expiration des accès et
prévention des doublons d'exécution testés. Ordinateur actif nécessaire.

## Phase 6 — distribution (v1.0)

- Construction reproductible d'imapsync et de ses dépendances ; notices et licences.
- Installateur Windows autonome, puis distributions Linux et macOS.
- Test sur machines vierges sans Python/Perl installés ; désinstallation propre.
- Documentation, procédure de mise à jour et publication des sources.

Validation : paquet construit sur chaque OS cible et migration de référence réussie.
Signature des binaires selon les moyens disponibles ; ne pas annoncer une signature
ou notarisation qui n'a pas été réalisée.

## Hors périmètre de cette roadmap

Synchronisation bidirectionnelle de deux boîtes actives ; contacts et calendriers ;
archive locale EML/MBOX ; service web hébergé. Ces besoins nécessitent un autre lot.

## Suivi de la livraison v0.2 alpha 1 — 15 septembre 2026

Le périmètre et l'ordre du plan version 1 sont conservés. **La phase 2 est terminée
sur comptes de test isolés.** La sélection et les correspondances de dossiers,
le bilan et les tests de migration réels sont présents.

Le [run 34911811074](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34911811074) a réussi
sur le commit `0eb09bfabda1a082bed6d9e881810373383f0324` : socle Linux/Windows et
14 essais IMAP Linux. Le dernier critère, refus APPEND OVERQUOTA par Dovecot 2.3.21
puis reprise après augmentation du quota, est validé. La PR #2 est fusionnée dans
`92064b430aa3f8f14d504728b013ca013b3f83b0`.

STATUS.md consigne les preuves et leurs limites. Cette clôture ne vaut pas
qualification de migrations Windows/macOS, de fournisseurs réels ou de grands volumes.
La phase 3 est la prochaine étape, sans code de phase 3 livré dans cette mise à jour.

## Suivi de la livraison v0.3 alpha 1 — 15 septembre 2026

Le périmètre et l'ordre du plan version 1 sont conservés. La phase 3 est découpée en
lots livrés par PR séparées, dans cet ordre : 3a filtres par dates et taille et
estimation du volume ; 3b correspondance automatique des dossiers ; 3c historique
local et export de rapports ; 3d déplacement et miroir. Raison : isoler le premier
code de suppression (3d) des fonctions sans risque, et permettre une validation
IMAP réelle par lot.

**Le lot 3a est validé et fusionné** (PR #4, branche `phase-3/filtres`) : le
[run 34916209481](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34916209481) a réussi sur le commit `10637f2c862acba1758a7ee351f24b9a42f16c27`, fusionné dans `1f3ddf5987369f87b8a49722655f4d77d67ae48f`
— 111 tests de socle sous Linux et Windows, 18 essais IMAP réels. STATUS.md en
consigne les preuves et les limites. Progression
et temps restant restent absents : les données du moteur (`ETA` fondée sur les
tailles de dossiers) ne sont pas jugées assez fiables pour un affichage.

Écart consigné : la simulation ne peut pas appliquer le filtre de taille sans
télécharger la source (`--nodry1`). L'estimation est donc un maximum quand ce filtre
est actif, et le bilan l'indique. Choix discuté et accepté pour ce lot.

## Suivi de la livraison v0.3 alpha 2 — 15 septembre 2026 (lot 3b)

**Lot 3b validé et fusionné** : découverte des dossiers et proposition de correspondance,
validée par l'utilisateur dans le tableau existant, sans lever l'obligation de simulation.
Le [run 34917709552](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34917709552) a réussi sur le commit `7065672cc367272950aca0d502ba1cb998ce80f9`, fusionné dans `74c1b706e60019a02cca078674c0ec378c462072`.

Écart consigné : l'application émet désormais elle-même une commande IMAP (`LIST`, lecture
seule) pour la découverte. AGENTS.md interdit un moteur IMAP maison à la place d'imapsync ;
un `LIST` sans transfert n'en est pas un, et l'alternative par analyse de la sortie
d'imapsync a été écartée. Décision prise après discussion. Voir docs/ARCHITECTURE.md.

## Suivi de la livraison v0.3 alpha 3 — 15 septembre 2026 (lot 3c)

**Lot 3c validé et fusionné** : historique local et export de rapports sans secrets, au
format JSON, un fichier par exécution. Le [run 34918761935](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34918761935) a réussi sur le commit
`b5b68cfdef206c96dc86590e214cdc4e1ae6e0e8`, fusionné dans `ffd4018e2c196aca1e9cd60a2e7c122652bf2e75` (144 / 144 / 21, aucun essai ignoré). Décision de format prise avec l'utilisateur (JSON plutôt que
SQLite) ; motifs dans docs/ARCHITECTURE.md.

Reste de la phase 3 : lot 3d, déplacement et miroir. Premier code de suppression du projet,
donc désactivés par défaut, aperçu explicite des suppressions et confirmation séparée,
testés sur comptes jetables avant toute validation. Les limites de débit prévues par la
phase 3 seront traitées avec ce lot ou consignées comme abandonnées.

## Suivi de la livraison v0.3 alpha 4 — 15 septembre 2026 (lot 3d)

Lot 3d implémenté : miroir, première et seule fonction de suppression du produit.

Décisions prises et consignées :
- **Miroir seul.** Le déplacement (`--delete1`, supprimer à la source après copie) n'est pas
  livré et sort du périmètre de la phase 3. Motif : irréversibilité sur la boîte que
  l'utilisateur est en train de migrer. Sera rouvert seulement si un besoin réel apparaît.
- **Marquage par défaut, vidage en option.** Le miroir marque `\Deleted` sans expunger ;
  imapsync expungerait de lui-même, ce comportement est donc explicitement désactivé.
- **Confirmation saisie.** Aperçu chiffré issu de la simulation, puis saisie de `SUPPRIMER`.
- **Limites de débit abandonnées** du périmètre de la phase 3, faute de besoin démontré ;
  consigné ici plutôt que laissé en suspens.
- **Progression et temps restant non livrés** : la roadmap les conditionnait à des données
  fiables du moteur ; l'ETA d'imapsync dépend de `foldersizes` et ne l'est pas assez.

**Le lot 3d est validé et fusionné** : le run de la PR #10 a réussi sur le commit
`562d67e`, fusionné dans `25750fc` (170 tests de socle sous Linux et Windows,
23 essais IMAP réels). Après une première tentative en conflit documentaire, le lot a été
régénéré sur `1b38ef9` sans modification de code.

La phase 3 est complète : filtres et volume (3a), découverte et
correspondance (3b), historique et export (3c), miroir (3d). La phase 4 (OAuth Google et
Microsoft) est la suite prévue.

## Clôture de la phase 3 — 15 septembre 2026

La phase 3 est terminée. Les quatre lots sont fusionnés, chacun après un run vert :
3a filtres et estimation du volume, 3b découverte et correspondance des dossiers,
3c historique local et export de rapports, 3d miroir. STATUS.md porte le tableau des
preuves (runs, commits testés, commits de fusion, nombres de tests).

Trois éléments du périmètre initial ne sont pas livrés, et c'est délibéré :
- **déplacement** (copier puis supprimer à la source) : écarté, irréversible sur une boîte
  en cours de migration ;
- **limites de débit** : abandonnées, aucun besoin démontré ;
- **progression et temps restant** : la roadmap les conditionnait à des données fiables du
  moteur ; l'ETA d'imapsync dépend de `foldersizes` et ne l'est pas assez.

La phase 4 (OAuth Google et Microsoft) suit, sans anticipation : rien n'en est commencé.
