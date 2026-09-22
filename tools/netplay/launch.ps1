# launch.ps1 - start GD's Melee from the online package. Asks for your Melee ISO the first time
# and remembers it (iso.txt next to this file).
param([switch]$Keyboard)
$here = $PSScriptRoot
$isoFile = Join-Path $here "iso.txt"
$iso = if (Test-Path $isoFile) { (Get-Content $isoFile -Raw).Trim() } else { "" }
if (-not $iso -or -not (Test-Path $iso)) {
  $found = Get-ChildItem $here -Filter *.iso -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($found) {
    $iso = $found.FullName
  } else {
    Add-Type -AssemblyName System.Windows.Forms
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Title = "Pick your Super Smash Bros. Melee disc image (NTSC 1.02 .iso)"
    $dlg.Filter = "Disc images (*.iso;*.gcm)|*.iso;*.gcm|All files (*.*)|*.*"
    if ($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 1 }
    $iso = $dlg.FileName
  }
  Set-Content -Path $isoFile -Value $iso -Encoding ascii
}
$env:MELEE_CARD_PATH = Join-Path $here "card"
$env:MELEE_MODS_DIR = Join-Path $here "nomods"   # both players must run the same game
$env:MELEE_SKIP_INTRO = "1"
if ($Keyboard) { $env:MELEE_INPUT = "keyboard" } else { Remove-Item Env:MELEE_INPUT -ErrorAction SilentlyContinue }
Start-Process -FilePath (Join-Path $here "melee-pc.exe") -ArgumentList '--iso', ('"' + $iso + '"') -WorkingDirectory $here
