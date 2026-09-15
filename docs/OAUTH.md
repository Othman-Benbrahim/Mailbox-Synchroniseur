# Connexion OAuth : inscrire ta propre application

Cette application n'embarque aucune identité d'application. Pour utiliser OAuth, tu
inscris ta propre application chez le fournisseur et tu colles son identifiant
(`client_id`) dans Mailbox Synchroniseur. Rien n'est enregistré au nom de ce projet,
aucun quota n'est partagé avec d'autres utilisateurs, et aucun secret de ce projet
ne circule.

## Quand en as-tu besoin ?

| Fournisseur | Mot de passe d'application | OAuth |
| --- | --- | --- |
| Gmail / Google Workspace | Fonctionne, avec la validation en deux étapes activée | Possible, mais inutile dans la plupart des cas |
| Outlook.com, Microsoft 365 | **Ne fonctionne plus** | **Obligatoire** |
| Autres fournisseurs IMAP | Généralement oui | Rarement proposé |

**Pour une boîte Outlook.com personnelle, cette application n'offre donc aujourd'hui aucun
chemin praticable** : Microsoft n'accepte plus le mot de passe et l'inscription OAuth est
hors de portée. Un client de messagerie doté de sa propre identité d'application, comme
Thunderbird, sait se connecter sans inscription et permet de copier des dossiers d'un compte
à l'autre.

Pour Gmail, le chemin simple reste le mot de passe d'application : activer la validation
en deux étapes, puis générer un mot de passe sur `myaccount.google.com/apppasswords`.
Il n'est pas disponible si le compte est inscrit au Programme Protection Avancée, ou si
un administrateur Workspace l'interdit.

## Microsoft (Outlook.com, Microsoft 365)

> **Avertissement — à lire avant de commencer.** Avec un compte **personnel** (Outlook.com,
> Hotmail, Live), ces étapes échouent. Microsoft rattache ces comptes au tenant « Microsoft
> Services », qui ne contient aucun annuaire où inscrire une application ; la connexion au
> centre d'administration Entra renvoie l'erreur `AADSTS50020`. La création automatique d'un
> annuaire lié à un compte personnel a été supprimée. La voie officielle est de créer un
> compte Azure, donc un tenant : l'inscription d'application reste gratuite, mais l'ouverture
> du compte Azure demande une carte bancaire.
>
> En conséquence, **l'OAuth Microsoft de cette application n'est pas praticable pour une
> boîte personnelle**, et le développement de la phase 4 s'est arrêté là (voir STATUS.md).
> Les étapes ci-dessous ne valent que si tu disposes déjà d'un tenant Entra, par exemple via
> un compte professionnel ou scolaire.

1. Ouvrir le centre d'administration Microsoft Entra, section « Inscriptions d'applications ».
2. « Nouvelle inscription », donner un nom, choisir le type de comptes correspondant à
   ta boîte (comptes personnels pour Outlook.com, l'annuaire de l'organisation pour un
   Microsoft 365 d'entreprise).
3. Dans « Authentification », ajouter une plateforme « Applications mobiles et de bureau »
   et activer **« Allow public client flows »**. Sans cette option, la connexion est refusée
   avec « unauthorized_client ».
4. Dans « Autorisations d'API » : Microsoft Graph → autorisations déléguées →
   `IMAP.AccessAsUser.All`, puis `offline_access`.
5. Copier l'**ID d'application (client)** depuis la page Vue d'ensemble.
6. Dans Mailbox Synchroniseur : choisir « OAuth — Microsoft », coller le `client_id`,
   cliquer sur « Se connecter dans le navigateur… » et accorder l'accès.

Aucun secret client n'est nécessaire : l'application est un client public.
Sur un Microsoft 365 d'entreprise, un administrateur peut devoir donner son consentement.

## Google (Gmail)

1. Créer un projet sur `console.cloud.google.com` (gratuit, sans facturation).
2. Activer l'API Gmail dans ce projet.
3. Configurer l'écran de consentement OAuth : type « Externe », nom, adresse de contact.
4. Ajouter le scope `https://mail.google.com/`.
5. S'ajouter comme **utilisateur de test** dans l'onglet Audience.
6. Créer des identifiants → ID client OAuth → type **Application de bureau**.
7. Coller le `client_id` et le secret client dans Mailbox Synchroniseur, puis se connecter.

**Deux limites propres à Google, à connaître avant de commencer.** L'écran de
consentement affichera un avertissement « application non validée », qu'il faut accepter.
Et tant que l'application reste en mode « Testing », les autorisations expirent sept jours
après le consentement. Pour une migration ponctuelle, c'est sans conséquence : le jeton
d'accès obtenu est valable environ une heure et la migration se fait dans la foulée.
Passer en production avec le scope `mail.google.com` exige une vérification par Google,
avec audit de sécurité ; ce n'est pas envisageable pour un particulier.

## Ce que l'application fait du jeton

Le jeton d'accès reste en mémoire pour la session. Il n'est jamais écrit dans un profil,
jamais affiché dans le journal (il y est masqué comme un mot de passe), et il n'est pas
passé sur la ligne de commande : il est écrit dans un fichier temporaire lisible par toi
seul, dans le dossier de l'opération en cours, que le moteur lit et qui disparaît à la fin.

Changer d'identifiant, de `client_id` ou de méthode d'authentification efface le jeton et
oblige à se reconnecter. Fermer l'application l'efface également. Il n'y a aucun
stockage dans un coffre système à ce stade : c'est prévu pour un lot ultérieur.
