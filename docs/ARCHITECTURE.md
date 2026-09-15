# Architecture et décisions

- Python >=3.11, PySide6/Qt Widgets. Interface française ; code original sous MIT.
- `models.py` : validation et plans de transfert immuables, sans secrets sérialisés.
- `profiles.py` : JSON versionné et écriture atomique d'un profil sans secrets.
- `engine.py` : liste d'arguments imapsync typée ; jamais de shell.
- `runner.py` : QProcess asynchrone, annulation, filtrage du journal.
- `folders.py` : encodage des noms en UTF-7 modifié IMAP.
- `folder_selector.py` : saisie et inversion des correspondances explicites.
- `filter_selector.py` : saisie des filtres par dates et taille (phase 3, lot 3a).
- `discovery.py` : une commande IMAP `LIST` par compte, en lecture seule, TLS vérifié (lot 3b).
- `mapping.py` : proposition pure de correspondance des dossiers, avec raisons (lot 3b).
- `discovery_worker.py` : exécution de la découverte hors du fil d'interface (lot 3b).
- `history.py` : historique local JSON sans secrets et texte de rapport exportable (lot 3c).
- `history_view.py` : liste, détail, export, reprise de périmètre et suppression (lot 3c).
- `mirror_selector.py` : armement du miroir, seule fonction destructive (lot 3d).
- `oauth.py` : flux OAuth code+PKCE sur boucle locale, sans identité embarquée (lot 4a).
- `oauth_worker.py` : exécution du flux hors du fil d'interface (lot 4a).
- `report.py` : compteurs observés et conditions de confirmation de destination.
- `ui.py` : source/destination, simulation préalable, exécution et bilan.

imapsync est un processus externe dans la première livraison, choisi par
l'utilisateur. Le code Perl amont n'est ni réécrit ni livré dans cette version.
Le bundling reproductible est un critère explicite de la phase 6.

Les mots de passe passent via l'environnement du processus enfant uniquement,
jamais via la ligne de commande ou un fichier. Cela ne protège pas d'un processus
local privilégié ou d'un logiciel malveillant exécuté sous le même compte. Python
ne garantit pas l'effacement physique des chaînes en RAM. L'environnement Qt est
vidé après démarrage et les références de secrets sont libérées en fin d'opération.
Le journal masque les valeurs littérales et leurs représentations courantes ; il
peut contenir des adresses et noms de dossiers. Pas de journal brut écrit sur disque.

TLS est forcé, avec validation de la chaîne et du nom d'hôte. Le magasin de CA
utilisé dépend de l'installation imapsync/Perl. Les erreurs de certificats ne sont
jamais contournées automatiquement. Contrat testé avec imapsync 2.314, TLS direct
et STARTTLS : voir INTEGRATION.md pour les preuves et limites.

Une copie exige la simulation réussie du même plan et des mêmes secrets de session.
Le profil ne mémorise pas cette autorisation. Les indicateurs Deleted ne sont pas
propagés, les expunges sont désactivés, les états des messages déjà présents ne sont
pas resynchronisés dans cette alpha. La copie n'est pas une transaction : arrêter
conserve les messages déjà copiés. Une simulation ne fige pas le contenu distant.

Sources vérifiées le 14 septembre 2026 :
- https://github.com/imapsync/imapsync
- https://imapsync.lamiral.info/README
- https://imapsync.lamiral.info/LICENSE
- https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html

## Phase 2 : dossiers, profils et bilan

`Plan.folders = None` signifie tous les dossiers. Une sélection explicite vide est
refusée. Chaque entrée produit `--folder source --f1f2 source=destination` pour la
simulation et la copie, jamais pour `--justlogin`. Les noms sont encodés en UTF-7
modifié avant construction des arguments. Un nom source contenant `=` est refusé
car imapsync utilise ce séparateur. Les doublons de source et de destination sont
refusés sans distinction de casse, de manière conservatrice. Le profil JSON v2
conserve ces correspondances ; la lecture v1 est maintenue, sans autoriser le moteur.

Le runner analyse les lignes complètes du moteur avant leur masquage pour ne pas
fausser les nombres si un mot de passe contient des chiffres. Le rapport ne conserve
que nombres, mode et statut. Les lignes restent filtrées avant affichage.
La confirmation exige copie, sortie 0, zéro erreur, zéro message manquant,
zéro message non identifié, absence d'arrêt et de crash. Des informations absentes
ne deviennent pas des zéros. Un bilan contradictoire avec une sortie 0 donne un échec.
Le rapport concerne le dernier essai de session ; son export/historique reste en phase 3.

## Phase 3, lot 3a : filtres et estimation du volume

`Plan.filters` est un `Filters` immuable ; `Filters()` signifie aucun filtre.
Les dates sont des chaînes ISO strictes (`AAAA-MM-JJ`), validées avant construction
des arguments, bornes incluses. `engine.search_criteria` produit
`SINCE j-Mon-aaaa BEFORE j-Mon-aaaa` avec le mois anglais de la RFC 3501, indépendant
de la locale ; la borne de fin est décalée d'un jour car `BEFORE` est strict.
L'option `--search` s'applique aux deux comptes : la comparaison source/destination
porte sur le même sous-ensemble. Les tailles sont des entiers d'octets positifs
(`--maxsize` exclut au-delà, `--minsize` exclut jusqu'à la valeur incluse, sémantique
d'imapsync). Aucun filtre n'est transmis avec `--justlogin`. L'interface édite des
Kio entiers ; au chargement d'un profil, un maximum est arrondi vers le haut et un
minimum vers le bas, pour ne jamais rendre le filtre plus restrictif que celui enregistré.

Profil JSON v3 : clé `filters` obligatoire et exhaustive ; v1 et v2 restent lus avec
`Filters()`. Un v2 portant `filters` ou un v3 sans est refusé.

Bilan : `report.py` lit, dans les statistiques finales d'imapsync 2.314,
`Messages transferred : 0 (could be N without --dry mode)` (messages à copier en
simulation), `Total bytes transferred`, `Total bytes skipped`, et dans le listing
des tailles `Host1 Total size` (messages sélectionnés dans les dossiers voulus).
L'estimation de simulation vaut `Host1 Total size − Total bytes skipped`, seulement
si la simulation a terminé avec code 0 et zéro erreur, jamais négative. En mode
`--dry`, imapsync ne télécharge pas les messages (`dry1`) et n'applique donc pas
`--maxsize`/`--minsize` : l'estimation est un maximum dans ce cas, signalé dans le texte.

imapsync identifie tous les messages sélectionnés à la source avant d'appliquer le
filtre de taille ; un message exclu par taille figure donc parmi les « absents à
destination ». Le bilan compte les lignes `msg … skipped (… exceeds maxsize limit …)`
et `… smaller than minsize …` ; la confirmation de présence exige que les absents
soient exactement expliqués par ces exclusions (`unexplained_missing == 0`). Ils sont
affichés, jamais soustraits silencieusement. Le runner ne met en échec une copie que
sur erreurs, absents non expliqués ou messages non identifiés.

Ces lectures proviennent de la source imapsync épinglée ; les essais IMAP les
vérifient contre le moteur réel. Un libellé changé donne « non communiqué ».

## Phase 3, lot 3b : découverte des dossiers et proposition de correspondance

Décision consignée : l'application parle IMAP directement, pour un seul verbe (`LIST`),
en lecture seule, afin de connaître les dossiers des deux comptes. Ce n'est pas un moteur
de transfert : aucune sélection de boîte, aucun FETCH, aucun APPEND, et la copie reste
entièrement déléguée à imapsync. L'alternative (`imapsync --justfolders --dry` et analyse de
sa sortie) a été écartée : plus lente, sortie non structurée. `imaplib` est la bibliothèque
standard ; pas de dépendance ajoutée.

`discovery.list_folders` exige TLS avec vérification de la chaîne et du nom d'hôte
(`ssl.create_default_context`, `CERT_REQUIRED`, `check_hostname`), en TLS direct ou STARTTLS
sans repli en clair. Le magasin de certificats est celui de Python, distinct de celui de
l'installation imapsync/Perl ; la documentation utilisateur le signale. Les messages
d'erreur ne contiennent jamais le mot de passe. Les noms sont décodés de l'UTF-7 modifié
(`folders.imap_utf7_decode`, tolérant : une section invalide est conservée telle quelle).
Le lecteur de réponses `LIST` accepte les noms cités, atomes et littéraux, le délimiteur
`NIL`, et lit les attributs SPECIAL-USE (RFC 6154) et `\Noselect`.

`mapping.propose` est une fonction pure : pour chaque dossier source sélectionnable, dans
l'ordre parents puis enfants, elle cherche dans l'ordre un nom identique, un rôle commun
(attribut du serveur, sinon alias usuels français/anglais), un nom identique à la casse
près, un préfixe déjà renommé, puis propose le nom traduit dans le séparateur de la
destination. Les dossiers `\Noselect` et `\All` sont exclus avec leur raison ; deux sources
visant la même destination donnent une exclusion explicite, jamais une collision silencieuse,
de sorte que toute proposition satisfait `Plan.validate`. Chaque ligne porte un motif
affiché à l'utilisateur.

Dans l'interface, la proposition remplit le tableau existant : elle est modifiable, elle
invalide la simulation comme toute modification, et la copie reste conditionnée à une
simulation réussie. Pendant la découverte, la configuration et les actions sont bloquées et
la fermeture est différée ; les mots de passe sont libérés par le worker en fin d'exécution.

## Phase 3, lot 3c : historique local et export de rapports

Format retenu : un fichier JSON par exécution, dans `<données utilisateur>/historique/`
(`QStandardPaths.AppDataLocation`, remplaçable par `MAILBOX_HISTORY_DIR`). Choix discuté :
JSON plutôt que SQLite, car le volume attendu est faible, aucune requête n'est nécessaire,
le contenu reste lisible et inspectable par l'utilisateur, et chaque entrée se supprime
fichier par fichier. Écriture atomique (`mkstemp` + `os.replace` + `fsync`), nom
`AAAAMMJJ-HHMMSS-NNN-<mode>.json` pour éviter toute collision à la même seconde, `version`
explicite refusée si inconnue, taille plafonnée à la lecture, fichier illisible ignoré sans
faire échouer la liste, purge au-delà de 200 entrées.

Ce qui est enregistré est exactement ce que le bilan affiche : horodatages, mode, résultat
et message, comptes (hôte, identifiant, port, sécurité — comme dans le profil), périmètre,
filtres, compteurs et code de sortie. **Ni mot de passe, ni journal de session** : le journal
peut contenir des sorties du moteur que l'utilisateur n'a pas choisi de conserver. Le rapport
exporté est le même contenu en texte, et le rappelle explicitement en dernière ligne.

L'échec d'écriture de l'historique est signalé dans le journal et n'interrompt jamais
l'opération : l'historique est une commodité, pas un élément du chemin critique. La reprise
d'un périmètre passé recharge dossiers et filtres seulement ; elle ne rétablit ni compte, ni
secret, et invalide la simulation comme toute modification.

## Phase 3, lot 3d : miroir

Périmètre décidé : **miroir seulement** (`--delete2`). Le déplacement (`--delete1`) n'est pas
livré et ne le sera pas par défaut : supprimer les originaux d'une boîte en cours de
migration est l'erreur irréversible du domaine, et imapsync recommande lui-même de ne le
faire qu'après vérification séparée. `--nodelete1` est passé explicitement dans **tous** les
modes, y compris sans miroir, pour que le contrat soit lisible dans la ligne de commande.

`--delete2` active de lui-même `uidexpunge2`, ou `expunge2` à défaut : la destination serait
vidée sans que l'utilisateur l'ait demandé. Les deux sont donc forcés à `--noexpunge2
--nouidexpunge2`, et le vidage n'a lieu que si l'utilisateur coche l'option dédiée
(`--expunge2`). Par défaut le miroir marque `\Deleted` : réversible depuis le client de
messagerie de l'utilisateur.

`Plan.mirror` et `Plan.expunge` participent à l'égalité du plan : armer le miroir invalide
la simulation précédente, donc la copie exige une simulation faite miroir armé. Ces deux
champs ne sont **pas** sérialisés dans le profil : un mode destructif ne se restaure jamais
depuis un fichier. Le miroir est refusé avec un filtre actif : un message masqué par un
filtre serait vu comme absent de la source et supprimé à destination — refus explicite,
jamais un filtrage silencieux des suppressions.

Le compteur de suppressions vient des lignes `Host2: msg …/… marked \Deleted` du moteur,
émises aussi en mode `--dry` (suivies de « not really since --dry mode »). La simulation
fournit donc un décompte exact sans rien supprimer, décompte réutilisé pour l'aperçu de
confirmation. La confirmation exige la saisie de `SUPPRIMER` ; un `QMessageBox` à deux
boutons a été jugé insuffisant pour une action destructive. Si la simulation annonce zéro
suppression, seule la confirmation ordinaire de copie s'applique.

L'historique enregistre `mirror`, `expunge` et le nombre de suppressions ; le rapport
exporté indique « Miroir : inactif — aucune suppression » quand il ne l'était pas.

## Phase 4, lot 4a : OAuth pour IMAP

Aucune identité d'application n'est embarquée dans le projet. L'utilisateur inscrit la
sienne et fournit son `client_id` ; motif : une identité embarquée engage personnellement
le mainteneur auprès du fournisseur (vérification, quotas partagés, suspension collective),
et le scope `https://mail.google.com/` impose une vérification avec audit. Conséquence
assumée : l'utilisateur a une procédure de console à suivre, documentée dans docs/OAUTH.md.

Flux : code d'autorisation avec PKCE (S256), navigateur système, redirection vers
`http://localhost:<port libre>/`, serveur HTTP local éphémère qui n'écoute que sur la boucle
locale et ne journalise rien — l'URL de retour contient le code. Le `state` est comparé au
retour ; une discordance abandonne la connexion. Aucun secret client n'est utilisé pour
Microsoft (client public) ; Google en impose un, qui n'est pas un secret au sens strict pour
une application de bureau et n'est donc jamais enregistré.

`Account.auth` vaut `"basic"` ou `"oauth"`, avec `provider` pour le fournisseur. La valeur
`"basic"` est choisie plutôt que `"password"` pour que le mot « password » reste absent de
tout profil sérialisé — un test de garde le vérifie. Ces deux champs sont enregistrés dans
le profil (ce ne sont pas des secrets) ; les profils antérieurs se relisent avec les valeurs
par défaut.

Le jeton est traité comme un mot de passe : masqué dans le journal par le Redactor, absent
des profils et de l'historique, effacé à la fermeture et dès que l'identifiant, le
`client_id` ou la méthode changent. Il n'est **pas** passé en argument : imapsync accepte
`--oauthaccesstoken{1,2}` sous forme de chemin de fichier dont il lit la première ligne, et
le runner écrit ce fichier en 0600 dans le répertoire temporaire de l'opération, supprimé à
la fin. Les variables `IMAPSYNC_PASSWORD{1,2}` ne sont pas renseignées pour un compte OAuth.
