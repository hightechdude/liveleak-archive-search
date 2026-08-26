#define MyAppName "LiveLeak Archive Search"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "HIGHTECHDUDE"
#define MyAppExeName "LiveLeakSearch.exe"
#define MyAppURL "https://github.com/HIGHTECHDUDE"

[Setup]
AppId={{A8F3C2E1-9B47-4D2A-8F1E-3C9D7B5A2E8F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=LiveLeakSearch_Setup_v1.0.0
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
VersionInfoVersion=1.0.0.0
VersionInfoCompany=HIGHTECHDUDE
VersionInfoDescription=LiveLeak Archive Search
VersionInfoCopyright=Created by HIGHTECHDUDE
VersionInfoProductName=LiveLeak Archive Search
VersionInfoProductVersion=1.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\LiveLeakSearch.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;