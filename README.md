# Mailbox Synchroniseur — 0.1.0 alpha 1

Application de bureau en français pour copier des messages entre deux comptes
IMAP, en pilotant le moteur libre imapsync. Le développement suit [ROADMAP.md](ROADMAP.md).
L'état réel et les prochaines étapes sont dans [STATUS.md](STATUS.md).

![Interface de la version alpha](docs/interface-alpha.png)

## Ce que cette première version permet

- Configurer source et destination, TLS direct ou STARTTLS.
- Enregistrer/ouvrir un profil sans les mots de passe ; inverser les comptes.
- Piloter un imapsync installé : tester les accès, simuler, puis copier tous les dossiers.
- Arrêter un processus ; relancer une simulation avant reprise.
- Lire un journal de session avec masquage des mots de passe connus.

La copie est déverrouillée après une simulation réussie. Toute modification des
comptes, ports, mots de passe ou chemin du moteur invalide cette simulation.
Le chargement d'un profil efface les secrets et oblige à sélectionner de nouveau
l'exécutable local : le fichier du profil n'autorise pas l'exécution d'un programme.
Le journal affiche les sorties du moteur, principalement en anglais.

## Windows : lancement depuis les sources

1. Extraire entièrement cette archive dans un dossier, par exemple
   `D:\Documents\Mailbox-Synchroniseur`. Ne pas lancer depuis l'intérieur du ZIP.
2. Installer Python 3.11 ou plus récent, avec le lanceur `py`.
3. Double-cliquer sur **Lancer-Windows.bat**. Au premier lancement, un environnement
   `.venv` est créé et PySide6 est téléchargé (connexion Internet nécessaire).
4. Dans l'application, sélectionner un **imapsync.exe de confiance** déjà disponible
   sur l'ordinateur. Il n'est pas fourni dans cette alpha.
5. Renseigner les deux comptes, tester les accès et lancer une simulation.
6. Examiner le journal et cliquer sur « Copier les messages ».

Le script BAT ne nécessite pas de modifier la stratégie d'exécution PowerShell.
Il lance Python dans l'environnement du projet, sans activation manuelle.
Un mot de passe d'application peut être nécessaire selon le fournisseur.
Les connexions OAuth Google/Microsoft ne sont pas encore implémentées.

Alternative PowerShell, depuis le dossier extrait :

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m mailbox_sync
```

## Linux / macOS

Avec Python >=3.11 installé, lancer `sh lancer.sh`. Sélectionner un exécutable
imapsync natif fonctionnel (pour le script Perl, ses dépendances doivent être
installées). Cette livraison est testée sous Linux uniquement ; Windows et macOS
nécessitent encore des essais sur les systèmes cibles.

## Moteur imapsync

Sources amont : https://github.com/imapsync/imapsync
Documentation et distributions de l'auteur : https://imapsync.lamiral.info/

Le code source amont est libre ; certaines distributions et le support de l'auteur
sont payants. Cette archive ne contient aucun exécutable imapsync ni ses dépendances.
La construction et l'intégration d'un moteur redistribuable dans un installateur
sans Python ni Perl préinstallés figurent dans la phase 6.

Le moteur doit prendre en charge les mots de passe `IMAPSYNC_PASSWORD1/2` dans son
environnement et les options documentées dans `docs/ARCHITECTURE.md`. Le contrat
utilisé est celui de la documentation officielle consultée pour cette livraison ;
aucune version de moteur réelle n'a encore été certifiée avec l'application.

## Limites actuelles

Alpha de développement, pas encore un outil validé pour une migration importante.
Les tests fournis exécutent un faux moteur local ; ils ne valident pas le transfert
réel des messages. La phase 2 est consacrée aux tests IMAP réels, à la reprise et à
la comparaison source/destination.

- Copie de tous les dossiers ; sélection et correspondance à venir.
- Pas de miroir, déplacement, synchronisation bidirectionnelle, contacts ou calendriers.
- Pas de sauvegarde de mot de passe, OAuth, planification ni installateur autonome.
- Progression indéterminée : pas de pourcentage ou temps restant inventé.
- Pas de resynchronisation des états des messages déjà présents dans cette alpha.
- Les erreurs du moteur signifient qu'une copie peut être partielle ; arrêter
  n'annule pas les messages déjà copiés.
- Les certificats doivent être acceptés par le magasin de confiance de l'installation
  imapsync/Perl. L'application n'offre pas de désactivation de leur vérification.

Les secrets restent dans la session et l'environnement du processus enfant pendant
son exécution. Cela ne protège pas contre un autre processus local privilégié.
Les profils contiennent des adresses et noms de serveurs. Le journal peut contenir
des adresses et noms de dossiers et n'est pas enregistré automatiquement.

## Développement

```sh
python -m pip install -e '.[dev]'
python -m pytest -q
```

Sur une machine Linux sans affichage : `QT_QPA_PLATFORM=offscreen python -m pytest -q`.
Les tests du moteur simulé n'utilisent aucune boîte mail ni aucun accès utilisateur.

Licence MIT pour le code original. Voir LICENSE et THIRD_PARTY.md pour les composants.
