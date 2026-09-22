# build_launcher.ps1 - compile the end-user launcher ("GD Melee.exe").
#
#   powershell -File tools\release\build_launcher.ps1 [-Out <path to exe>]
#
# Uses the C# compiler that ships with Windows (.NET Framework 4.x, csc.exe), so there is nothing
# to install on the build machine, and the result runs on any Windows 10/11 with nothing to install
# either (.NET Framework 4.8 is part of the OS). The icon is drawn here, so it is original art.
param(
  [string]$Out = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "_build\release\GD Melee.exe")
)
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "launcher"
$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe" }
if (-not (Test-Path $csc)) { throw "csc.exe (.NET Framework 4.x) not found under $env:WINDIR\Microsoft.NET" }

$outDir = Split-Path $Out -Parent
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$obj = Join-Path $outDir "launcher-obj"
New-Item -ItemType Directory -Force -Path $obj | Out-Null

# --- icon: a red rounded square with a white "GD", at 16/32/48/256 px ---------------------------
Add-Type -AssemblyName System.Drawing
function New-IconPng([int]$size) {
  $bmp = New-Object System.Drawing.Bitmap $size, $size
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = "AntiAlias"; $g.TextRenderingHint = "AntiAliasGridFit"
  $r = [Math]::Max(2, [int]($size * 0.2)); $d = 2 * $r; $s = $size - 1
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $path.AddArc(0, 0, $d, $d, 180, 90); $path.AddArc($s - $d, 0, $d, $d, 270, 90)
  $path.AddArc($s - $d, $s - $d, $d, $d, 0, 90); $path.AddArc(0, $s - $d, $d, $d, 90, 90); $path.CloseFigure()
  $g.FillPath((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(0xC8, 0x2E, 0x3C))), $path)
  $font = New-Object System.Drawing.Font "Segoe UI", ([single]($size * 0.42)), ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
  $fmt = New-Object System.Drawing.StringFormat; $fmt.Alignment = "Center"; $fmt.LineAlignment = "Center"
  $g.DrawString("GD", $font, [System.Drawing.Brushes]::White, (New-Object System.Drawing.RectangleF 0, ([single]($size * 0.02)), $size, $size), $fmt)
  $g.Dispose()
  $ms = New-Object System.IO.MemoryStream
  $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
  return ,$ms.ToArray()
}
$sizes = 16, 32, 48, 256
$pngs = @(); foreach ($z in $sizes) { $pngs += ,(New-IconPng $z) }
$ico = Join-Path $obj "launcher.ico"
$fs = [System.IO.File]::Create($ico); $w = New-Object System.IO.BinaryWriter $fs
$w.Write([uint16]0); $w.Write([uint16]1); $w.Write([uint16]$sizes.Count)
$offset = 6 + 16 * $sizes.Count
for ($i = 0; $i -lt $sizes.Count; $i++) {
  $z = $sizes[$i]; $b = if ($z -ge 256) { 0 } else { $z }
  $w.Write([byte]$b); $w.Write([byte]$b); $w.Write([byte]0); $w.Write([byte]0)
  $w.Write([uint16]1); $w.Write([uint16]32); $w.Write([uint32]$pngs[$i].Length); $w.Write([uint32]$offset)
  $offset += $pngs[$i].Length
}
foreach ($p in $pngs) { $w.Write($p) }
$w.Close()

# --- compile --------------------------------------------------------------------------------------
$cscArgs = @("/nologo", "/target:winexe", "/optimize+", "/platform:anycpu",
          "/out:$Out", "/win32icon:$ico", "/win32manifest:$(Join-Path $src 'app.manifest')",
          "/r:System.dll", "/r:System.Core.dll", "/r:System.Drawing.dll", "/r:System.Windows.Forms.dll",
          "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll", "/r:System.Web.Extensions.dll",
          (Join-Path $src "GDMeleeLauncher.cs"), (Join-Path $src "ModsBrowser.cs"))
& $csc @cscArgs
if ($LASTEXITCODE -ne 0) { throw "csc failed ($LASTEXITCODE)" }
Remove-Item $obj -Recurse -Force
Write-Output "launcher: $Out"
