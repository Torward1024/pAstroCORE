; The Windows installer: what a user double-clicks, and what it leaves behind.
;
; Built from the PyInstaller folder in `dist\pAstroCORE`:
;
;     ISCC /DVersion=1.17.0 packaging\pastrocore.iss
;
; It installs for one user, under their own profile, so Windows never asks for an
; administrator. Asking for one is a dialog that stops somebody who does not have the
; password, and nothing here needs to write outside the profile.

#ifndef Version
  #define Version "0.0.0"
#endif

#define Name "pAstroCORE"
#define Publisher "Alexey Rudnitskiy"
#define Site "https://github.com/Torward1024/pAstroCORE"

[Setup]
AppId={{7E4B2A16-9C3D-4F58-A0E1-5D7C8B9A1F23}
AppName={#Name}
AppVersion={#Version}
AppPublisher={#Publisher}
AppPublisherURL={#Site}
AppSupportURL={#Site}/issues
DefaultDirName={autopf}\{#Name}
DefaultGroupName={#Name}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename={#Name}-{#Version}-windows-x64
SetupIconFile=pastrocore.ico
UninstallDisplayIcon={app}\{#Name}.exe
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\{#Name}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Name}"; Filename: "{app}\{#Name}.exe"
Name: "{group}\Uninstall {#Name}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Name}"; Filename: "{app}\{#Name}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#Name}.exe"; Description: "Start {#Name}"; Flags: nowait postinstall skipifsilent
