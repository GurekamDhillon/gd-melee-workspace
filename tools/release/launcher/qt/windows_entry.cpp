// Small static-runtime entry point. Qt and its 64-bit DLLs live in launcher/bin;
// the 32-bit game's CRT stays beside melee-pc.exe and is never overwritten.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <strsafe.h>
int WINAPI wWinMain(HINSTANCE, HINSTANCE, LPWSTR args, int) {
    wchar_t root[32768], exe[32768];
    DWORD n = GetModuleFileNameW(nullptr, root, 32768);
    if (!n || n >= 32768) return 1;
    while (n && root[n - 1] != L'\\') --n;
    root[n] = 0;
    if (FAILED(StringCchPrintfW(exe, 32768, L"%slauncher\\bin\\gd-melee-launcher.exe", root))) return 1;
    auto length = lstrlenW(exe) + lstrlenW(args) + 5;
    auto command = static_cast<wchar_t *>(HeapAlloc(GetProcessHeap(), 0, length * sizeof(wchar_t)));
    if (!command) return 1;
    StringCchPrintfW(command, length, L"\"%s\" %s", exe, args);
    STARTUPINFOW si{}; si.cb = sizeof(si); PROCESS_INFORMATION pi{};
    BOOL ok = CreateProcessW(exe, command, nullptr, nullptr, FALSE, 0, nullptr, nullptr, &si, &pi);
    HeapFree(GetProcessHeap(), 0, command);
    if (!ok) { MessageBoxW(nullptr, L"Cannot start launcher/bin/gd-melee-launcher.exe. Extract the complete release folder.", L"GD's Melee", MB_OK | MB_ICONERROR); return 1; }
    CloseHandle(pi.hThread); WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD result = 1; GetExitCodeProcess(pi.hProcess, &result); CloseHandle(pi.hProcess); return int(result);
}
