# Dernier critère de la phase 2 : quota strict

Cette suite complète le test GreenMail, qui ne fait qu'annoncer un quota dépassé.
`test_dovecot_strict_quota_refuses_append_and_resumes` utilise deux instances réelles
de Dovecot 2.3.21 en TLS direct, avec le moteur imapsync 2.314 réel.

## Scénario exigé

1. Source avec une pièce jointe ; destination avec deux anciens messages.
2. Destination limitée à 64 Kio, backend de quota `count` avec `quota_vsizes = yes`, marge de dépassement nulle.
3. Simulation sans modification des boîtes.
4. Ajout IMAP direct refusé : réponse `NO` contenant `OVERQUOTA`.
5. Copie par le Runner/QProcess réel : erreur, zéro message transféré et aucune
   confirmation de migration complète. Source et destination inchangées.
6. Redémarrage de la même destination avec une limite de 1 Mio, Maildir conservé.
7. Nouvelle simulation, copie réussie, comparaison SHA-256 MIME/dates/états.
8. Nouvelle copie : zéro recopie et aucune perte des anciens messages.

Le serveur applique lui-même son quota. Aucun remplacement de commande APPEND,
aucun faux moteur et aucune réponse IMAP fabriquée ne sont utilisés.

## Isolation et reproductibilité

Installer `dovecot-imapd` sous Ubuntu 24.04. La fixture vérifie la version 2.3.21.
Elle suit la configuration Dovecot sans privilèges : même utilisateur système
pour les processus, aucun chroot, ports non privilégiés sur 127.0.0.1 seulement.
Chaque instance reçoit ses propres fichiers de configuration, Maildir, état et
sockets dans un répertoire temporaire court. La fixture n'utilise pas les fichiers
`/etc/dovecot` et ne commande jamais le service système.

Dans la VM GitHub jetable, le workflow arrête le service système par défaut après
installation du paquet. Les deux serveurs du test démarrent ensuite sans sudo.
Les processus du test et leurs enfants sont arrêtés et leurs fichiers supprimés.
Le mot de passe et le certificat sont exclusivement des données de test.

Avec les prérequis et variables de `INTEGRATION.md`, lancer en utilisateur ordinaire :

```sh
export MAILBOX_DOVECOT=/usr/sbin/dovecot
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/integration \
  -k dovecot_strict -q --tb=short
```

## Validation acquise — 15 septembre 2026

Le [run GitHub 34911811074](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34911811074) a réussi
sur le commit `0eb09bfabda1a082bed6d9e881810373383f0324`, ensuite fusionné par la
PR #2 dans `92064b430aa3f8f14d504728b013ca013b3f83b0`.
La [tâche imap](https://github.com/Othman-Benbrahim/Mailbox-Synchroniseur/actions/runs/34911811074/job/104200749475)
a validé la suite de 14 essais, incluant ce scénario. Le dernier critère de la
phase 2 est satisfait ; STATUS.md et ROADMAP.md enregistrent sa fermeture.

La tâche active MAILBOX_DOVECOT et installe la version attendue de Dovecot.
Une version incompatible ou un serveur qui ne démarre pas fait échouer le test.
Le rapport `imap-results.xml` est conservé dans l'artefact du run. Pour les
vérifications futures, un test ignoré ne vaut pas réussite de ce critère.

## Correctif nécessaire et provenance de la preuve

La première exécution GitHub s'arrêtait à l'ajout du message source. La configuration
du backend `count` a été complétée avec `quota_vsizes = yes`, obligatoire pour son
initialisation, puis la suite a réussi. Les journaux serveur sont maintenant inclus
dans le diagnostic pytest pour faciliter l'analyse d'une éventuelle régression.

La configuration avait été acceptée localement par `doveconf`, mais le serveur
n'avait pas pu démarrer dans ce runtime, où les sockets Unix sont bloqués.
La validation réelle de ce scénario provient de GitHub Actions. Elle concerne les
comptes isolés de cette fixture, pas une certification de fournisseurs réels.

Références de configuration :
- https://doc.dovecot.org/2.3/configuration_manual/howto/rootless/
- https://doc.dovecot.org/2.3/configuration_manual/quota_plugin/
