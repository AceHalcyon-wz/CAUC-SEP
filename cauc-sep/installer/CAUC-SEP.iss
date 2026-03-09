; CAUC-SEP Inno Setup Installation Script
; Version: 0.3.0
; Author: CAUC
; Updated: 2026-03-09
;
; 功能：
;   - 专业级Windows安装包生成
;   - 支持中英文双语界面
;   - 自动创建桌面快捷方式
;   - 完整卸载功能
;
; 使用方法：
;   1. 先运行 scripts\build-nuitka.bat 生成后端EXE
;   2. 使用Inno Setup编译此脚本
;
; Inno Setup下载：https://jrsoftware.org/isinfo.php

#define MyAppName "CAUC-SEP"
#define MyAppVersion "0.3.0"
#define MyAppExeName "CAUC-SEP-Backend.exe"
#define MyAppURL "https://github.com/cauc/cauc-sep"

[Setup]
AppId={{CAUC-SEP-2024-1A2B-3C4D-5E6F-7890ABCDEF01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=CAUC
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=CAUC-SEP-Setup-v{#MyAppVersion}
SetupIconFile=..\backend\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=100
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0.17763
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\assets\icon.ico
UninstallDisplayName={#MyAppName}
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=no
DisableFinishedPage=no
DisableStartupPrompt=no
CreateAppDir=yes
DirExistsWarning=yes
OverwriteInstalldir=yes
AppendDefaultDirName=yes
AppendDefaultGroupName=yes
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousLanguage=yes
LanguageDetectionMethod=uilanguage
SetupLogging=yes
RestartApplications=no
CloseApplications=yes
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Messages]
english.BeveledLabel=CAUC Spintronics Experiment Platform
chinesesimplified.BeveledLabel=CAUC自旋电子实验平台

[CustomMessages]
english.WelcomeLabel1=Welcome to the CAUC-SEP Setup Wizard
english.WelcomeLabel2=This will install CAUC-SEP Spintronics Experiment Platform on your computer.%n%nIt is recommended that you close all other applications before starting.
english.FinishedHeadingLabel=Completing the CAUC-SEP Setup Wizard
english.FinishedLabel=Setup has finished installing CAUC-SEP on your computer.%n%nClick Finish to exit Setup.
english.LaunchProgram=Launch CAUC-SEP
chinesesimplified.WelcomeLabel1=欢迎使用 CAUC-SEP 安装向导
chinesesimplified.WelcomeLabel2=此向导将在您的计算机上安装 CAUC-SEP 自旋电子实验平台。%n%n建议您在开始之前关闭所有其他应用程序。
chinesesimplified.FinishedHeadingLabel=CAUC-SEP 安装向导完成
chinesesimplified.FinishedLabel=安装程序已在您的计算机上安装了 CAUC-SEP。%n%n单击"完成"退出安装程序。
chinesesimplified.LaunchProgram=启动 CAUC-SEP

[Types]
Name: "full"; Description: "{cm:FullInstall}"
Name: "compact"; Description: "{cm:CompactInstall}"
Name: "custom"; Description: "{cm:CustomInstall}"; Flags: iscustom

[Components]
Name: "main"; Description: "Main Program"; Types: full compact custom; Flags: fixed
Name: "frontend"; Description: "Frontend Web Interface"; Types: full
Name: "docs"; Description: "Documentation"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Launch at Windows startup"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
; Backend executable (Nuitka compiled)
Source: "..\dist\release\CAUC-SEP-Backend.exe"; DestDir: "{app}"; Flags: ignoreversion solidbreak; Components: main
; Fallback to backend\dist if release not found
Source: "..\backend\dist\CAUC-SEP-Backend.exe"; DestDir: "{app}"; Flags: ignoreversion solidbreak skipifsourcedoesntexist; Components: main

; Frontend static files
Source: "..\dist\release\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs solidbreak; Components: frontend
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs solidbreak skipifsourcedoesntexist; Components: frontend

; Assets
Source: "..\backend\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs solidbreak; Components: main

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion solidbreak; Components: docs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion solidbreak; Components: docs
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion solidbreak; Components: docs
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs solidbreak skipifsourcedoesntexist; Components: docs

; Startup scripts
Source: "..\dist\release\start.bat"; DestDir: "{app}"; Flags: ignoreversion solidbreak skipifsourcedoesntexist; Components: main
Source: "..\dist\release\stop.bat"; DestDir: "{app}"; Flags: ignoreversion solidbreak skipifsourcedoesntexist; Components: main

; Configuration
Source: "..\dist\release\config\config.ini"; DestDir: "{app}\config"; Flags: ignoreversion solidbreak skipifsourcedoesntexist; Components: main

[Dirs]
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\data"; Permissions: users-modify
Name: "{app}\config"; Permissions: users-modify
Name: "{app}\exports"; Permissions: users-modify
Name: "{app}\traces"; Permissions: users-modify
Name: "{app}\cache"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram}"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\config"
Type: filesandordirs; Name: "{app}\exports"
Type: filesandordirs; Name: "{app}\traces"
Type: filesandordirs; Name: "{app}\cache"
Type: filesandordirs; Name: "{app}\frontend"
Type: filesandordirs; Name: "{app}\assets"
Type: filesandordirs; Name: "{app}\docs"
Type: files; Name: "{app}\*.db"
Type: files; Name: "{app}\*.log"

[Registry]
; Add to PATH (optional, disabled by default)
; Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Flags: preservestringtype uninsdeletevalue

; Auto-start entry
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CAUC-SEP"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[InstallDelete]
Type: files; Name: "{app}\*.pyc"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
function InitializeSetup(): Boolean;
var
  PythonVersion: String;
  ResultCode: Integer;
begin
  Result := True;
  Log('CAUC-SEP Setup initialized');
  
  if not RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.10\InstallPath', '', PythonVersion) then
  begin
    if not RegQueryStringValue(HKCU, 'SOFTWARE\Python\PythonCore\3.10\InstallPath', '', PythonVersion) then
    begin
      Log('Python not found in registry - this is OK for standalone build');
    end;
  end;
  
  if RunningTaskCount('{#MyAppExeName}') > 0 then
  begin
    if MsgBox('CAUC-SEP is currently running. Please close it before continuing with installation.', mbConfirmation, MB_OKCANCEL) = IDCANCEL then
    begin
      Result := False;
    end;
  end;
end;

function RunningTaskCount(const ExeName: String): Integer;
var
  TaskList: TArrayOfString;
  I: Integer;
begin
  Result := 0;
  if not FileExists(ExpandConstant('{sys}\tasklist.exe')) then Exit;
  
  if Exec(ExpandConstant('{sys}\tasklist.exe'), '/FI "IMAGENAME eq ' + ExeName + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // Task list executed
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: string;
begin
  if CurStep = ssPostInstall then begin
    ConfigPath := ExpandConstant('{app}\config\config.ini');
    
    if not FileExists(ConfigPath) then begin
      ForceDirectories(ExpandConstant('{app}\config'));
      SaveStringToFile(ConfigPath, 
        '# CAUC-SEP Configuration' + #13#10 +
        '' + #13#10 +
        '[server]' + #13#10 +
        'host = 127.0.0.1' + #13#10 +
        'port = 8000' + #13#10 +
        '' + #13#10 +
        '[logging]' + #13#10 +
        'level = INFO' + #13#10 +
        'max_bytes = 10485760' + #13#10 +
        'backup_count = 5' + #13#10 +
        '' + #13#10 +
        '[devices]' + #13#10 +
        'simulation = true' + #13#10 +
        '' + #13#10 +
        '[modbus]' + #13#10 +
        'port = COM3' + #13#10 +
        'baudrate = 115200' + #13#10 +
        'parity = N' + #13#10 +
        'stopbits = 1' + #13#10 +
        'bytesize = 8' + #13#10 +
        'timeout = 1.0' + #13#10 +
        '' + #13#10 +
        '[database]' + #13#10 +
        'path = {app}\data\experiments.db' + #13#10 +
        '' + #13#10 +
        '[paths]' + #13#10 +
        'logs = {app}\logs' + #13#10 +
        'data = {app}\data' + #13#10 +
        'exports = {app}\exports' + #13#10, 
        False);
    end;
    
    Log('CAUC-SEP installation completed successfully');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataPath: string;
begin
  if CurUninstallStep = usUninstall then begin
    if MsgBox('Do you want to delete all user data (logs, data, config, exports)?', mbConfirmation, MB_YESNO) = IDYES then begin
      DelTree(ExpandConstant('{app}\logs'), True, True, True);
      DelTree(ExpandConstant('{app}\data'), True, True, True);
      DelTree(ExpandConstant('{app}\config'), True, True, True);
      DelTree(ExpandConstant('{app}\exports'), True, True, True);
      DelTree(ExpandConstant('{app}\traces'), True, True, True);
      DelTree(ExpandConstant('{app}\cache'), True, True, True);
      DelTree(ExpandConstant('{app}\frontend'), True, True, True);
      Log('User data deleted');
    end;
  end;
end;
