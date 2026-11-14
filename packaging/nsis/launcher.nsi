; PromptForger.exe: tiny launcher that starts the bundled Java runtime without a console window.
Unicode true
!define APP_VERSION "1.1.0"
Name "Prompt Forger"
OutFile "${OUT_DIR}\PromptForger.exe"
Icon "${ICON}"
RequestExecutionLevel user
SilentInstall silent
SetCompressor /SOLID lzma

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "Prompt Forger"
VIAddVersionKey "FileDescription" "Prompt Forger"
VIAddVersionKey "CompanyName" "Panwar Studio"
VIAddVersionKey "LegalCopyright" "Copyright (c) 2026 Prince Panwar"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"

Section
  IfFileExists "$EXEDIR\runtime\bin\javaw.exe" +3 0
    MessageBox MB_ICONSTOP "Prompt Forger is incomplete (the runtime folder is missing). Please reinstall it."
    Abort
  SetOutPath "$EXEDIR"
  Exec '"$EXEDIR\runtime\bin\javaw.exe" -Dfile.encoding=UTF-8 "-Dpromptforger.home=$EXEDIR" -m com.panwarstudio.promptforger/com.panwarstudio.promptforger.App'
SectionEnd
