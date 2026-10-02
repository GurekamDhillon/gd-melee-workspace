# Build and deploy the Qt 6 launcher. Run on Windows with VS 2022 and Qt >= 6.5 (MSVC x64).
param(
  [string]$Out = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "_build/release/GD Melee.exe"),
  [string]$QtRoot = $env:QT_ROOT_DIR,
  [string]$Generator = "Visual Studio 17 2022"
)
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$build = Join-Path $root "_build/launcher-qt-windows"
$Out = [System.IO.Path]::GetFullPath($Out)
$outDir = Split-Path $Out -Parent
$args = @("-S", (Join-Path $PSScriptRoot "launcher/qt"), "-B", $build,
          "-G", $Generator, "-A", "x64", "-DBUILD_TESTING=ON", "-DLAUNCHER_DEPLOY_QT=ON")
if ($QtRoot) {
  $args += "-DCMAKE_PREFIX_PATH=$QtRoot"
  # Tests and their child process must resolve this SDK's native Qt DLLs.
  $env:PATH = (Join-Path $QtRoot "bin") + ";" + $env:PATH
}
& cmake @args
if ($LASTEXITCODE -ne 0) { throw "Qt launcher configuration failed. Set QT_ROOT_DIR to an MSVC x64 Qt >= 6.5 installation." }
& cmake --build $build --config Release --parallel 8
if ($LASTEXITCODE -ne 0) { throw "Qt launcher compilation failed." }
& ctest --test-dir $build -C Release --output-on-failure --output-junit launcher-test-results.xml
if ($LASTEXITCODE -ne 0) {
  Get-Content (Join-Path $build "launcher-tests.txt") -ErrorAction SilentlyContinue
  Get-Content (Join-Path $build "Testing/Temporary/LastTest.log") -ErrorAction SilentlyContinue
  Get-Content (Join-Path $build "launcher-test-results.xml") -ErrorAction SilentlyContinue
  throw "Qt launcher tests failed."
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
& cmake --install $build --config Release --prefix (Join-Path $outDir "launcher")
if ($LASTEXITCODE -ne 0) { throw "Qt runtime deployment failed." }
# The static-runtime entry point keeps the x64 Qt CRT away from the x86 game CRT.
Copy-Item (Join-Path $build "Release/GD Melee.exe") $Out -Force
Write-Output "launcher: $Out (Qt runtime in launcher/)"
