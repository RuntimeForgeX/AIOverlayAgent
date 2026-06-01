; Inno Setup Script - Professional Windows Installer
; Builds a standard Windows installer wizard for AI Overlay Agent.
; Similar to Git, VSCode, and other professional Windows installers.

#include "app_config.issinc"

#define MyAppURL "https://github.com"
#define MyAppPublisherURL "https://github.com"

[Setup]
; Core setup configuration
AppId={{{#MyAppIdGuid}}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppPublisherURL}
AppSupportURL={#MyAppPublisherURL}
AppUpdatesURL={#MyAppPublisherURL}

; Installation paths and defaults
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; UI and visual styling
WizardStyle=modern
WizardSizePercent=100
DisableProgramGroupPage=no
AllowNoIcons=yes

; Installer configuration
OutputDir=..\release
OutputBaseFilename={#MyAppName}_Setup
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Compression and architecture
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; User experience
PrivilegesRequired=lowest
ChangesAssociations=yes
ChangesEnvironment=yes

; Info files before/after installation
InfoBeforeFile=LICENSE.txt
InfoAfterFile=POST_INSTALL_INFO.txt

; Windows compatibility (Windows 10 2004+)
MinVersion=10.0.19041
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1={#MyAppName} Setup Wizard
WelcomeLabel2=This will install {#MyAppName} on your computer.%n%nThe AI overlay remains invisible to screen recording software (OBS, Zoom, Meet, etc.), making it perfect for teaching and streaming.%n%nClick Next to continue, or Cancel to exit.
FinishedHeadingLabel={#MyAppName} Installed Successfully!
FinishedLabel=The application is now ready to use. You can launch it from your Desktop or Start Menu.
ConfirmUninstall=Are you sure you want to completely remove {#MyAppName} and all of its components?

[Tasks]
; Desktop shortcut
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

; Start Menu shortcuts
Name: "startmenu"; Description: "Create &Start Menu shortcuts"; GroupDescription: "Shortcuts:"

; Quick Launch
Name: "quicklaunch"; Description: "Create &Quick Launch shortcut"; GroupDescription: "Shortcuts:"

; Startup option
Name: "startup"; Description: "&Run on startup"; GroupDescription: "Startup:"

; Documentation
Name: "docs"; Description: "View &documentation after install"; GroupDescription: "Post-Install:"

[Files]
; Main application executable
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Configuration files
Source: "..\config.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app_config.ini"; DestDir: "{app}"; Flags: ignoreversion

; License and documentation
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "POST_INSTALL_INFO.txt"; DestDir: "{app}"; Flags: ignoreversion

; Environment template
Source: "..\.env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion

; Documentation
Source: "..\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\QUICK_TEST.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "AI Overlay for Screen Recording"
Name: "{group}\Documentation"; Filename: "{app}\README.md"; Comment: "View application documentation"
Name: "{group}\Configuration"; Filename: "{app}\config.ini"; Comment: "Edit application settings"
Name: "{group}\Setup API Key"; Filename: "{app}\.env.example"; Comment: "Setup your API key"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Comment: "Remove {#MyAppName}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "AI Overlay Agent"

; Quick Launch
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunch; Comment: "AI Overlay Agent"

; Startup folder
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startup; Comment: "AI Overlay Agent - Auto-start"

[Run]
; Launch application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Registry]
; Per-user install path (Inno Setup registers uninstall info automatically)
Root: HKCU; Subkey: "Software\{#MyAppPublisher}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue

[UninstallDelete]
; Clean up user data folder on uninstall (optional - uncomment to enable)
; Type: dirifempty; Name: "{app}"
; Type: files; Name: "{userdocs}\{#MyAppName}"

[Code]
// Called after successful installation
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Log installation success
    Log('Installation completed successfully');
  end;
end;

// Handle uninstall
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Log('Uninstallation completed successfully');
  end;
end;
