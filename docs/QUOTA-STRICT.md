# Dernier critère de la phase 2 : quota strict

Cette suite complète le test GreenMail, qui ne fait qu'annoncer un quota dépassé.
`test_dovecot_strict_quota_refuses_append_and_resumes` utilise deux instances réelles
de Dovecot 2.3.21 en TLS direct, avec le moteur imapsync 2.314 réel.

## Scénario exigé

1. Source avec une pièce jointe ; destination avec deux anciens messages.
2. Destination limitée à 64 Kio, backend de quota `count`, marge de dépassement nulle.
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

## Critère de fermeture

Le nouveau test doit **réussir**, pas être ignoré. La tâche GitHub `imap` définit
MAILBOX_DOVECOT et installe Dovecot ; une version inattendue ou un démarrage impossible
fait échouer le test. Le rapport `imap-results.xml` est conservé comme artefact CI.
La suite d'intégration complète attend désormais 14 succès, dont ce scénario.
Après succès, mettre à jour STATUS.md avec le commit et le lien du run correspondant
avant de commencer la phase 3.

## État au moment de préparer ce correctif

- Fusion de la PR #1 confirmée sur main, commit `3d5b7de9c94f347aceba4ae839c9284fe93b52c7`.
- 56 tests du socle réussis localement après ajout ; nouveau test collecté.
- Configuration acceptée par `doveconf` 2.3.21 provenant du paquet Ubuntu.
- Démarrage réel local impossible : les sockets Unix sont interdits dans ce runtime.
- Aucun succès du nouveau scénario Dovecot n'est donc encore revendiqué.

Références de configuration :
- https://doc.dovecot.org/2.3/configuration_manual/howto/rootless/
- https://doc.dovecot.org/2.3/configuration_manual/quota_plugin/
