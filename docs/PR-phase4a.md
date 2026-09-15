# Texte de la PR — phase 4, lot 4a

Titre : Phase 4 (lot 4a) : connexion OAuth pour IMAP

- Authentification OAuth en plus du mot de passe : Microsoft (obligatoire, Microsoft ayant
  coupé l'authentification de base) et Google (optionnelle, le mot de passe d'application
  fonctionnant toujours). Flux code + PKCE, navigateur système, boucle locale, `state` vérifié.
- **Aucune identité d'application embarquée.** L'utilisateur inscrit la sienne ; procédure
  pas à pas dans `docs/OAUTH.md`. Motif du choix dans ROADMAP.md et docs/ARCHITECTURE.md.
- Le jeton est traité comme un mot de passe : masqué au journal, hors profils et historique,
  effacé dès que l'identité ou l'inscription change, et jamais passé en argument — imapsync
  lit `--oauthaccesstoken{1,2}` depuis un fichier 0600 du répertoire temporaire de l'opération.
- Profils : `auth` et `provider` ajoutés ; les profils antérieurs se relisent inchangés.

Validation locale Linux : 198 tests de socle (28 nouveaux), dont le flux complet contre un
vrai serveur HTTP de boucle locale.

**Ce lot n'est pas validé contre un serveur IMAP réel** : ni GreenMail ni pymap ne font
XOAUTH2. Aucune compatibilité Gmail, Outlook.com ou Microsoft 365 n'est annoncée ; STATUS.md
le consigne. Le lot 4b a pour objet exclusif de combler ce trou.
