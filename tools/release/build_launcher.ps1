# Build and deploy the Qt 6 launcher with an installed MSVC x64 toolset and Qt >= 6.5.
param(
  [string]$Out = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "_build/release/GD Melee.exe"),
  [string]$QtRoot = $env:QT_ROOT_DIR,
  [string]$Generator = "",
  [string]$BuildDir = "",
  [string]$CMake = "cmake"
)
$ErrorActionPreference = "Stop"
function Invoke-NativeTool([string]$Executable, [string[]]$Arguments) {
  # Windows PowerShell 5.1 can promote harmless native stderr to an exception
  # when the caller redirects streams. Native tools define failure by exit code.
  $ErrorActionPreference = 'Continue'
  # A tool that is not on PATH never runs, so it never sets LASTEXITCODE: without this
  # sentinel the previous tool's 0 would be read as this one's success.
  $global:LASTEXITCODE = -1
  & $Executable @Arguments
  $script:NativeToolExit = $global:LASTEXITCODE
}
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$build = if ($BuildDir) { [System.IO.Path]::GetFullPath($BuildDir) } else { Join-Path $root "_build/launcher-qt-windows" }
$ctest = 'ctest'
if (Split-Path $CMake -Parent) { $ctest = Join-Path (Split-Path $CMake -Parent) 'ctest.exe' }
# windeployqt can return success without deploying a CRT when VCINSTALLDIR is unset.
# Resolve and copy an app-local x64 runtime explicitly, independent of the x86 game.
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$crt = $null
if (Test-Path $vswhere) {
  $installations = (& $vswhere -all -products * -format json | ConvertFrom-Json)
  $latest = $installations | Sort-Object { [version]$_.installationVersion } -Descending | Select-Object -First 1
  if (-not $Generator -and $latest) {
    $Generator = if ([version]$latest.installationVersion -ge [version]'18.0') { 'Visual Studio 18 2026' } else { 'Visual Studio 17 2022' }
  }
  $candidates = foreach ($vs in $installations) {
    Get-ChildItem (Join-Path $vs.installationPath 'VC/Redist/MSVC/*/x64/Microsoft.VC*.CRT') -Directory -ErrorAction SilentlyContinue
  }
  $best = $candidates | Sort-Object { [version]$_.Parent.Parent.Name } -Descending | Select-Object -First 1
  if ($best) { $crt = $best.FullName }
}
if (-not $Generator) { $Generator = 'Visual Studio 17 2022' }
if (-not $crt) { throw 'No x64 MSVC app-local runtime found; install the Visual Studio C++ workload.' }
$env:PATH = $crt + ';' + $env:PATH
$Out = [System.IO.Path]::GetFullPath($Out)
$outDir = Split-Path $Out -Parent
$args = @("-S", (Join-Path $PSScriptRoot "launcher/qt"), "-B", $build,
          "-G", $Generator, "-A", "x64", "-DBUILD_TESTING=ON", "-DLAUNCHER_DEPLOY_QT=ON")
if ($QtRoot) {
  $args += "-DCMAKE_PREFIX_PATH=$QtRoot"
  # Tests and their child process must resolve this SDK's native Qt DLLs.
  $env:PATH = (Join-Path $QtRoot "bin") + ";" + $env:PATH
}
Invoke-NativeTool $CMake $args
if ($NativeToolExit -ne 0) { throw "Qt launcher configuration failed. Set QT_ROOT_DIR to an MSVC x64 Qt >= 6.5 installation." }
Invoke-NativeTool $CMake @('--build', $build, '--config', 'Release', '--parallel', '8')
if ($NativeToolExit -ne 0) { throw "Qt launcher compilation failed." }
Invoke-NativeTool $ctest @('--test-dir', $build, '-C', 'Release', '--output-on-failure', '--output-junit', 'launcher-test-results.xml')
if ($NativeToolExit -ne 0) {
  Get-Content (Join-Path $build "launcher-tests.txt") -ErrorAction SilentlyContinue
  Get-Content (Join-Path $build "Testing/Temporary/LastTest.log") -ErrorAction SilentlyContinue
  Get-Content (Join-Path $build "launcher-test-results.xml") -ErrorAction SilentlyContinue
  throw "Qt launcher tests failed."
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Invoke-NativeTool $CMake @('--install', $build, '--config', 'Release', '--prefix', (Join-Path $outDir 'launcher'))
if ($NativeToolExit -ne 0) { throw "Qt runtime deployment failed." }
# The static-runtime entry point keeps the x64 Qt CRT away from the x86 game CRT.
Copy-Item (Join-Path $build "Release/GD Melee.exe") $Out -Force
$launcherBin = Join-Path $outDir 'launcher/bin'
foreach ($name in 'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll') {
  Copy-Item (Join-Path $crt $name) (Join-Path $launcherBin $name) -Force
}
foreach ($name in 'msvcp140_1.dll', 'msvcp140_2.dll', 'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll', 'concrt140.dll') {
  if (Test-Path (Join-Path $crt $name)) { Copy-Item (Join-Path $crt $name) (Join-Path $launcherBin $name) -Force }
}
# Official SDK diagnostic strings contain vendor build-user roots. Redact
# deployed copies in place; modified Qt copies are explicitly unsigned.
# Never change the SDK itself or invalidate a Microsoft CRT signature.
Invoke-NativeTool 'python' @((Join-Path $PSScriptRoot 'sanitize_launcher.py'), '--strip-qt-signatures', (Join-Path $outDir 'launcher'), $Out)
if ($NativeToolExit -ne 0) { throw 'Launcher path sanitization failed.' }
Add-Content -Encoding ascii -Path (Join-Path $outDir 'launcher/qt-build.txt') -Value 'Deployed Qt diagnostic roots redacted in place; modified Qt copies are explicitly unsigned (vendor Authenticode removed). SDK and Microsoft CRT signatures unchanged.'

# Test the deployed app without any SDK or toolset DLL directories in PATH.
Invoke-NativeTool 'python' @((Join-Path $PSScriptRoot 'verify_launcher_runtime.py'), $outDir)
if ($NativeToolExit -ne 0) { throw 'Deployed launcher smoke test failed.' }
Write-Output "launcher: $Out (Qt runtime in launcher/)"
