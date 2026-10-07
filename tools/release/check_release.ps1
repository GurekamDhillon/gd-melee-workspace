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
#      Mods (mods\<id>\...) are checked against tools\release\mod_rules.json, the same table that
#      build_release.ps1 copies by: a known mod id, and inside it only paths that match that mod's allow
#      patterns (.lua .wgsl .gxmesh .gxtex .json .genoasm .words ...). Mod ids on the never-package list
#      (envoy_drives_sa2, local-assets, ported or private fighters, ACE/Akaneia packs) fail by name.
#   2b. The one `.dat` exception: the Courier's own built files. A .dat is accepted only if mods\original-assets.json
#      lists it with a matching sha256 (written at package time from the build record of
#      tools/geno/build_courier.sh), its path matches the mod's original_dat pattern (Gn<Name>_<costume>.dat,
#      never a disc name such as Pl*.dat), it is under 8 MB, it contains the mod's own symbol names and NO symbol
#      of any other fighter (every `Ply<Name>_` token must be Courier's). Every other sniff still runs on it.
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
                     "netplay_server.txt", "build-provenance.json")
$DiscExt = @(".iso", ".gcm", ".rvz", ".wia", ".ciso", ".wbfs", ".nkit", ".gcz", ".dol", ".dat", ".usd",
             ".hps", ".thp", ".mth", ".ssm", ".sem", ".gci", ".sav", ".raw", ".tpl", ".bnr", ".rel", ".elf",
             ".png", ".bmp", ".tga", ".dds", ".jpg", ".jpeg", ".tex", ".bin", ".wav", ".ogg", ".mp3", ".obj", ".glb")
$DiscDirs = @("ace", "packs", "akaneia-build", "akaneia", "meleedump", "card", "card-ace", "card-empty",
              "card-trophy", "userdata", "crashlogs", "hsd_export", "m-ex", "menutex", "gltf", "orig", "files", "sys")
$Required = @("README.txt", "version.txt", "MANIFEST.sha256", "LICENSES/GPL-2.0.txt",
              "LICENSES/THIRD-PARTY-NOTICES.txt", "melee-pc.exe", "melee-pc.map", "GD Melee.exe",
              "SDL3.dll", "webgpu_dawn.dll", "msvcp140.dll", "msvcp140_atomic_wait.dll", "vcruntime140.dll",
              "initial_pipeline_cache.db", "initial_pipeline_cache.core", "HOW TO PLAY ONLINE.txt",
              "build-provenance.json", "launcher/bin/gd-melee-launcher.exe", "launcher/bin/Qt6Core.dll",
              "launcher/bin/Qt6Gui.dll", "launcher/bin/Qt6Widgets.dll", "launcher/bin/qt.conf",
              "launcher/bin/msvcp140.dll", "launcher/bin/vcruntime140.dll", "launcher/bin/vcruntime140_1.dll",
              "launcher/qt-build.txt", "launcher/licenses/LGPL-3.0-only.txt",
              "launcher/licenses/Qt-GPL-exception-1.0.txt", "launcher/licenses/SourceSans3-OFL-1.1.txt",
              "launcher/licenses/BarlowCondensed-OFL-1.1.txt")

$ModRules = Get-Content (Join-Path $PSScriptRoot "mod_rules.json") -Raw | ConvertFrom-Json
$ModTopFiles = @("README.txt", "sources.txt", "enabled.txt", "original-assets.json")

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

# mods\original-assets.json: rel path -> sha256 of the built original files the package claims to hold
$OriginalAssets = @{}
$oaEntry = $entries | Where-Object { $_.Rel -eq "mods/original-assets.json" } | Select-Object -First 1
if ($oaEntry) {
  try {
    $oa = [System.Text.Encoding]::UTF8.GetString($oaEntry.Bytes) | ConvertFrom-Json
    foreach ($f in @($oa.files)) {
      if ($f.sha256 -notmatch '^[0-9a-f]{64}$' -or -not $f.path) { throw "bad entry" }
      $OriginalAssets[[string]$f.path] = [string]$f.sha256
    }
  } catch { Fail "mods/original-assets.json is malformed: $($_.Exception.Message)" }
}

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
if (-not $haveRepo -or $uiBlobs.Count -eq 0) { Fail "cannot verify required ui art (no committed _build/ui at $RepoRoot)" }
$Required += @($uiBlobs.Keys)
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
  if ($rel -match '(^/|\\|(^|/)\.\.?(/|$)|:)' -or -not $rel) { Fail "$rel : unsafe release path" }
  if ($hashes.ContainsKey($rel)) { Fail "$rel : duplicate release entry" }
  $name = [System.IO.Path]::GetFileName($rel)
  $ext = [System.IO.Path]::GetExtension($rel).ToLowerInvariant()
  $dirs = @($rel.Split('/') | Select-Object -SkipLast 1)
  $hashes[$rel] = (($sha256.ComputeHash($b) | ForEach-Object { $_.ToString("x2") }) -join '')

  # 2. denylist first, for the clearest message
  # the Courier's own built .dat files: path + record + symbol checks (see 2b above); any other .dat is disc data
  $origDat = $false
  if ($ext -eq ".dat" -and $dirs.Count -ge 3 -and $dirs[0] -eq "mods") {
    $modRule = $ModRules.mods.$($dirs[1])
    $inModDat = (@($dirs | Select-Object -Skip 2) + $name) -join '/'
    if ($modRule -and $modRule.original_dat -and $inModDat -cmatch ('^(?:' + $modRule.original_dat + ')$')) {
      $origDat = $true
      $recorded = $OriginalAssets[$rel]
      if (-not $recorded) { Fail "$rel : a .dat that mods/original-assets.json does not list is disc data (or could be) and never ships"; $origDat = $false }
      elseif ($recorded -ne $hashes[$rel]) { Fail "$rel : sha256 does not match mods/original-assets.json"; $origDat = $false }
      elseif ($b.Length -gt 8MB) { Fail "$rel : an original .dat is never this big ($([Math]::Round($b.Length / 1MB)) MB)"; $origDat = $false }
      else {
        $txt = [System.Text.Encoding]::GetEncoding(28591).GetString($b)
        $prefix = [string]$modRule.original_dat_symbol_prefix
        if ($txt.IndexOf($prefix, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) { Fail "$rel : holds none of the mod's own symbols ('$prefix')"; $origDat = $false }
        foreach ($m in [regex]::Matches($txt, 'Ply([A-Za-z0-9]+)_')) {
          if (-not $m.Groups[1].Value.StartsWith($prefix)) { Fail "$rel : contains another fighter's symbol ($($m.Value)): that is disc-derived"; $origDat = $false; break }
        }
      }
    }
  }
  if (($DiscExt -contains $ext) -and -not $origDat) { Fail "$rel : '$ext' files are disc data (or could hold it) and never ship" }
  # a mod's own files\ folder (the Courier's built models) is not the disc's files\ folder: exempt only when the
  # path is on that mod's allow list, i.e. the mod rules name it on purpose
  $modOwnFiles = $false
  if ($dirs.Count -ge 3 -and $dirs[0] -eq "mods" -and $dirs[2] -eq "files" -and $ModRules.mods.$($dirs[1])) {
    $mr = $ModRules.mods.$($dirs[1])
    $modOwnFiles = ((@($dirs | Select-Object -Skip 2) + $name) -join '/') -cmatch ('^(?:' + (($mr.allow | ForEach-Object { "(?:$_)" }) -join '|') + ')$')
  }
  foreach ($d in $dirs) { if (($DiscDirs -contains $d.ToLowerInvariant()) -and -not ($modOwnFiles -and $d -ceq "files")) { Fail "$rel : inside a '$d' folder, which is where disc data or saves live" } }

  # 1. allowlist
  $ok = $false
  # Qt's 64-bit runtime is isolated from the 32-bit game and its CRT.
  $launcherBinary = $rel -match '^launcher/bin/(gd-melee-launcher\.exe|Qt6(Core|Gui|Widgets|Svg|Network)\.dll|msvcp140(_1|_2|_atomic_wait|_codecvt_ids)?\.dll|vcruntime140(_1)?\.dll|concrt140\.dll|d3dcompiler_47\.dll|opengl32sw\.dll|dxcompiler\.dll|dxil\.dll|vc_redist\.x64\.exe)$' -or
                    $rel -match '^launcher/(plugins|bin)/(platforms/q(windows|offscreen|minimal)\.dll|styles/q(modernwindows|windowsvista)style\.dll|imageformats/q(gif|ico|jpeg|svg)\.dll|generic/qtuiotouchplugin\.dll|networkinformation/qnetworklistmanager\.dll|tls/q(certonlybackend|schannelbackend)\.dll)$'
  if ($dirs.Count -eq 0) {
    $ok = ($AllowedBinaries -contains $name) -or ($AllowedTopFiles -contains $name)
  } elseif ($dirs[0] -eq "ui") {
    $ok = ($dirs.Count -eq 1) -and ($ext -eq ".gxtex" -or $ext -eq ".json")
  } elseif ($dirs[0] -eq "LICENSES") {
    $ok = ($dirs.Count -eq 1) -and ($ext -eq ".txt")
  } elseif ($dirs[0] -eq "launcher") {
    $ok = $launcherBinary -or ($rel -eq 'launcher/bin/qt.conf') -or ($rel -eq 'launcher/qt-build.txt') -or
          ($dirs.Count -eq 2 -and $dirs[1] -eq 'licenses' -and $ext -eq '.txt')
  } elseif ($dirs[0] -eq "mods") {
    if ($dirs.Count -eq 1) { $ok = $ModTopFiles -contains $name }
    else {
      $id = $dirs[1]
      if ($id -match $ModRules.deny_mod_ids) { Fail "$rel : mod '$id' is on the never-package list (private, ported, local or disc-derived)" }
      $modRule = $ModRules.mods.$id
      if (-not $modRule) { Fail "$rel : mod '$id' is not a mod this release carries (tools/release/mod_rules.json)"; $ok = $true }
      else {
        $inMod = (@($dirs | Select-Object -Skip 2) + $name) -join '/'
        $ok = $inMod -cmatch ('^(?:' + (($modRule.allow | ForEach-Object { "(?:$_)" }) -join '|') + ')$')
        if (-not $ok -and $origDat) { $ok = $true }
      }
    }
  } elseif ($dirs[0] -eq "scripts") {
    $ok = ($rel -eq "scripts/README.txt") -or
          ($dirs.Count -ge 2 -and $dirs[1] -eq "examples" -and ($ext -eq ".lua" -or $ext -eq ".json"))
    if ($dirs.Count -ge 3 -and $dirs[1] -eq "examples" -and ($ModRules.examples_skip -contains $dirs[2])) {
      Fail "$rel : '$($dirs[2])' is a mod now (mods/$($dirs[2])), not an example script"; $ok = $true
    }
  }
  foreach ($d in $dirs) { if ($ModRules.deny_dirs_anywhere -contains $d.ToLowerInvariant()) { Fail "$rel : inside a '$d' folder, which is local-only" } }
  if (-not $ok) { Fail "$rel : not on the release allowlist (tools/release/check_release.ps1)" }
  if (($ext -eq ".exe" -or $ext -eq ".dll") -and -not (($dirs.Count -eq 0 -and $AllowedBinaries -contains $name) -or $launcherBinary)) {
    Fail "$rel : unexpected executable"
  }

  # 3. content sniffing
  if ($b.Length -ge 0x20 -and (BE32 $b 0x1C) -eq 3258163005L) { Fail "$rel : contains a GameCube disc header" }
  if ($b.Length -ge 0x20 -and (BE32 $b 0x18) -eq 1562156707L) { Fail "$rel : contains a Wii disc header" }
  $m4 = Ascii $b 0 4
  if ($m4 -eq "RVZ$([char]1)" -or $m4 -eq "WIA$([char]1)" -or $m4 -eq "CISO") { Fail "$rel : is a compressed disc image" }
  if ((Ascii $b 0 4) -match '^G[A-Z]{2}[EPJ]$' -and (Ascii $b 4 2) -match '^[0-9A-Z]{2}$') { Fail "$rel : starts with a game ID ($(Ascii $b 0 6)): a memory-card save or disc header" }
  if (-not $origDat -and $ext -ne ".exe" -and $ext -ne ".dll" -and $b.Length -ge 0x20 -and (BE32 $b 0) -eq $b.Length) { Fail "$rel : looks like an HSD archive (.dat): its first word is its own size" }
  if ($b.Length -ge 0x100 -and $ext -ne ".exe" -and $ext -ne ".dll") {
    # DOL: 7 text + 11 data section offsets, then 18 load addresses in 0x80000000-0x81800000
    $t0 = BE32 $b 0; $a0 = BE32 $b 0x48; $entry = BE32 $b 0xE0
    if ($t0 -eq 0x100 -and $a0 -ge 2147483648L -and $a0 -lt 2172649472L -and $entry -ge 2147483648L -and $entry -lt 2172649472L) { Fail "$rel : looks like a DOL (GameCube executable)" }
  }
  if (@(".exe", ".dll", ".map", ".db", ".lua", ".wgsl", ".json", ".txt", ".md", ".genoasm", ".words", ".dat") -contains $ext) {
    $text = [System.Text.Encoding]::GetEncoding(28591).GetString($b)
    if (($ext -eq ".exe" -or $ext -eq ".dll") -and $text.Contains("GD_MELEE_TRACY_DEVELOPMENT_ONLY")) {
      Fail "$rel : development-only Tracy profiler is enabled; rebuild with GW_PROF_TRACY unset"
    }
    $m = $userPath.Match($text)
    if ($m.Success) { Fail "$rel : contains a personal path ($($m.Value)...)" }
    foreach ($alignment in 0, 1) {
      $length = [int]([Math]::Floor(($b.Length - $alignment) / 2) * 2)
      if ($length -gt 0) {
        $wide = [System.Text.Encoding]::Unicode.GetString($b, $alignment, $length)
        $m = $userPath.Match($wide)
        if ($m.Success) { Fail "$rel : contains a personal path ($($m.Value)...)" }
      }
    }
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
# every default-on mod must be there, and enabled.txt must name only mods that are (never an experimental or off one)
foreach ($prop in $ModRules.mods.PSObject.Properties) {
  if ($prop.Value.default_on -and -not $hashes.ContainsKey("mods/$($prop.Name)/mod.json")) { Fail "missing required file: mods/$($prop.Name)/mod.json" }
  # a mod's own required files (Envoy's shaders, the drive models): a mod without them loads but does not work
  if ($prop.Value.default_on -or $hashes.ContainsKey("mods/$($prop.Name)/mod.json")) {
    foreach ($need in @($prop.Value.required)) {
      if ($need -and -not $hashes.ContainsKey("mods/$($prop.Name)/$need")) { Fail "missing required file: mods/$($prop.Name)/$need" }
    }
  }
}
if (-not $hashes.ContainsKey("mods/enabled.txt")) { Fail "missing required file: mods/enabled.txt" }
else {
  $en = $entries | Where-Object { $_.Rel -eq "mods/enabled.txt" } | Select-Object -First 1
  foreach ($line in ([System.Text.Encoding]::UTF8.GetString($en.Bytes) -split "`r?`n")) {
    $eid = ($line -replace '#.*$', '').Trim()
    if (-not $eid) { continue }
    $er = $ModRules.mods.$eid
    if (-not $er) { Fail "mods/enabled.txt names '$eid', which is not a mod this release carries" }
    elseif (-not $er.default_on) { Fail "mods/enabled.txt turns on '$eid', which must ship off by default" }
    elseif (-not $hashes.ContainsKey("mods/$eid/mod.json")) { Fail "mods/enabled.txt names '$eid', which is not in the package" }
  }
}
if (-not $hashes.ContainsKey('launcher/bin/platforms/qwindows.dll') -and -not $hashes.ContainsKey('launcher/plugins/platforms/qwindows.dll')) {
  Fail "missing required file: launcher/bin/platforms/qwindows.dll (or launcher/plugins/platforms/qwindows.dll)"
}

. (Join-Path $PSScriptRoot 'netplay_protocol.ps1')
$versionEntry = $entries | Where-Object { $_.Rel -eq 'version.txt' } | Select-Object -First 1
if ($versionEntry) {
  try { Assert-NetplayMetadata ([System.Text.Encoding]::ASCII.GetString($versionEntry.Bytes)) }
  catch { Fail $_.Exception.Message }
}

# The build stamp binds the final EXE/map to the source identity checked before packaging.
# Manifest hashes alone prove neither that identity nor that the two artifacts were built together.
$provenanceEntry = $entries | Where-Object { $_.Rel -eq 'build-provenance.json' } | Select-Object -First 1
if ($provenanceEntry) {
  try {
    $stamp = [System.Text.Encoding]::UTF8.GetString($provenanceEntry.Bytes) | ConvertFrom-Json
    if ($stamp.format -isnot [int] -or $stamp.format -ne 1 -or $stamp.melee_commit -notmatch '^[0-9a-f]{40}$' -or
        $stamp.source_sha256 -notmatch '^[0-9a-f]{64}$' -or $stamp.source_dirty -isnot [bool] -or
        $stamp.netplay_protocol -isnot [int] -or $stamp.netplay_protocol -ne (Get-NetplayProtocol)) {
      throw 'malformed build provenance or incompatible protocol'
    }
    foreach ($artifact in 'melee-pc.exe', 'melee-pc.map') {
      $recorded = $stamp.files.$artifact
      if ($recorded -notmatch '^[0-9a-f]{64}$' -or $recorded -ne $hashes[$artifact]) {
        throw "build provenance hash mismatch: $artifact"
      }
    }
    $identities = [regex]::Matches([System.Text.Encoding]::ASCII.GetString($versionEntry.Bytes), '(?m)^melee\s+([0-9a-f]{40})\s+')
    if ($identities.Count -ne 1 -or $identities[0].Groups[1].Value -ne $stamp.melee_commit) {
      throw 'build provenance commit does not match version.txt'
    }
  } catch { Fail "build provenance refused: $($_.Exception.Message)" }
}

# 5. manifest: every file listed once with the right hash, and nothing listed that is absent
$man = $entries | Where-Object { $_.Rel -eq "MANIFEST.sha256" } | Select-Object -First 1
if ($man) {
  $listed = @{}
  foreach ($line in ([System.Text.Encoding]::UTF8.GetString($man.Bytes) -split "`r?`n")) {
    if ($line -match '^([0-9a-f]{64})  (.+)$') {
      if ($listed.ContainsKey($Matches[2])) { Fail "$($Matches[2]) : duplicate MANIFEST.sha256 entry" }
      $listed[$Matches[2]] = $Matches[1]
    } elseif ($line.Trim()) { Fail "malformed MANIFEST.sha256 line" }
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
