; SERVUS - Inno Setup script
; Gera SetupServus-<versao>.exe e suporta auto-update via AppMutex.
; Versao e injetada pelo release.ps1 via /DAppVersion=

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName       "SERVUS"
#define AppPublisher  "Nicholas"
#define AppExeName    "Servus.exe"
#define AppId         "{C7E84A3F-7E22-4F8A-9A1D-SERVUS00001}"
#define AppMutex      "Global\ServusAppRunning"

[Setup]
AppId={{#AppId}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\release
OutputBaseFilename=SetupServus-{#AppVersion}
SetupIconFile=..\assets\servus.ico
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
RestartApplications=yes
AppMutex={#AppMutex}

[Languages]
Name: "brazilian"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"
Name: "startupicon"; Description: "Iniciar com o Windows"; GroupDescription: "Inicializacao:"; Flags: unchecked

[Files]
; Copia toda a saida do PyInstaller (--onedir)
Source: "..\dist\Servus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}";    Filename: "{app}\{#AppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName}"; Flags: nowait postinstall skipifsilent
