# Texte historique de la PR #1

Ce texte décrit la première livraison, avant validation du quota strict dans la
PR #2. L'état actuel et la clôture de la phase 2 sont consignés dans [STATUS.md](../STATUS.md).

La première alpha pilotait imapsync sans preuve de migration réelle et copiait tous
les dossiers. Cette PR repart du commit initial eedaa95 pour ajouter un périmètre
explicite et un bilan fondé sur les observations du moteur.

- Sélection et correspondance manuelles des dossiers, Unicode et sous-dossiers.
- Profils JSON v2 sans secrets, avec lecture des profils v1.
- Bilan des copies, messages ignorés, erreurs et présence à destination.
- Tests avec imapsync 2.314 réel, GreenMail et pymap ; workflow CI Linux/Windows.

Validation locale Linux : 69 tests réussis, dont 13 essais IMAP réels. Les fixtures
vérifient MIME/pièces jointes par SHA-256, dates, états, absence de suppression,
reprise après coupure TCP, absence de recopies, TLS direct et STARTTLS.

Limite du jalon : quota annoncé plein testé, mais GreenMail continue d'accepter
APPEND. Un refus par serveur à quota strict reste à qualifier ; la phase 2 reste
ouverte et la phase 3 ne commence pas. Aucun résultat Windows ou fournisseur réel
n'est revendiqué. Voir STATUS.md et docs/INTEGRATION.md.
