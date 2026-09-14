# État du projet — 0.2.0 alpha 1

Reprise du dépôt GitHub initial `Othman-Benbrahim/Mailbox-Synchroniseur`, commit
`eedaa95843118c4d2ed23ec791cf50f319ce00ae`. Cette livraison prolonge ce socle.

| Phase | État | Preuve / suite |
| --- | --- | --- |
| 0 — Cadrage | Terminée | Roadmap, architecture, licence et structure initiales conservées |
| 1 — Application exécutable | Socle alpha conservé | Tests existants maintenus, interface Qt ouverte |
| 2 — Migrations vérifiées | Implémentée, qualification encore partielle | 13 tests IMAP réels réussis ; refus APPEND par quota strict restant |
| 3 — Fonctions avancées | À faire | Attendre la fermeture du jalon 2 |
| 4 — OAuth et fournisseurs | À faire | Google / Microsoft non validés |
| 5 — Automatisation | À faire | Aucun service en arrière-plan |
| 6 — Distribution autonome | À faire | Aucun installateur ou moteur embarqué livré |

## Fonctionnalités livrées

- Onglet de sélection explicite des dossiers et correspondance source/destination.
- Noms Unicode et sous-dossiers ; destination vide = même nom ; collisions refusées.
- Profils JSON v2 sans mots de passe, compatibilité de lecture v1.
- Toute modification du périmètre invalide la simulation ; inversion des mappings
  avec les comptes ; configuration désactivée durant l'exécution.
- Bilan du moteur : copiés, ignorés, erreurs, absents et confirmation conditionnelle
  de présence à destination. Données absentes affichées « non communiqué ».
- Tests d'intégration reproductibles et workflow GitHub Actions ajouté.

## Preuves locales

Linux, Python 3.12, PySide6 6.11.2, pytest 9.1.1, imapsync 2.314,
GreenMail 2.1.3 et pymap 0.36.7 : **69 tests réussis en 68,49 s**, dont 56 tests du
socle/interface et 13 essais IMAP réels. Voir `docs/validation-phase2.xml` et
`docs/INTEGRATION.md` pour la méthode, les versions et les commandes.
Les fixtures comparent les SHA-256 MIME, pièces jointes, dates et états. La coupure
réseau réelle, la reprise sans recopies, les refus TLS et d'identifiants sont vérifiés.
La construction/installation éditable 0.2.0a1 et le téléchargement vérifié des
outils de test ont réussi. Les deux onglets de l'interface ont été ouverts et leurs captures inspectées.

Les mots de passe restent absents des arguments du moteur, profils et journal
filtré. Les expunges, suppressions et resynchronisations d'états restent désactivés.

## Limites et prochain jalon

Le test de quota vérifie un quota annoncé plein et le statut d'échec du moteur.
GreenMail continue d'accepter APPEND : il reste à tester un serveur appliquant un
quota strict et refusant effectivement l'ajout. **La phase 2 n'est donc pas déclarée
entièrement terminée.** Ne pas passer aux modes destructeurs de phase 3.

Windows/macOS, fournisseurs réels, gros volumes et installateur autonome ne sont
pas validés. Le workflow CI est fourni ; aucun résultat GitHub Actions n'est revendiqué.
Les contrôles SHA-256 appartiennent aux tests, pas au bilan affiché par l'application.
