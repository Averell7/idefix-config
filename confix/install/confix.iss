; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Confix"
#define MyAppPublisher "GAF"
#define MyAppVersion "3.1.2"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId=A0B537CF-8AA0-43DD-94DC-15CF48A94FE7
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=http://idefix64.fr/
AppSupportURL=http://idefix64.fr/
AppUpdatesURL=http://idefix64.fr/
DefaultDirName={pf}\Confix
DefaultGroupName={#MyAppName} {#MyAppVersion}
AllowNoIcons=yes
OutputDir=D:\Mes Documents\en cours\Sheltercom\Shelter-admin\confix3\install
OutputBaseFilename={#MyAppName}_{#MyAppVersion}_Setup
Compression=lzma
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
Source: "D:\Mes Documents\en cours\Sheltercom\Shelter-admin\confix3\dist\confix\confix.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\Mes Documents\en cours\Sheltercom\Shelter-admin\confix3\dist\confix\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\Confix"; Filename: "{app}\confix.exe"
Name: "{group}\{cm:UninstallProgram,Confix}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Confix"; Filename: "{app}\confix.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Confix"; Filename: "{app}\confix.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\confix.exe"; Description: "{cm:LaunchProgram,Confix}"; Flags: nowait postinstall skipifsilent
