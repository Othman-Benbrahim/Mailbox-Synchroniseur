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

## Suivi de la livraison v0.2 alpha 1

Le périmètre et l'ordre du plan version 1 sont conservés. La sélection/mise en
correspondance des dossiers et le bilan sont implémentés. Les essais du moteur
réel sur serveurs isolés passent ; détails et preuves dans STATUS.md et
`docs/INTEGRATION.md`. Le refus APPEND d'un serveur à quota strict reste à qualifier :
la phase 2 demeure ouverte, sans commencer la phase 3.
