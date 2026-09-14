# Architecture et décisions

- Python >=3.11, PySide6/Qt Widgets. Interface française ; code original sous MIT.
- `models.py` : validation et plans de transfert immuables, sans secrets sérialisés.
- `profiles.py` : JSON versionné et écriture atomique d'un profil sans secrets.
- `engine.py` : liste d'arguments imapsync typée ; jamais de shell.
- `runner.py` : QProcess asynchrone, annulation, filtrage du journal.
- `ui.py` : source/destination, simulation préalable, exécution et état.

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
jamais contournées automatiquement. Tester ce contrat avec le moteur réel en phase 2.

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
