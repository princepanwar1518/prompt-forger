<#
.SYNOPSIS
    Builds Prompt Forger for Windows: Python engine (PyInstaller) + JavaFX UI (jpackage).

.DESCRIPTION
    Output in .\build\dist:
      PromptForger\                       portable app folder (run PromptForger.exe)
      PromptForger-<ver>-portable.zip     the same folder, zipped
      PromptForger-<ver>.exe              installer (only when WiX Toolset 3 is installed)

    Requirements:
      - JDK 21 that includes JavaFX, e.g. BellSoft Liberica "Full JDK 21" (java, javac, jar, jpackage on PATH)
      - Python 3.11+ (py launcher or python on PATH)
      - Optional: WiX Toolset 3.x (candle.exe, light.exe) for the .exe installer

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$NoInstaller
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Version   = '1.1.0'
$AppName   = 'PromptForger'
$Module    = 'com.panwarstudio.promptforger'
$MainClass = 'com.panwarstudio.promptforger.App'
# Fixed so future installers upgrade in place instead of installing side by side.
$UpgradeUuid = '6f1c2a3e-8b4d-4e7a-9c5f-2d8e1b7a4c90'

$Root     = Split-Path -Parent $PSScriptRoot
$Build    = Join-Path $Root 'build'
$Engine   = Join-Path $Root 'engine'
$AppSrc   = Join-Path $Root 'app\src\main'
$Dist     = Join-Path $Build 'dist'
$Payload  = Join-Path $Build 'payload\engine'

function Step([string]$Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }

function Invoke-Native {
    param([Parameter(Mandatory)][string]$Exe, [string[]]$Arguments = @())
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "'$Exe $($Arguments -join ' ')' failed with exit code $LASTEXITCODE" }
}

function Require([string]$Command, [string]$Hint) {
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) { throw "$Command was not found on PATH. $Hint" }
}

# ------------------------------------------------------------------ preflight
Step 'Checking tools'
$jdkHint = 'Install a JDK 21 that bundles JavaFX, e.g. BellSoft Liberica "Full JDK 21", and put its bin folder on PATH.'
foreach ($tool in 'java', 'javac', 'jar', 'jpackage') { Require $tool $jdkHint }
$modules = (& java --list-modules) -join "`n"
if ($modules -notmatch 'javafx\.controls@') { throw "This JDK does not include JavaFX. $jdkHint" }

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $python = @('py', '-3') }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $python = @('python') }
else { throw 'Python 3.11+ was not found (tried py and python). Install it from python.org.' }
# No double quotes inside -c: Windows PowerShell 5.1 mangles them when calling native programs.
$pyVersion = [int](& $python[0] @($python | Select-Object -Skip 1) -c 'import sys; print(sys.version_info[0]*100+sys.version_info[1])')
if ($pyVersion -lt 311) { throw "Python 3.11+ required, found $([math]::Floor($pyVersion / 100)).$($pyVersion % 100)" }
Write-Host "JDK: $((& java -version 2>&1 | Select-Object -First 1))"
Write-Host "Python: $pyVersion"

if (Test-Path $Build) { Remove-Item $Build -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Build, $Dist | Out-Null

# ------------------------------------------------------------------ engine
Step 'Creating Python build environment'
$venv = Join-Path $Build 'venv'
Invoke-Native $python[0] (@($python | Select-Object -Skip 1) + @('-m', 'venv', $venv))
$venvPy = Join-Path $venv 'Scripts\python.exe'
Invoke-Native $venvPy @('-m', 'pip', 'install', '--quiet', '--upgrade', 'pip')
Invoke-Native $venvPy @('-m', 'pip', 'install', '--quiet', 'pyinstaller>=6,<7', 'pytest>=8')

if (-not $SkipTests) {
    Step 'Testing engine'
    Push-Location $Engine
    try { Invoke-Native $venvPy @('-m', 'pytest', '-q') } finally { Pop-Location }
}

Step 'Freezing engine with PyInstaller'
Invoke-Native $venvPy @(
    '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--console',
    '--name', 'prompt-forger-engine',
    '--distpath', (Join-Path $Build 'engine-dist'),
    '--workpath', (Join-Path $Build 'pyi-work'),
    '--specpath', (Join-Path $Build 'pyi-work'),
    '--paths', $Engine,
    (Join-Path $Engine 'engine_main.py'))
New-Item -ItemType Directory -Force -Path (Split-Path $Payload) | Out-Null
Copy-Item (Join-Path $Build 'engine-dist\prompt-forger-engine') $Payload -Recurse

Step 'Smoke-testing frozen engine'
$engineExe = Join-Path $Payload 'prompt-forger-engine.exe'
$reply = ('{"id":1,"method":"ping"}' | & $engineExe) -join ''
if ($LASTEXITCODE -ne 0 -or $reply -notmatch '"version"') { throw "Frozen engine did not answer ping. Got: $reply" }
Write-Host "Engine replied: $reply"

# ------------------------------------------------------------------ UI
Step 'Compiling JavaFX UI'
$classes = Join-Path $Build 'classes'
New-Item -ItemType Directory -Force -Path $classes | Out-Null
$sources = Get-ChildItem (Join-Path $AppSrc 'java') -Recurse -Filter *.java | ForEach-Object { '"' + ($_.FullName -replace '\\', '/') + '"' }
$argFile = Join-Path $Build 'sources.txt'
[IO.File]::WriteAllLines($argFile, $sources)
Invoke-Native 'javac' @('--release', '21', '-encoding', 'UTF-8', '-Xlint:all', '-Werror', '-d', $classes, "@$argFile")
Copy-Item (Join-Path $AppSrc 'resources\*') $classes -Recurse -Force

$mods = Join-Path $Build 'mods'
New-Item -ItemType Directory -Force -Path $mods | Out-Null
Invoke-Native 'jar' @('--create', '--file', (Join-Path $mods 'prompt-forger.jar'), '--main-class', $MainClass, '-C', $classes, '.')

# ------------------------------------------------------------------ package
Step 'Packaging app image'
$icon = Join-Path $PSScriptRoot 'icon.ico'
Invoke-Native 'jpackage' @(
    '--type', 'app-image', '--dest', $Dist,
    '--name', $AppName, '--app-version', $Version,
    '--vendor', 'Panwar Studio', '--description', 'Forge structured prompts for AI models',
    '--copyright', 'Copyright (c) 2026 Prince Panwar',
    '--module-path', $mods, '--module', "$Module/$MainClass",
    '--app-content', $Payload,
    '--icon', $icon,
    '--java-options', '-Dfile.encoding=UTF-8',
    '--jlink-options', '--strip-debug --no-header-files --no-man-pages --strip-native-commands')

$appImage = Join-Path $Dist $AppName
if (-not (Test-Path (Join-Path $appImage 'engine\prompt-forger-engine.exe'))) {
    throw "Engine missing from app image (expected $appImage\engine). Check jpackage --app-content layout."
}

$zip = Join-Path $Dist "$AppName-$Version-portable.zip"
Compress-Archive -Path $appImage -DestinationPath $zip -Force
Write-Host "Portable build: $zip"

if ($NoInstaller) { Write-Host 'Skipping installer (-NoInstaller).'; exit 0 }
if (-not (Get-Command candle.exe -ErrorAction SilentlyContinue)) {
    Write-Warning 'WiX Toolset 3 not found, so no .exe installer was built. Install it (e.g. "choco install wixtoolset") and re-run, or ship the portable zip.'
    exit 0
}

Step 'Building installer'
Invoke-Native 'jpackage' @(
    '--type', 'exe', '--dest', $Dist,
    '--app-image', $appImage,
    '--name', $AppName, '--app-version', $Version, '--vendor', 'Panwar Studio',
    '--win-menu', '--win-menu-group', 'Prompt Forger', '--win-shortcut', '--win-shortcut-prompt',
    '--win-dir-chooser', '--win-per-user-install', '--win-upgrade-uuid', $UpgradeUuid)
Get-ChildItem $Dist -Filter *.exe | ForEach-Object { Write-Host "Installer: $($_.FullName)" }
