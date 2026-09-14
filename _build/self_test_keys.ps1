param(
  [int]$Presses = 60,
  [int]$IntervalMs = 700,
  [int]$Key = 0x4A   # 'J' = A button in the port's keyboard bridge
)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KeySend {
  [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  public static void Focus(IntPtr h) { if (h != IntPtr.Zero) { ShowWindow(h, 9); SetForegroundWindow(h); } }
  public static void Tap(byte vk) {
    keybd_event(vk, 0, 0, UIntPtr.Zero);
    System.Threading.Thread.Sleep(70);
    keybd_event(vk, 0, 2, UIntPtr.Zero);
  }
}
"@
$p = Get-Process melee-pc -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($null -eq $p) { Write-Output "no melee-pc window"; exit 1 }
[KeySend]::Focus($p.MainWindowHandle)
Start-Sleep -Milliseconds 400
for ($i = 0; $i -lt $Presses; $i++) {
  [KeySend]::Tap([byte]$Key)
  Start-Sleep -Milliseconds $IntervalMs
}
Write-Output "sent $Presses presses"
