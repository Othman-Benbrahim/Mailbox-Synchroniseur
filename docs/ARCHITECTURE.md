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
