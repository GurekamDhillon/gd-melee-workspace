Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Fg {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
}
"@

$proc = Get-Process melee-pc -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $proc) { Write-Output "no melee-pc running"; exit 1 }

$h = $proc.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { Write-Output "no main window"; exit 1 }

[Fg]::ShowWindow($h, 9) | Out-Null
$pidOut = 0
$target = [Fg]::GetWindowThreadProcessId($h, [ref]$pidOut)
$cur = [Fg]::GetCurrentThreadId()
[Fg]::AttachThreadInput($cur, $target, $true) | Out-Null
[Fg]::SetForegroundWindow($h) | Out-Null
[Fg]::AttachThreadInput($cur, $target, $false) | Out-Null
Start-Sleep -Milliseconds 400

[Fg]::keybd_event(0x0D, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 90
[Fg]::keybd_event(0x0D, 0, 2, [UIntPtr]::Zero)

Write-Output "focused pid=$($proc.Id) and pressed Enter (Start)"
