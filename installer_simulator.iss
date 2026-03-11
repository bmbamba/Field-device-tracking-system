; installer_simulator.iss  —  Inno Setup script for CLAN Device Simulator
; Build EXE first:  py -m PyInstaller device_simulator.spec
; Then compile:     iscc installer_simulator.iss

#define AppName      "CLAN Device Simulator"
#define AppVersion   "1.0"
#define AppPublisher "CLAN Systems"
#define AppExeName   "ClanDeviceSimulator.exe"
#define BuildDir     "dist\ClanDeviceSimulator"

[Setup]
AppId={{B2C3D4E5-F6A7-8901-BCDE-F12345678901}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\ClanDeviceSimulator
DefaultGroupName=CLAN Tracking
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=ClanDeviceSimulator_v1.0_Setup
SetupIconFile=tracking_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
LicenseFile=LICENSE.txt
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Also install a helper batch file so users can run the simulator easily
Source: "run_simulator.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName} (Console)"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Run Simulator";        Filename: "{app}\run_simulator.bat"
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\run_simulator.bat"; Tasks: desktopicon

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
