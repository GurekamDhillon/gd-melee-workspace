param(
  [string]$Iso = "C:\gdm\_build\melee_mod.iso",
  [string]$TT = "fox",
  [int[]]$TimestampsSec = @(8,12,16,20,24,28,33,38,45),
  [string]$OutDir = "C:\gdm\_build\stage_capture",
  [string]$OutLog = "C:\gdm\_build\stage_run.out.log",
  [string]$ErrLog = "C:\gdm\_build\stage_run.err.log"
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Cap {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdcBlt, uint nFlags);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Get-ChildItem $OutDir -Filter *.png -ErrorAction SilentlyContinue | Remove-Item -Force

$env:MELEE_WINDOW_X = "30000"
$env:MELEE_WINDOW_Y = "30000"
Remove-Item Env:MELEE_WINDOW_HIDE -ErrorAction SilentlyContinue
Remove-Item Env:MELEE_PAD_SCRIPT -ErrorAction SilentlyContinue
Remove-Item Env:MELEE_AUDIO_DUMP -ErrorAction SilentlyContinue
Remove-Item Env:MELEE_FORCE_INTRO -ErrorAction SilentlyContinue
if ($TT -ne "") { $env:MELEE_TARGET_TEST = $TT } else { Remove-Item Env:MELEE_TARGET_TEST -ErrorAction SilentlyContinue }

Remove-Item $OutLog -ErrorAction SilentlyContinue
Remove-Item $ErrLog -ErrorAction SilentlyContinue

$p = Start-Process -FilePath "C:\gdm\_build\melee-pc.exe" `
    -ArgumentList '--iso',"`"$Iso`"" `
    -WorkingDirectory "C:\gdm\_build" -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog

Write-Output "LAUNCHED pid=$($p.Id) iso=$Iso MELEE_TARGET_TEST=$TT"

$t0 = Get-Date
$hwnd = [IntPtr]::Zero
foreach ($t in $TimestampsSec) {
    $target = $t0.AddSeconds($t)
    $now = Get-Date
    if ($target -gt $now) { Start-Sleep -Milliseconds ([int](($target - $now).TotalMilliseconds)) }
    if ($p.HasExited) { Write-Output "process exited before t=${t}s"; break }
    if ($hwnd -eq [IntPtr]::Zero) {
        $p.Refresh()
        $hwnd = $p.MainWindowHandle
    }
    if ($hwnd -eq [IntPtr]::Zero) { Write-Output "t=${t}s: no window handle yet"; continue }
    $rect = New-Object Cap+RECT
    [Cap]::GetClientRect($hwnd, [ref]$rect) | Out-Null
    $w = $rect.Right - $rect.Left
    $h = $rect.Bottom - $rect.Top
    if ($w -le 0 -or $h -le 0) { Write-Output "t=${t}s: zero-size client rect"; continue }
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    $ok = [Cap]::PrintWindow($hwnd, $hdc, 2)
    $g.ReleaseHdc($hdc)
    $g.Dispose()
    $path = Join-Path $OutDir ("t{0:D2}.png" -f $t)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output "t=${t}s: captured ($w x $h, ok=$ok)"
}

if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; Write-Output "STOPPED" }
Write-Output "done"
