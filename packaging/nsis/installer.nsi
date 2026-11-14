; Prompt Forger installer: per-user install (no admin rights), Start menu + desktop shortcuts, clean uninstall.
Unicode true
!include "MUI2.nsh"

!define APP_NAME "Prompt Forger"
!define APP_VERSION "1.1.0"
!define PUBLISHER "Panwar Studio"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\PromptForger"

Name "${APP_NAME}"
OutFile "${OUT_DIR}\PromptForger-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\Prompt Forger"
InstallDirRegKey HKCU "Software\PromptForger" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails nevershow
ShowUninstDetails nevershow

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "FileDescription" "${APP_NAME} Setup"
VIAddVersionKey "CompanyName" "${PUBLISHER}"
VIAddVersionKey "LegalCopyright" "Copyright (c) 2026 Prince Panwar"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"

!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\PromptForger.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Prompt Forger"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  ; Upgrades: replace bundled runtime and engine so no stale files from an older version remain.
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\engine"
  File /r "${APP_DIR}\*.*"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\PromptForger" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\PromptForger.ico"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "EstimatedSize" ${SIZE_KB}

  CreateShortCut "$SMPROGRAMS\${APP_NAME}.lnk" "$INSTDIR\PromptForger.exe" "" "$INSTDIR\PromptForger.ico"
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\PromptForger.exe" "" "$INSTDIR\PromptForger.ico"
SectionEnd

Section "Uninstall"
  ; Remove only what the installer created. Presets in %APPDATA%\PromptForger are kept.
  Delete "$SMPROGRAMS\${APP_NAME}.lnk"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\engine"
  Delete "$INSTDIR\PromptForger.exe"
  Delete "$INSTDIR\PromptForger.ico"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "${UNINST_KEY}"
  DeleteRegKey HKCU "Software\PromptForger"
SectionEnd
