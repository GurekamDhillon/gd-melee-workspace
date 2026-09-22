# check_release.ps1 - prove a release folder or zip holds only what we may redistribute.
#
#   powershell -File tools\release\check_release.ps1 <folder or .zip> [-RepoRoot <workspace root>]
#
# Exit code 0 = clean. Anything else = the release must NOT be published; every problem is listed.
# build_release.ps1 runs this on the staged folder AND on the finished zip; publish.ps1 runs it once
# more on the exact file it uploads.
#
# The rules, strictest first:
#   1. An allowlist. Every file must be one of the named top-level binaries, or have one of a few
#      extensions we produce (.gxtex/.json under ui\, .txt/.md docs, .sha256). Anything else fails,
#      so a new kind of file has to be added here on purpose.
#   2. A denylist with clear messages for disc data: .iso .gcm .rvz .ciso .wbfs .nkit .dol .dat .usd
#      .hps .thp .mth .ssm .sem .gci .tpl .bnr .png .bmp .tga .dds ... and folders named after the
#      places disc data lives in this workspace (ace, packs, akaneia-build, meleedump, card...).
#   3. Content sniffing on every file, whatever its name: a GameCube/Wii disc header, an RVZ/WIA
#      container, a memory-card save (GCI: "GALE01" at offset 0), an HSD archive (.dat: the first
#      word is the file's own size), a DOL (text section table pointing inside the file at 0x100).
#   4. ui\ must be byte-identical to the art committed in the workspace repo (_build/ui at HEAD):
#      alpha's original art, and nothing that crept in beside it.
#   5. No file bigger than 64 MB, no personal paths (C:\Users\<name>) inside binaries, the licence
#      files present, and MANIFEST.sha256 matching every file.
param(
  [Parameter(Mandatory = $true, Position = 0)][string]$Path,
  [string]$RepoRoot = ""
)
$ErrorActionPreference = "Stop"
if (-not $RepoRoot) { $RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent }
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem

$AllowedBinaries = @("GD Melee.exe", "melee-pc.exe", "SDL3.dll", "webgpu_dawn.dll",
                     "msvcp140.dll", "msvcp140_atomic_wait.dll", "vcruntime140.dll")
$AllowedTopFiles = @("melee-pc.map", "initial_pipeline_cache.db", "initial_pipeline_cache.core",
                     "README.txt", "HOW TO PLAY ONLINE.txt", "version.txt", "MANIFEST.sha256",
                     "netplay_server.txt")
$DiscExt = @(".iso", ".gcm", ".rvz", ".wia", ".ciso", ".wbfs", ".nkit", ".gcz", ".dol", ".dat", ".usd",
             ".hps", ".thp", ".mth", ".ssm", ".sem", ".gci", ".sav", ".raw", ".tpl", ".bnr", ".rel", ".elf",
             ".png", ".bmp", ".tga", ".dds", ".jpg", ".jpeg", ".tex", ".bin", ".wav", ".ogg", ".mp3", ".obj", ".glb")
$DiscDirs = @("ace", "packs", "akaneia-build", "akaneia", "meleedump", "card", "card-ace", "card-empty",
              "card-trophy", "userdata", "crashlogs", "hsd_export", "m-ex", "menutex", "gltf", "orig", "files", "sys")
$Required = @("README.txt", "version.txt", "MANIFEST.sha256", "LICENSES/GPL-2.0.txt",
              "LICENSES/THIRD-PARTY-NOTICES.txt", "melee-pc.exe", "GD Melee.exe")

$problems = New-Object System.Collections.Generic.List[string]
function Fail([string]$msg) { $problems.Add($msg) }

# ---- enumerate: (relative path with '/', bytes) -----------------------------------------------
$entries = New-Object System.Collections.Generic.List[object]
$full = (Resolve-Path $Path).Path
if ((Get-Item $full) -is [System.IO.DirectoryInfo]) {
  $base = $full.TrimEnd('\') + '\'
  foreach ($f in Get-ChildItem $full -Recurse -File -Force) {
    $entries.Add([pscustomobject]@{ Rel = $f.FullName.Substring($base.Length).Replace('\', '/'); Bytes = [System.IO.File]::ReadAllBytes($f.FullName) })
  }
} else {
  $zip = [System.IO.Compression.ZipFile]::OpenRead($full)
  try {
    $names = @($zip.Entries | ForEach-Object { $_.FullName })
    if ($names | Where-Object { $_ -match '\\' }) { Fail "zip entries use '\' separators (unzips wrongly outside Windows)" }
    # a release zip holds exactly one top folder: GDMelee-<version>-win64/
    $tops = @($names | ForEach-Object { ($_ -replace '\\', '/').Split('/')[0] } | Sort-Object -Unique)
    if ($tops.Count -ne 1) { Fail "zip should contain one top-level folder, found: $($tops -join ', ')" }
    foreach ($e in $zip.Entries) {
      $rel = ($e.FullName -replace '\\', '/')
      if ($rel.EndsWith('/')) { continue }
      if ($tops.Count -eq 1) { $rel = $rel.Substring($tops[0].Length + 1) }
      $ms = New-Object System.IO.MemoryStream
      $s = $e.Open(); $s.CopyTo($ms); $s.Close()
      $entries.Add([pscustomobject]@{ Rel = $rel; Bytes = $ms.ToArray() })
    }
  } finally { $zip.Dispose() }
}
if ($entries.Count -eq 0) { Fail "no files found in $Path" }

function BE32([byte[]]$b, [int]$o) {
  if ($b.Length -lt $o + 4) { return -1 }
  # as [int64]: PowerShell reads a hex literal like 0xC2339F3D as a NEGATIVE int32, so every
  # constant below is compared as a positive int64 instead
  return ([int64]$b[$o] * 16777216) + ([int64]$b[$o + 1] * 65536) + ([int64]$b[$o + 2] * 256) + [int64]$b[$o + 3]
}
function Ascii([byte[]]$b, [int]$o, [int]$n) {
  if ($b.Length -lt $o + $n) { return "" }
  return [System.Text.Encoding]::ASCII.GetString($b, $o, $n)
}

# ---- ui\ at HEAD in the workspace repo: rel -> git blob sha1 --------------------------------
$uiBlobs = @{}
$haveRepo = Test-Path (Join-Path $RepoRoot ".git")
if ($haveRepo) {
  foreach ($line in (git -C $RepoRoot ls-tree -r HEAD -- _build/ui)) {
    # <mode> blob <sha>\t<path>
    $parts = $line -split "`t"
    $sha = ($parts[0] -split ' ')[2]
    $uiBlobs[$parts[1].Substring("_build/".Length)] = $sha
  }
}
$sha1 = [System.Security.Cryptography.SHA1]::Create()
function GitBlobSha([byte[]]$b) {
  $hdr = [System.Text.Encoding]::ASCII.GetBytes("blob $($b.Length)`0")
  $all = New-Object byte[] ($hdr.Length + $b.Length)
  [Array]::Copy($hdr, $all, $hdr.Length); [Array]::Copy($b, 0, $all, $hdr.Length, $b.Length)
  return (($sha1.ComputeHash($all) | ForEach-Object { $_.ToString("x2") }) -join '')
}

$sha256 = [System.Security.Cryptography.SHA256]::Create()
$hashes = @{}
$userPath = [regex]'(?i)[A-Z]:[\\/]Users[\\/](?!Public[\\/]|Default[\\/])[A-Za-z0-9._ -]{2,}[\\/]'

foreach ($e in $entries) {
  $rel = $e.Rel; $b = $e.Bytes
  $name = [System.IO.Path]::GetFileName($rel)
  $ext = [System.IO.Path]::GetExtension($rel).ToLowerInvariant()
  $dirs = @($rel.Split('/') | Select-Object -SkipLast 1)
  $hashes[$rel] = (($sha256.ComputeHash($b) | ForEach-Object { $_.ToString("x2") }) -join '')

  # 2. denylist first, for the clearest message
  if ($DiscExt -contains $ext) { Fail "$rel : '$ext' files are disc data (or could hold it) and never ship" }
  foreach ($d in $dirs) { if ($DiscDirs -contains $d.ToLowerInvariant()) { Fail "$rel : inside a '$d' folder, which is where disc data or saves live" } }

  # 1. allowlist
  $ok = $false
  if ($dirs.Count -eq 0) {
    $ok = ($AllowedBinaries -contains $name) -or ($AllowedTopFiles -contains $name)
  } elseif ($dirs[0] -eq "ui") {
    $ok = ($dirs.Count -eq 1) -and ($ext -eq ".gxtex" -or $ext -eq ".json")
  } elseif ($dirs[0] -eq "LICENSES") {
    $ok = ($dirs.Count -eq 1) -and ($ext -eq ".txt")
  } elseif ($dirs[0] -eq "mods") {
    $ok = ($rel -eq "mods/README.txt")
  }
  if (-not $ok) { Fail "$rel : not on the release allowlist (tools/release/check_release.ps1)" }
  if (($ext -eq ".exe" -or $ext -eq ".dll") -and -not ($dirs.Count -eq 0 -and $AllowedBinaries -contains $name)) {
    Fail "$rel : unexpected executable"
  }

  # 3. content sniffing
  if ($b.Length -ge 0x20 -and (BE32 $b 0x1C) -eq 3258163005L) { Fail "$rel : contains a GameCube disc header" }
  if ($b.Length -ge 0x20 -and (BE32 $b 0x18) -eq 1562156707L) { Fail "$rel : contains a Wii disc header" }
  $m4 = Ascii $b 0 4
  if ($m4 -eq "RVZ$([char]1)" -or $m4 -eq "WIA$([char]1)" -or $m4 -eq "CISO") { Fail "$rel : is a compressed disc image" }
  if ((Ascii $b 0 4) -match '^G[A-Z]{2}[EPJ]$' -and (Ascii $b 4 2) -match '^[0-9A-Z]{2}$') { Fail "$rel : starts with a game ID ($(Ascii $b 0 6)): a memory-card save or disc header" }
  if ($ext -ne ".exe" -and $ext -ne ".dll" -and $b.Length -ge 0x20 -and (BE32 $b 0) -eq $b.Length) { Fail "$rel : looks like an HSD archive (.dat): its first word is its own size" }
  if ($b.Length -ge 0x100 -and $ext -ne ".exe" -and $ext -ne ".dll") {
    # DOL: 7 text + 11 data section offsets, then 18 load addresses in 0x80000000-0x81800000
    $t0 = BE32 $b 0; $a0 = BE32 $b 0x48; $entry = BE32 $b 0xE0
    if ($t0 -eq 0x100 -and $a0 -ge 2147483648L -and $a0 -lt 2172649472L -and $entry -ge 2147483648L -and $entry -lt 2172649472L) { Fail "$rel : looks like a DOL (GameCube executable)" }
  }
  if ($ext -eq ".exe" -or $ext -eq ".dll" -or $ext -eq ".map" -or $ext -eq ".db") {
    $text = [System.Text.Encoding]::GetEncoding(28591).GetString($b)
    $m = $userPath.Match($text)
    if ($m.Success) { Fail "$rel : contains a personal path ($($m.Value)...)" }
  }

  # 4. ui art must be the committed art
  if ($dirs.Count -ge 1 -and $dirs[0] -eq "ui") {
    if (-not $haveRepo) { Fail "$rel : cannot verify ui art (no workspace repo at $RepoRoot)" }
    elseif (-not $uiBlobs.ContainsKey($rel)) { Fail "$rel : not committed under _build/ui in the workspace repo" }
    elseif ($uiBlobs[$rel] -ne (GitBlobSha $b)) {
      # text files are checked out with CRLF (core.autocrlf) but committed with LF
      $lf = if ($ext -eq ".json") { [System.Text.Encoding]::UTF8.GetBytes(([System.Text.Encoding]::UTF8.GetString($b) -replace "`r`n", "`n")) } else { $null }
      if ($lf -eq $null -or $uiBlobs[$rel] -ne (GitBlobSha $lf)) { Fail "$rel : differs from the committed _build/ui art" }
    }
  }

  # 5. size
  if ($b.Length -gt 64MB) { Fail "$rel : $([Math]::Round($b.Length / 1MB)) MB is too big for anything we ship" }
}

foreach ($r in $Required) { if (-not $hashes.ContainsKey($r)) { Fail "missing required file: $r" } }

# 5. manifest: every file listed once with the right hash, and nothing listed that is absent
$man = $entries | Where-Object { $_.Rel -eq "MANIFEST.sha256" } | Select-Object -First 1
if ($man) {
  $listed = @{}
  foreach ($line in ([System.Text.Encoding]::UTF8.GetString($man.Bytes) -split "`r?`n")) {
    if ($line -match '^([0-9a-f]{64})  (.+)$') { $listed[$Matches[2]] = $Matches[1] }
  }
  foreach ($k in $hashes.Keys) {
    if ($k -eq "MANIFEST.sha256") { continue }
    if (-not $listed.ContainsKey($k)) { Fail "$k : not in MANIFEST.sha256" }
    elseif ($listed[$k] -ne $hashes[$k]) { Fail "$k : sha256 does not match MANIFEST.sha256" }
  }
  foreach ($k in $listed.Keys) { if (-not $hashes.ContainsKey($k)) { Fail "$k : listed in MANIFEST.sha256 but missing" } }
}

$totalMb = [Math]::Round((($entries | ForEach-Object { $_.Bytes.Length } | Measure-Object -Sum).Sum) / 1MB, 1)
if ($problems.Count -gt 0) {
  Write-Output "RELEASE CHECK FAILED: $Path"
  foreach ($p in $problems) { Write-Output "  x $p" }
  exit 1
}
Write-Output "release check OK: $($entries.Count) files, $totalMb MB, no disc data ($Path)"
exit 0
