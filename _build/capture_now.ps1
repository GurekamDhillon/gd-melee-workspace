param(
  [int[]]$TimestampsSec = @(0,6,12,20),
  [string]$OutDir = "C:\gdm\_build\stage_capture"
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Cap2 {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdcBlt, uint nFlags);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

$proc = Get-Process melee-pc -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $proc) { Write-Output "no melee-pc running"; exit 1 }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$t0 = Get-Date
foreach ($t in $TimestampsSec) {
    $target = $t0.AddSeconds($t)
    $now = Get-Date
    if ($target -gt $now) { Start-Sleep -Milliseconds ([int](($target - $now).TotalMilliseconds)) }
    $proc.Refresh()
    if ($proc.HasExited) { Write-Output "process exited"; break }
    $hwnd = $proc.MainWindowHandle
    if ($hwnd -eq [IntPtr]::Zero) { Write-Output "t=${t}s: no window"; continue }
    $rect = New-Object Cap2+RECT
    [Cap2]::GetClientRect($hwnd, [ref]$rect) | Out-Null
    $w = $rect.Right - $rect.Left
    $h = $rect.Bottom - $rect.Top
    if ($w -le 0 -or $h -le 0) { Write-Output "t=${t}s: zero rect"; continue }
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    $ok = [Cap2]::PrintWindow($hwnd, $hdc, 2)
    $g.ReleaseHdc($hdc); $g.Dispose()
    $path = Join-Path $OutDir ("now{0:D2}.png" -f $t)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output "t=${t}s: captured ($w x $h, ok=$ok)"
}
Write-Output "done"
