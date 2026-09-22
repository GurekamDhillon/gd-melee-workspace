# build_release.ps1 - assemble the public release zip: GDMelee-<version>-win64.zip
#
#   powershell -File tools\release\build_release.ps1                  # version from tools\release\VERSION
#   powershell -File tools\release\build_release.ps1 -Version 0.2.0   # override
#   ... -Server host:port       ship a netplay_server.txt (room codes work out of the box)
#   ... -GameDir <dir>          take melee-pc.exe and its DLLs from <dir> instead of _build
#   ... -Strict                 warnings (dirty melee tree, commit not on the public fork) become errors
#
# It packages what is ALREADY BUILT (_build\melee-pc.exe and friends): rebuild first if you changed
# code. Output goes to _build\release\ (git-ignored). It contains only:
#   our binaries (the game, the launcher), the runtime DLLs (SDL3, Dawn, the MSVC runtime), our own
#   UI art (_build\ui as committed), docs, licence notices, version.txt and MANIFEST.sha256.
# and then check_release.ps1 must pass on both the folder and the zip, or the script fails.
# Nothing is ever read from the disc-data folders; copy_in refuses them outright.
param(
  [string]$Version = "",
  [string]$Server = "",
  [string]$GameDir = "",
  [string]$OutDir = "",
  [switch]$Strict
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$build = Join-Path $root "_build"
if (-not $GameDir) { $GameDir = $build }
if (-not $OutDir) { $OutDir = Join-Path $build "release" }
if (-not $Version) { $Version = (Get-Content (Join-Path $PSScriptRoot "VERSION") -Raw).Trim() }
if ($Version -notmatch '^[0-9A-Za-z][0-9A-Za-z.\-]*$') { throw "bad version '$Version'" }
$name = "GDMelee-$Version-win64"
$stage = Join-Path $OutDir $name
$zipPath = Join-Path $OutDir "$name.zip"
$warnings = New-Object System.Collections.Generic.List[string]
function Warn([string]$m) { $warnings.Add($m); Write-Output "warning: $m" }

# Never read from these, whatever a future edit to this script asks for.
$forbidden = @("_build\ace", "_build\packs", "_build\m-ex", "_build\hsd_export", "_build\card", "_build\card-ace",
               "_build\USA", "akaneia-build", "menu\meleedump", "melee\orig") | ForEach-Object { (Join-Path $root $_).ToLowerInvariant() }
function Copy-In([string]$src, [string]$rel) {
  $full = [System.IO.Path]::GetFullPath($src)
  $low = $full.ToLowerInvariant()
  foreach ($f in $forbidden) { if ($low.StartsWith($f)) { throw "refusing to package $full : it is under $f (disc data)" } }
  if ($low -match '\.(iso|gcm|rvz|ciso|dol|dat|usd|gci)$') { throw "refusing to package $full : disc data extension" }
  if (-not (Test-Path $full -PathType Leaf)) { throw "missing: $full" }
  $dst = Join-Path $stage $rel
  New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
  Copy-Item $full $dst
}

# ---- provenance of the game build ---------------------------------------------------------------
$melee = Join-Path $root "melee"
$meleeRev = (git -C $melee rev-parse HEAD).Trim()
$meleeShort = $meleeRev.Substring(0, 9)
$wsRev = (git -C $root rev-parse --short=9 HEAD).Trim()
$dirty = git -C $melee status --porcelain --untracked-files=no -- src include pc extern
if ($dirty) { Warn "the melee checkout has uncommitted changes; the exe may not match commit $meleeShort (the GPL source offer points at that commit)" }
$ErrorActionPreference = "Continue"; $onPub = git -C $melee branch -r --contains $meleeRev 2>$null | Where-Object { $_ -match '^\s*pub/' }
$ErrorActionPreference = "Stop"
if (-not $onPub) { Warn "melee commit $meleeShort is not on the public fork (remote 'pub') yet: push pc-port before publishing" }
$exe = Join-Path $GameDir "melee-pc.exe"
$commitTime = [DateTimeOffset]::FromUnixTimeSeconds([long](git -C $melee log -1 --format=%ct)).LocalDateTime
if ((Get-Item $exe).LastWriteTime -lt $commitTime) { Warn "melee-pc.exe ($((Get-Item $exe).LastWriteTime)) is older than melee HEAD ($commitTime): rebuild so the exe contains the commit" }
$uiDirty = git -C $root status --porcelain -- _build/ui
if ($uiDirty) { throw "_build/ui has uncommitted changes; the release ships only committed art (commit or restore it first)" }
if ($Strict -and $warnings.Count -gt 0) { throw "-Strict: $($warnings.Count) warning(s) above" }

# ---- the MSVC runtime (app-local, as redist.txt allows) ------------------------------------------
$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
$crt = $null
if (Test-Path $vswhere) {
  # the newest runtime of every installed Visual Studio: it must be at least as new as the toolset
  # that linked melee-pc.exe
  $cands = foreach ($vs in (& $vswhere -all -products * -property installationPath)) {
    Get-ChildItem (Join-Path $vs "VC\Redist\MSVC\*\x86\Microsoft.VC*.CRT") -Directory -ErrorAction SilentlyContinue
  }
  $best = $cands | Where-Object { $_.Parent.Parent.Name -match '^[0-9.]+$' } |
          Sort-Object { [version]$_.Parent.Parent.Name } -Descending | Select-Object -First 1
  if ($best) { $crt = $best.FullName }
}
if (-not $crt) { throw "the x86 MSVC runtime redist folder (VC\Redist\MSVC\<ver>\x86\Microsoft.VC*.CRT) was not found; install the Visual Studio C++ workload" }

# ---- stage -----------------------------------------------------------------------------------------
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Write-Output "staging $name"
Write-Output "  melee $meleeShort, workspace $wsRev, MSVC runtime from $crt"

foreach ($f in "melee-pc.exe", "melee-pc.map", "SDL3.dll", "webgpu_dawn.dll", "initial_pipeline_cache.db", "initial_pipeline_cache.core") {
  Copy-In (Join-Path $GameDir $f) $f
}
foreach ($f in "msvcp140.dll", "msvcp140_atomic_wait.dll", "vcruntime140.dll") { Copy-In (Join-Path $crt $f) $f }

# the launcher, freshly compiled
& (Join-Path $PSScriptRoot "build_launcher.ps1") -Out (Join-Path $stage "GD Melee.exe") | Out-Null

# UI art: exactly the files committed under _build/ui
foreach ($rel in (git -C $root ls-files -- _build/ui)) {
  Copy-In (Join-Path $root $rel) ($rel.Substring("_build/".Length))
}

# docs and notices
Copy-In (Join-Path $PSScriptRoot "README-user.txt") "README.txt"
Copy-In (Join-Path $root "tools\netplay\HOW TO PLAY ONLINE.txt") "HOW TO PLAY ONLINE.txt"
Copy-In (Join-Path $PSScriptRoot "THIRD-PARTY-NOTICES.txt") "LICENSES\THIRD-PARTY-NOTICES.txt"
foreach ($l in Get-ChildItem (Join-Path $PSScriptRoot "licenses") -Filter *.txt) { Copy-In $l.FullName ("LICENSES\" + $l.Name) }
New-Item -ItemType Directory -Force -Path (Join-Path $stage "mods") | Out-Null
Set-Content -Path (Join-Path $stage "mods\README.txt") -Encoding ascii -Value @'
Mods go in this folder; the game always loads them, online too. Fighters and stages are matched
with your opponent by their content, so anything you both have can be picked online. A mods
browser that downloads and installs mods for you is coming.
'@
if ($Server) {
  if ($Server -notmatch '^[A-Za-z0-9.\-\[\]:]+:[0-9]{1,5}$') { throw "-Server must be host:port" }
  Set-Content -Path (Join-Path $stage "netplay_server.txt") -Value $Server -Encoding ascii
}
$date = Get-Date -Format "yyyy-MM-dd"
Set-Content -Path (Join-Path $stage "version.txt") -Encoding ascii -Value @(
  "$Version (melee $meleeShort)",
  "melee      $meleeRev  https://github.com/GurekamDhillon/melee/tree/$meleeRev",
  "workspace  $wsRev  https://github.com/GurekamDhillon/gd-melee-workspace",
  "built      $date"
)

# manifest: sha256sum format, '/' separators, sorted
$sha = [System.Security.Cryptography.SHA256]::Create()
$base = $stage.TrimEnd('\') + '\'
$lines = foreach ($f in (Get-ChildItem $stage -Recurse -File | Sort-Object FullName)) {
  $rel = $f.FullName.Substring($base.Length).Replace('\', '/')
  $h = (($sha.ComputeHash([System.IO.File]::ReadAllBytes($f.FullName)) | ForEach-Object { $_.ToString("x2") }) -join '')
  "$h  $rel"
}
[System.IO.File]::WriteAllText((Join-Path $stage "MANIFEST.sha256"), (($lines -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding $false))

# ---- check the folder, zip it, check the zip --------------------------------------------------------
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "check_release.ps1") $stage -RepoRoot $root
if ($LASTEXITCODE -ne 0) { throw "release check failed on the staged folder; nothing was zipped" }
# written entry by entry: .NET Framework's CreateFromDirectory stores '' separators under
# Windows PowerShell, which other unzippers turn into file names with backslashes in them
$zs = [System.IO.File]::Open($zipPath, [System.IO.FileMode]::CreateNew)
$za = New-Object System.IO.Compression.ZipArchive $zs, ([System.IO.Compression.ZipArchiveMode]::Create)
try {
  foreach ($f in (Get-ChildItem $stage -Recurse -File | Sort-Object FullName)) {
    $entry = $za.CreateEntry("$name/" + $f.FullName.Substring($base.Length).Replace('\', '/'), [System.IO.Compression.CompressionLevel]::Optimal)
    $entry.LastWriteTime = $f.LastWriteTime
    $es = $entry.Open(); $in = [System.IO.File]::OpenRead($f.FullName)
    $in.CopyTo($es); $in.Close(); $es.Close()
  }
} finally { $za.Dispose(); $zs.Close() }
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "check_release.ps1") $zipPath -RepoRoot $root
if ($LASTEXITCODE -ne 0) { Remove-Item $zipPath -Force; throw "release check failed on the zip; it was deleted" }

$zipHash = (Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Path "$zipPath.sha256" -Encoding ascii -Value "$zipHash  $name.zip"
$mb = [Math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Output ""
Write-Output "zip:     $zipPath ($mb MB)"
Write-Output "sha256:  $zipHash"
if ($warnings.Count -gt 0) { Write-Output "$($warnings.Count) warning(s) - read them before publishing" }
