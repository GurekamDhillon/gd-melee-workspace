# publish.ps1 - build the release zip and publish it as a GitHub release, in one command.
#
#   powershell -File tools\release\publish.ps1 -DryRun     # build + check + print what it would do
#   powershell -File tools\release\publish.ps1             # build + check + gh release create
#   ... -Version 0.2.0      (default: tools\release\VERSION)
#   ... -Repo owner/name    (default: GurekamDhillon/gd-melee-workspace)
#   ... -Draft              create the release as a draft, to look it over on GitHub first
#   ... -Server host:port   ship a netplay_server.txt (the address becomes public!)
#   ... -Force              publish despite provenance warnings (unpushed commits, stale exe)
#
# Why local and not CI: the game cannot be built on a GitHub runner today. It needs the clang 23
# toolchain unpacked in _toolchains (not in any repo), the multi-GB Aurora/Dawn/SDL3 build tree in
# _build\ax86m, gwtool, and the per-TU pipeline in _build\masstest; see tools\release\README.md.
# So the zip is built here from the local build, checked twice by check_release.ps1, and uploaded.
param(
  [string]$Version = "",
  [string]$Repo = "GurekamDhillon/gd-melee-workspace",
  [string]$Server = "",
  [switch]$Draft,
  [switch]$DryRun,
  [switch]$Force
)
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not $Version) { $Version = (Get-Content (Join-Path $PSScriptRoot "VERSION") -Raw).Trim() }
$tag = "v$Version"
$name = "GDMelee-$Version-win64"
$out = Join-Path $root "_build\release"
$zip = Join-Path $out "$name.zip"

# 1. the tag must be new. (Native commands that may fail run under "Continue": with "Stop",
# Windows PowerShell turns any stderr line from them into a terminating error.)
$ErrorActionPreference = "Continue"
if (-not $DryRun) {
  gh auth status 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "gh is not logged in (gh auth login)" }
}
$existing = gh release view $tag --repo $Repo --json tagName 2>$null
$tagTaken = ($LASTEXITCODE -eq 0 -and $existing)
# 2. the workspace commit the tag points at must be on GitHub, or the release links to nothing
$wsRev = (git -C $root rev-parse HEAD).Trim()
$wsPushed = git -C $root branch -r --contains $wsRev 2>$null | Where-Object { $_ -match '^\s*origin-ws/' }
$ErrorActionPreference = "Stop"
if ($tagTaken) { throw "$Repo already has a release $tag; bump tools\release\VERSION" }
if (-not $wsPushed) {
  $m = "workspace commit $($wsRev.Substring(0,9)) is not on origin-ws: push master first (git push origin-ws master)"
  if ($Force -or $DryRun) { Write-Output "warning: $m" } else { throw $m }
}

# 3. build (strict unless -Force: the melee commit must be public, the exe must contain it)
$buildArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "build_release.ps1"), "-Version", $Version)
if ($Server) { $buildArgs += @("-Server", $Server) }
if (-not ($Force -or $DryRun)) { $buildArgs += "-Strict" }
& powershell @buildArgs
if ($LASTEXITCODE -ne 0) { throw "build_release.ps1 failed" }

# 4. check the exact file we upload, once more
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "check_release.ps1") $zip -RepoRoot $root
if ($LASTEXITCODE -ne 0) { throw "release check failed: NOT publishing" }

# 5. notes
$ver = Get-Content (Join-Path $out "$name\version.txt")
$meleeRev = ($ver[1] -split '\s+')[1]
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
$notes = Join-Path $out "$name-notes.md"
# What's new / known issues for this version, written by hand in tools/release/notes/<version>.md.
$versionNotesFile = Join-Path $PSScriptRoot "notes\$Version.md"
$versionNotes = if (Test-Path $versionNotesFile) { (Get-Content $versionNotesFile -Raw -Encoding UTF8).Trim() } else { "" }
$body = @"
## GD's Melee $Version

A native Windows port of Super Smash Bros. Melee, built from the community decompilation.

$versionNotes

**This download contains no Nintendo game data.** You need your own disc image of Super Smash Bros. Melee, NTSC-U (USA) revision 1.02 (``GALE01``), as a plain ``.iso``. The ACE and Akaneia builds made from it work too.

### Install
1. Download **$name.zip** and unzip the whole folder somewhere you can write to (not Program Files).
2. Run **GD Melee.exe**. The first time, pick your ``.iso``; the launcher checks it and remembers it.
3. Press **PLAY**.

Windows SmartScreen may warn about an unsigned program: *More info > Run anyway*. Online play: see ``HOW TO PLAY ONLINE.txt`` in the zip.

### What's in the zip
The game (``melee-pc.exe``), the launcher (``GD Melee.exe``), their runtime libraries (SDL3, Dawn, the MSVC runtime), GD's Melee's own menu art, docs, and the licences of everything bundled (``LICENSES\``). ``MANIFEST.sha256`` lists every file.

### Source
- Game: [GurekamDhillon/melee@$($meleeRev.Substring(0,9))](https://github.com/GurekamDhillon/melee/tree/$meleeRev) (branch ``pc-port``)
- Launcher and release scripts: [gd-melee-workspace@$($wsRev.Substring(0,9))](https://github.com/$Repo/tree/$wsRev/tools/release)

``sha256($name.zip) = $zipHash``

Super Smash Bros. Melee is (c) Nintendo / HAL Laboratory. This project is not affiliated with or endorsed by them.
"@
[System.IO.File]::WriteAllText($notes, $body, (New-Object System.Text.UTF8Encoding $false))

# 6. publish
$ghArgs = @("release", "create", $tag, $zip, "$zip.sha256", "--repo", $Repo, "--target", $wsRev,
            "--title", "GD's Melee $Version", "--notes-file", $notes)
if ($Draft) { $ghArgs += "--draft" }
if ($DryRun) {
  Write-Output ""
  Write-Output "DRY RUN - would run:"
  Write-Output ("  gh " + (($ghArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '))
  Write-Output "notes: $notes"
  exit 0
}
& gh @ghArgs
if ($LASTEXITCODE -ne 0) { throw "gh release create failed" }
Write-Output "published $tag to https://github.com/$Repo/releases/tag/$tag"
