; Installateur Windows — Inno Setup.
; Installe l'application empaquetée et le moteur imapsync construit séparément.
; Aucune dépendance Python ni Perl n'est requise sur la machine cible.

#define AppName "Mailbox Synchroniseur"
#ifndef AppVersion
  #define AppVersion "0.6.0"
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Mailbox Synchroniseur contributors
DefaultDirName={autopf}\Mailbox Synchroniseur
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputBaseFilename=Mailbox-Synchroniseur-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Installation par utilisateur si l'installateur n'est pas lancé en administrateur.
PrivilegesRequiredOverridesAllowed=dialog commandline
LicenseFile=..\LICENSE
; Les notices des composants distribués accompagnent l'installation.
InfoAfterFile=..\THIRD_PARTY.md
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
; Mode dossier : les DLL Qt restent visibles et remplaçables (exigence LGPLv3).
Source: "..\dist\Mailbox-Synchroniseur\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\engine\imapsync.exe"; DestDir: "{app}\engine"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Mailbox-Synchroniseur.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Mailbox-Synchroniseur.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Run]
Filename: "{app}\Mailbox-Synchroniseur.exe"; Description: "Lancer {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; L'historique local appartient à l'utilisateur : il n'est pas supprimé ici.
Type: filesandordirs; Name: "{app}\_internal\__pycache__"
