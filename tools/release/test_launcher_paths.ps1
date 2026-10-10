# Path/overwrite regressions only: no compiler, Qt, CMake or game is run.
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'build_launcher.ps1'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($source, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$definition = $ast.Find({
  param($node)
  $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-LauncherBuildPaths'
}, $true)
if (-not $definition) { throw 'build_launcher.ps1 has no Get-LauncherBuildPaths function' }
# Load the real preflight without executing the build script's native-tool calls.
. ([scriptblock]::Create($definition.Extent.Text))

function Assert-Equal($Actual, $Expected) {
  if ($Actual -cne $Expected) { throw "expected '$Expected', got '$Actual'" }
}
function Assert-ProtectedOutput([string]$OutputPath) {
  $rejected = $false
  try {
    Get-LauncherBuildPaths -OutputPath $OutputPath -BuildPath 'qt' -RepoRoot $repo | Out-Null
  } catch {
    if ($_.Exception.Message -notlike '*Pass -Release*') { throw }
    $rejected = $true
  }
  if (-not $rejected) { throw "accepted protected launcher output: $OutputPath" }
}

$fixtureParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/')
$fixtureRoot = Join-Path $fixtureParent ('gd-launcher-paths-' + [guid]::NewGuid().ToString('N'))
$repo = Join-Path $fixtureRoot 'repo'
$caller = Join-Path $fixtureRoot 'caller'
$otherDirectory = Join-Path $fixtureRoot 'process-directory'
$processDirectory = [Environment]::CurrentDirectory
$originalPath = $env:PATH
$locationPushed = $false
$junction = $null
$escapeJunction = $null
try {
  New-Item -ItemType Directory -Path $repo, $caller, $otherDirectory -Force | Out-Null
  Push-Location $caller
  $locationPushed = $true
  # Reproduce Set-Location and .NET having different current directories.
  [Environment]::CurrentDirectory = $otherDirectory
  $paths = Get-LauncherBuildPaths -OutputPath 'package/GD Melee.exe' -BuildPath 'obj/../qt' -RepoRoot $repo
  Assert-Equal $paths.Out (Join-Path $caller 'package/GD Melee.exe')
  Assert-Equal $paths.BuildDir (Join-Path $caller 'qt')

  $absoluteOut = Join-Path $fixtureRoot 'absolute/GD Melee.exe'
  $absoluteBuild = Join-Path $fixtureRoot 'absolute-qt'
  $paths = Get-LauncherBuildPaths -OutputPath $absoluteOut -BuildPath $absoluteBuild -RepoRoot $repo
  Assert-Equal $paths.Out $absoluteOut
  Assert-Equal $paths.BuildDir $absoluteBuild
  $paths = Get-LauncherBuildPaths -OutputPath 'package/GD Melee.exe' -BuildPath '' -RepoRoot $repo
  Assert-Equal $paths.BuildDir (Join-Path $repo '_build/launcher-qt-windows')

  $protected = Join-Path $repo '_build/release/GD Melee.exe'
  Assert-ProtectedOutput $protected
  Assert-ProtectedOutput (Join-Path $repo '_build/release/nested/GD Melee.exe')
  Assert-ProtectedOutput (Join-Path $repo '_BUILD/RELEASE/GD Melee.exe')
  Assert-ProtectedOutput '../repo/_build/release/../release/GD Melee.exe'
  $paths = Get-LauncherBuildPaths -OutputPath $protected -BuildPath 'qt' -RepoRoot $repo -Release
  Assert-Equal $paths.Out $protected
  $sibling = Join-Path $repo '_build/release-dev/GD Melee.exe'
  $paths = Get-LauncherBuildPaths -OutputPath $sibling -BuildPath 'qt' -RepoRoot $repo
  Assert-Equal $paths.Out $sibling

  # Exercise the real script's default output guard as well as its helper.
  # A nonexistent CMake path prevents a build even if preflight regresses.
  $rejectedDefault = $false
  try {
    & $source -CMake (Join-Path $fixtureRoot 'must-not-run.exe') -BuildDir (Join-Path $fixtureRoot 'unused-qt') -QtRoot '' | Out-Null
  } catch {
    if ($_.Exception.Message -notlike '*Pass -Release*') { throw }
    $rejectedDefault = $true
  }
  if (-not $rejectedDefault) { throw 'default release output did not require -Release' }

  $sharedBuild = Join-Path $fixtureRoot 'shared-build'
  New-Item -ItemType Directory -Path $sharedBuild -Force | Out-Null
  $junction = Join-Path $repo '_build'
  New-Item -ItemType Junction -Path $junction -Target $sharedBuild | Out-Null
  Assert-ProtectedOutput $protected
  Assert-ProtectedOutput (Join-Path $sharedBuild 'release/nested/GD Melee.exe')
  # A junction leading out of release must not permit deployment into its parent.
  $outsideRelease = Join-Path $fixtureRoot 'outside-release'
  New-Item -ItemType Directory -Path $outsideRelease, (Join-Path $sharedBuild 'release') -Force | Out-Null
  $escapeJunction = Join-Path $junction 'release/redirect'
  New-Item -ItemType Junction -Path $escapeJunction -Target $outsideRelease | Out-Null
  Assert-ProtectedOutput (Join-Path $escapeJunction 'GD Melee.exe')
  $paths = Get-LauncherBuildPaths -OutputPath $protected -BuildPath 'qt' -RepoRoot $repo -Release
  Assert-Equal $paths.Out $protected
  Write-Output 'launcher caller-directory and protected-release path checks passed'
} finally {
  if ($locationPushed) { Pop-Location }
  [Environment]::CurrentDirectory = $processDirectory
  $env:PATH = $originalPath
  # All fixtures, including the junction target, must stay in this temp root.
  $cleanup = [System.IO.Path]::GetFullPath($fixtureRoot)
  if (-not $cleanup.StartsWith($fixtureParent + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "refusing cleanup outside temporary directory: $cleanup"
  }
  # Delete each junction itself without traversing its target.
  if ($escapeJunction -and (Test-Path -LiteralPath $escapeJunction)) { [System.IO.Directory]::Delete($escapeJunction) }
  if ($junction -and (Test-Path -LiteralPath $junction)) { [System.IO.Directory]::Delete($junction) }
  if (Test-Path -LiteralPath $cleanup) { Remove-Item -LiteralPath $cleanup -Recurse -Force }
}
