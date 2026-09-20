# Set the Windows per-application volume for a process, via the Core Audio session API.
#   powershell -File set_app_volume.ps1 -ProcessName melee-pc -Volume 0.03
# Waits for the process's audio session to appear, since a game creates it a moment after start.
param(
    # PREFER -ProcessId. Matching by NAME picks an arbitrary instance, and the sweep now
    # runs four games at once: every run was setting some OTHER run's volume and leaving
    # its own at full. Name matching is kept only for a single manual launch.
    [int]$ProcessId = 0,
    [string]$ProcessName = 'melee-pc',
    [double]$Volume = 0.03,
    [int]$TimeoutSec = 30
)

Add-Type -Language CSharp @'
using System;
using System.Runtime.InteropServices;

public static class AppVol {
    [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumerator { }

    [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator {
        int NotImpl1();
        int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ep);
    }

    [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice {
        int Activate(ref Guid iid, int ctx, IntPtr p, [MarshalAs(UnmanagedType.IUnknown)] out object o);
    }

    [ComImport, Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioSessionManager2 {
        int NotImpl1(); int NotImpl2();
        int GetSessionEnumerator(out IAudioSessionEnumerator e);
    }

    [ComImport, Guid("E2F5BB11-0570-40CA-ACDD-3AA01277DEE8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioSessionEnumerator {
        int GetCount(out int c);
        int GetSession(int i, out IAudioSessionControl s);
    }

    [ComImport, Guid("F4B1A599-7266-4319-A8CA-E70ACB11E8CD"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioSessionControl { }

    [ComImport, Guid("BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    // Vtable order: the 9 IAudioSessionControl methods, then GetSessionIdentifier and
    // GetSessionInstanceIdentifier, and only then GetProcessId - 11 slots to skip, not 10.
    interface IAudioSessionControl2 {
        int NotImpl0(); int NotImpl1(); int NotImpl2(); int NotImpl3(); int NotImpl4();
        int NotImpl5(); int NotImpl6(); int NotImpl7(); int NotImpl8(); int NotImpl9();
        int NotImpl10();
        int GetProcessId(out int pid);
    }

    [ComImport, Guid("87CE5498-68D6-44E5-9215-6DA47EF883D8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface ISimpleAudioVolume {
        int SetMasterVolume(float level, ref Guid ctx);
        int GetMasterVolume(out float level);
    }

    // Returns the number of sessions whose volume was set.
    public static int Set(int pid, float level) {
        Guid IID_ASM2 = new Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F");
        Guid empty = Guid.Empty;
        int hit = 0;

        var enumerator = (IMMDeviceEnumerator) new MMDeviceEnumerator();
        IMMDevice dev;
        Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0 /*eRender*/, 1 /*eMultimedia*/, out dev));

        object o;
        Marshal.ThrowExceptionForHR(dev.Activate(ref IID_ASM2, 1 /*CLSCTX_INPROC_SERVER*/, IntPtr.Zero, out o));
        var mgr = (IAudioSessionManager2) o;

        IAudioSessionEnumerator sessions;
        Marshal.ThrowExceptionForHR(mgr.GetSessionEnumerator(out sessions));
        int count;
        Marshal.ThrowExceptionForHR(sessions.GetCount(out count));

        for (int i = 0; i < count; i++) {
            IAudioSessionControl ctl;
            if (sessions.GetSession(i, out ctl) != 0 || ctl == null) continue;
            var ctl2 = ctl as IAudioSessionControl2;
            if (ctl2 == null) continue;
            int spid;
            if (ctl2.GetProcessId(out spid) != 0 || spid != pid) continue;
            var vol = ctl as ISimpleAudioVolume;
            if (vol == null) continue;
            if (vol.SetMasterVolume(level, ref empty) == 0) hit++;
        }
        return hit;
    }
}
'@

$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
    $p = if ($ProcessId -gt 0) {
        Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    } else {
        Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if ($p) {
        try {
            $n = [AppVol]::Set($p.Id, [float]$Volume)
            if ($n -gt 0) {
                Write-Output ("VOLUME_SET pid={0} level={1:P0} sessions={2}" -f $p.Id, $Volume, $n)
                exit 0
            }
        } catch {
            Write-Output ("VOLUME_ERR " + $_.Exception.Message)
            exit 1
        }
    }
    Start-Sleep -Milliseconds 500
}
Write-Output ("VOLUME_TIMEOUT no audio session for {0} within {1}s" -f $(if ($ProcessId -gt 0) { "pid $ProcessId" } else { $ProcessName }), $TimeoutSec)
exit 1
