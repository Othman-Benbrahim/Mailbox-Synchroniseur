# Instructions pour la suite du développement

Lire ROADMAP.md et STATUS.md avant toute modification. Suivre les phases dans
l'ordre ; mettre à jour les preuves de validation et les limites à chaque livraison.
Ne jamais annoncer une compatibilité ou une migration réelle sur la seule base
d'un faux processus. Respecter les garde-fous du produit : pas de shell, pas de
secrets en profils/journaux/arguments, TLS obligatoire, copie après simulation.
Le miroir (phase 3, lot 3d) est la seule fonction capable de supprimer des messages, et
uniquement à destination : ne jamais ajouter --delete1 ni toucher la boîte source. Ne pas
affaiblir ses garde-fous (case décochée au démarrage, jamais dans un profil, simulation du
même plan exigée, aperçu chiffré, confirmation saisie, pas de vidage par défaut). Ne pas ajouter un moteur IMAP
maison à la place d'imapsync. Ne pas créer de serveur web pour cette application.
