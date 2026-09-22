param(
  [string]$Iso = "C:\gdm\_build\melee_mod.iso",
  [string]$TT = "fox"
)

Remove-Item Env:MELEE_WINDOW_X -ErrorAction SilentlyContinue
Remove-Item Env:MELEE_WINDOW_Y -ErrorAction SilentlyContinue
Remove-Item Env:MELEE_WINDOW_HIDE -ErrorAction SilentlyContinue
Remove-Item Env:MELEE_PAD_SCRIPT -ErrorAction SilentlyContinue
Remove-Item Env:MELEE_AUDIO_DUMP -ErrorAction SilentlyContinue

if ($TT -ne "") { $env:MELEE_TARGET_TEST = $TT } else { Remove-Item Env:MELEE_TARGET_TEST -ErrorAction SilentlyContinue }

$p = Start-Process -FilePath "C:\gdm\_build\melee-pc.exe" `
    -ArgumentList '--iso',"`"$Iso`"" `
    -WorkingDirectory "C:\gdm\_build" -PassThru

Write-Output "LAUNCHED pid=$($p.Id) on the primary monitor, iso=$Iso, MELEE_TARGET_TEST=$TT"
