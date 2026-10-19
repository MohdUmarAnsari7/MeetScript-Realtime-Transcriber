; =====================================================================
; Inno Setup Script: MeetScript
; =====================================================================

#define MyAppName "MeetScript"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Mohd umar ansari"
#define MyAppExeName "MeetScript.exe"

[Setup]
; Unique application GUID
AppId={{D37F46B1-A6B8-4A59-8631-B7390F108C7F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Custom icon for setup installer and Windows uninstaller
SetupIconFile=favicon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=installer_output
OutputBaseFilename=MeetScript_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; "lowest" allows installation without requiring Windows Administrator rights
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copies the compiled PyInstaller MeetScript folder into the installation directory
Source: "dist\MeetScript\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "favicon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu and Desktop shortcuts using custom favicon.ico
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\favicon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\favicon.ico"; Tasks: desktopicon

[Run]
; Checkbox to launch app immediately after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
