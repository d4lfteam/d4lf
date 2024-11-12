#include "saapi.h"

#include <tchar.h>

#include <sstream>
#include <string>
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

HANDLE hPipe;

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
        case DLL_PROCESS_ATTACH:
            InitPipe();
            SA_SayW(L"CONNECTED");
            break;

        case DLL_PROCESS_DETACH:
            SA_SayW(L"DISCONNECTED");
            break;

        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
            break;
    }
    return TRUE;
}

void InitPipe() { hPipe = CreateFile(_T("\\\\.\\pipe\\d4lf"), GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL); }

extern "C" bool SA_SayW(const wchar_t *str) {
    if (!str) return false;

    std::string narrowStr;
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, str, -1, nullptr, 0, nullptr, nullptr);
    narrowStr.resize(size_needed);
    WideCharToMultiByte(CP_UTF8, 0, str, -1, &narrowStr[0], size_needed, nullptr, nullptr);

    DWORD bytesWritten = 0;
    BOOL flg = WriteFile(hPipe, narrowStr.c_str(), static_cast<DWORD>(narrowStr.length()), &bytesWritten, NULL);
    if (!flg) InitPipe();
    return true;
}

extern "C" bool SA_BrlShowTextW(const wchar_t *str) { return true; }

extern "C" bool SA_IsRunning() { return true; }

extern "C" bool SA_StopAudio() { return true; }
