# État du projet — 0.1.0 alpha 1

Livraison initiale associée à la roadmap version 1 du 14 septembre 2026.

| Phase | État | Preuve / suite |
| --- | --- | --- |
| 0 — Cadrage | Terminée | ROADMAP.md, ARCHITECTURE.md, licence et structure modulaire |
| 1 — Application exécutable | Terminée au niveau du socle alpha | Installation Python réussie, fenêtre ouverte, 36 tests réussis |
| 2 — Migrations vérifiées | Prochaine étape | Moteur réel et serveurs IMAP isolés à installer ; aucun transfert réel validé |
| 3 — Fonctions avancées | À faire | Après validation de la phase 2 |
| 4 — OAuth et fournisseurs | À faire | Google / Microsoft non validés |
| 5 — Automatisation | À faire | Aucun service en arrière-plan |
| 6 — Distribution autonome | À faire | Aucun installateur ou moteur embarqué livré |

## Vérifications effectuées

Environnement : Linux, Python 3.12, PySide6 6.11.2, pytest 9.1.1.
Commande : `QT_QPA_PLATFORM=offscreen python -m pytest tests -q`.
Résultat final : **36 passed in 1.55s**.

- Construction et installation éditable du paquet réussies.
- Ouverture effective de la fenêtre Qt ; capture inspectée : docs/interface-alpha.png.
- Validation des hôtes, ports, mêmes comptes, identifiants et modes TLS.
- Commandes sans options de suppression ni mots de passe en arguments.
- Filtrage de l'indicateur Deleted, expunges et resynchronisation des états désactivés.
- Profils atomiques sans secrets ; profils incorrects refusés ; chemin d'exécutable
  non accepté automatiquement lors du chargement d'un profil.
- Processus enfant réel avec moteur simulé : succès, échec d'authentification,
  échec de démarrage, arrêt, prévention d'une deuxième exécution simultanée.
- Mots de passe masqués même lorsque leur sortie arrive en plusieurs fragments ;
  lignes trop longues omises ; nettoyage des fichiers temporaires.
- Parcours GUI : test d'accès, simulation, déverrouillage de la copie, invalidation
  après changement de mot de passe, copie, rétablissement après échec de démarrage.

## Limites de ces preuves

Les tests utilisent un **moteur simulé**, exécuté via QProcess. Aucun imapsync réel
ni serveur IMAP n'a été utilisé. Le passage des options TLS est testé ; leur effet
sur une négociation réelle n'a pas encore été vérifié. Aucun message utilisateur
n'a été lu, copié ou supprimé. Pas de validation Windows/macOS à ce stade.
Le lanceur Windows est fourni sous forme de BAT ; il n'est pas un installateur.

## Prochaine action conforme à la roadmap

Commencer la phase 2 : figer une version du moteur réel, monter deux serveurs IMAP
isolés avec certificats de test et fixtures MIME, vérifier intégrité et reprise,
puis ajouter la sélection et la correspondance des dossiers ainsi que le bilan.
Ne pas avancer aux options destructrices avant la réussite de ce jalon.
