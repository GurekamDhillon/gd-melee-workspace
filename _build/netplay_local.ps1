# netplay_local.ps1 - two copies of the port on this machine, playing one match over loopback UDP
# (gw_netplay.c). HOST is P1, GUEST is P2. Both use keyboard + controllers: the GameCube adapter
# goes to whichever window has focus (released on blur). -HostDevice/-GuestDevice gc|keyboard pin a
# side, as the old default did (host gc, guest keyboard). Each copy runs from its own sandbox (its own exe copy, log, card and pipeline cache).
#
#   powershell -File _build\netplay_local.ps1                       # Fox vs Marth, Battlefield
#   powershell -File _build\netplay_local.ps1 -Scene "mode=vs;p1=falco/hu;p2=sheik/hu;stage=fd"
#
# Keyboard (guest window must be focused): WASD stick (Left Shift = half tilt), arrows C-stick,
# J=A K=B I/Space=X O=Y L=R U=L ;=Z Enter=Start. The GC controller works whichever window has focus.
#
# -Seconds N closes both after N seconds (for scripted tests); -PadHost/-PadGuest drive either side
# from a pad script instead of the device; -Delay sets the input delay (frames).
#
# SIMULATED NETWORK: -NetSim <preset | settings>, applied to both copies' outgoing packets (so the
# round trip is twice the lag). Change it mid-match with:  powershell -File _build\netsim.ps1 bad
# (it rewrites runs\netsim.txt, which both copies re-read every second).
#   presets: off, lan, good, wifi, far, bad, awful   (see netsim.ps1)
#   settings: "lag=60,jitter=15,loss=5,burst=2,dup=1,spike=5000:300"  (ms, ms, %, packets, %, ms:ms)
param(
  [string]$Scene = "mode=vs;at=match;p1=fox/c0/hu;p2=marth/c0/hu;stage=battlefield;time=480",
  [int]$Delay = 2,
  [string]$Disc = "vanilla",
  [int]$Port = 51500,
  [double]$Volume = 0.03,
  [int]$Seconds = 0,
  [string]$PadHost = "",
  [string]$PadGuest = "",
  [string]$NetSim = "off",
  [switch]$Menu,   # boot both to the main menu and connect through ONLINE PLAY instead
  [switch]$RealNetwork,  # no loopback shortcut: real STUN codes, as two copies of the package would
  [int]$HostChar = -1,   # CharacterKind for each side when connecting at boot (m-ex fighters too)
  [int]$GuestChar = -1,
  [string]$Exe = "",     # run this melee-pc.exe (a lane's build) instead of _build's; sandboxes go beside it
  [string]$Server = "",  # MELEE_NETPLAY_SERVER for both (default: netplay_server.txt beside the exe)
  [string]$LiveHost = "", # MELEE_PAD_LIVE file for each side: drive it by writing "<buttons_hex>" into it
  [string]$LiveGuest = "",
  [hashtable]$EnvHost = @{},  # extra environment per side, e.g. @{MELEE_LOBBY_AUTOPLAY="1"}
  [hashtable]$EnvGuest = @{},
  [string]$HostDevice = "",  # MELEE_INPUT per side; "" = the game default (keyboard + controllers, the
  [string]$GuestDevice = "", # adapter follows the focused window); "keyboard" / "gc" pin a side
  [string]$Label = ""    # the windows' run label starts with this, e.g. "alpha / A1" -> "alpha / A1 - HOST P1 ..."
)
$ErrorActionPreference = "Stop"
$build = $PSScriptRoot
$root = Split-Path $build -Parent
$exeDir = if ($Exe) { Split-Path (Resolve-Path $Exe) -Parent } else { $build }

Get-Content (Join-Path $root ".env") -ErrorAction SilentlyContinue | ForEach-Object {
  if ($_ -match '^\s*(?:export\s+)?(GW_ISO_\w+)\s*=\s*"?([^"]*)"?\s*$') {
    Set-Item -Path ("Env:" + $Matches[1]) -Value $Matches[2]
  }
}
$iso = switch ($Disc) {
  "vanilla" { $env:GW_ISO_VANILLA }
  "akaneia" { $env:GW_ISO_AKANEIA }
  "ace"     { $env:GW_ISO_ACE }
  default   { $Disc }
}
if (-not $iso) { Write-Output "FAIL: no ISO for '$Disc' - set it in $root\.env"; exit 1 }

function Sync-RunFile($src, $dstDir) {
  if (-not (Test-Path $src)) { return }
  $s = Get-Item $src
  $d = Join-Path $dstDir $s.Name
  if (Test-Path $d) {
    $t = Get-Item $d
    if ($t.Length -eq $s.Length -and $t.LastWriteTimeUtc -eq $s.LastWriteTimeUtc) { return }
  }
  Copy-Item $src $d -Force
}
function Link-RunFile($src, $dstDir) {
  if (-not (Test-Path $src)) { return }
  $s = Get-Item $src
  $d = Join-Path $dstDir $s.Name
  if (Test-Path $d) {
    $t = Get-Item $d
    if ($t.Length -eq $s.Length -and $t.LastWriteTimeUtc -eq $s.LastWriteTimeUtc) { return }
    Remove-Item $d -Force -ErrorAction SilentlyContinue
  }
  try { New-Item -ItemType HardLink -Path $d -Target $s.FullName -ErrorAction Stop | Out-Null }
  catch { Copy-Item $src $d -Force }
}

# Side by side on the primary screen, each a 4:3 window half the working width.
Add-Type -AssemblyName System.Windows.Forms
$wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$w = [int]($wa.Width / 2)

# The live network-conditions file both copies watch. Start it from -NetSim.
$netsimFile = Join-Path $build "runs\netsim.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $netsimFile) | Out-Null
& (Join-Path $build "netsim.ps1") $NetSim
$h = [int]([Math]::Min($wa.Height, $w * 3 / 4))

function Start-Side($tag, $label, $netplay, $device, $x, $pad, $vol) {
  $sandbox = Join-Path $exeDir "runs\$tag"
  New-Item -ItemType Directory -Force -Path $sandbox | Out-Null
  # By executable path from the process table: Get-Process's MainModule can throw for a process
  # that is starting or exiting, which silently skipped it and left its exe locked.
  # C:\gdm is a junction to the project folder: match the run folder, not the full path.
  Get-CimInstance Win32_Process -Filter "Name = 'melee-pc.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -like ("*" + $sandbox.Substring($root.Length) + "\melee-pc.exe") } | ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
      Wait-Process -Id $_.ProcessId -Timeout 10 -ErrorAction SilentlyContinue   # its exe stays locked until it exits
    }
  foreach ($f in @("melee-pc.exe", "melee-pc.map")) { Sync-RunFile (Join-Path $exeDir $f) $sandbox }
  if ($Server) { $env:MELEE_NETPLAY_SERVER = $Server } else { Remove-Item Env:MELEE_NETPLAY_SERVER -ErrorAction SilentlyContinue }
  $srvFile = Join-Path $build "netplay_server.txt"
  if (-not $Server -and (Test-Path $srvFile)) { Sync-RunFile $srvFile $sandbox }
  foreach ($f in @("SDL3.dll", "webgpu_dawn.dll")) { Link-RunFile (Join-Path $build $f) $sandbox }
  foreach ($f in @("initial_pipeline_cache.db", "initial_pipeline_cache.core")) { Sync-RunFile (Join-Path $build $f) $sandbox }
  Get-ChildItem $sandbox -Filter "*.db*" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notlike "initial_pipeline_cache.db*" } |
    Remove-Item -Force -ErrorAction SilentlyContinue
  Remove-Item (Join-Path $sandbox "melee-pc.log") -ErrorAction SilentlyContinue
  $cardSrc = Join-Path $build $(if ($Disc -eq "ace") { "card-ace" } else { "card" })
  $cardDst = Join-Path $sandbox "card"
  if (-not (Test-Path $cardDst) -and (Test-Path $cardSrc)) { Copy-Item $cardSrc $cardDst -Recurse -Force }

  $env:MELEE_CARD_PATH = $cardDst
  $env:MELEE_MODS_DIR = Join-Path $build "nomods"   # both sides must run the same code
  New-Item -ItemType Directory -Force -Path $env:MELEE_MODS_DIR | Out-Null
  $env:MELEE_SKIP_INTRO = "1"
  $env:MELEE_SCENE = $Scene
  $env:MELEE_NETPLAY = if ($Menu) { "" } else { $netplay }
  if ($Menu) { $env:MELEE_SCENE = "mode=menu" }
  $env:MELEE_NETPLAY_DELAY = "$Delay"
  $c = if ($tag -eq "np_host") { $HostChar } else { $GuestChar }
  if ($c -ge 0) { $env:MELEE_NETPLAY_CHAR = "$c" } else { Remove-Item Env:MELEE_NETPLAY_CHAR -ErrorAction SilentlyContinue }
  if ($RealNetwork) { Remove-Item Env:MELEE_NETPLAY_BIND -ErrorAction SilentlyContinue } else { $env:MELEE_NETPLAY_BIND = "127.0.0.1" }
  if ($device) { $env:MELEE_INPUT = $device } else { Remove-Item Env:MELEE_INPUT -ErrorAction SilentlyContinue }
  $env:MELEE_NET_SIM_FILE = $netsimFile
  $env:MELEE_RUN_LABEL = if ($Label) { "$Label - $label" } else { $label }
  $env:MELEE_WINDOW_X = "$($wa.X + $x)"
  $env:MELEE_WINDOW_Y = "$($wa.Y)"
  $env:MELEE_WINDOW_W = "$w"
  $env:MELEE_WINDOW_H = "$h"
  # the keyboard side must not let SDL grab the GameCube adapter either
  if ($device -eq "keyboard") { $env:SDL_JOYSTICK_HIDAPI_GAMECUBE = "0" } else { Remove-Item Env:SDL_JOYSTICK_HIDAPI_GAMECUBE -ErrorAction SilentlyContinue }
  if ($pad) { $env:MELEE_PAD_SCRIPT = $pad } else { Remove-Item Env:MELEE_PAD_SCRIPT -ErrorAction SilentlyContinue }
  $live = if ($tag -eq "np_host") { $LiveHost } else { $LiveGuest }
  if ($live) { Set-Content -Path $live -Value "0000"; $env:MELEE_PAD_LIVE = $live } else { Remove-Item Env:MELEE_PAD_LIVE -ErrorAction SilentlyContinue }
  foreach ($v in @("MELEE_LOBBY_AUTOPLAY")) { Remove-Item "Env:$v" -ErrorAction SilentlyContinue }
  $extra = if ($tag -eq "np_host") { $EnvHost } else { $EnvGuest }
  foreach ($k in $extra.Keys) { Set-Item -Path ("Env:" + $k) -Value $extra[$k] }
  foreach ($v in @("MELEE_SLP", "MELEE_RB_FAKE", "MELEE_SYNCTEST", "MELEE_STATE_TRACE", "MELEE_WINDOW_HIDE")) {
    Remove-Item "Env:$v" -ErrorAction SilentlyContinue
  }
  $p = Start-Process -FilePath (Join-Path $sandbox "melee-pc.exe") `
        -ArgumentList '--iso', ('"' + $iso + '"') -WorkingDirectory $sandbox -PassThru
  try {
    & (Join-Path $build "set_app_volume.ps1") -ProcessId $p.Id -Volume $vol -TimeoutSec 20 | Out-Null
  } catch { Write-Output "note: could not set volume ($_)" }
  Write-Output "$label  pid $($p.Id)  log $(Join-Path $sandbox 'melee-pc.log')"
  return $p
}

# The host first: it claims the GameCube adapter and listens. The guest plays silently - both
# windows play the same sounds, and two copies a frame or two apart sound like an echo.
$hostP = Start-Side "np_host" "HOST P1" "host:$Port" $HostDevice 0 $PadHost $Volume
Start-Sleep -Seconds 3
$guestP = Start-Side "np_guest" "GUEST P2" "join:127.0.0.1:$Port" $GuestDevice $w $PadGuest 0.0

if ($Seconds -gt 0) {
  Start-Sleep -Seconds $Seconds
  foreach ($p in @($hostP, $guestP)) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  Write-Output "closed after $Seconds s"
}
