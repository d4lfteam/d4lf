void InitPipe();

extern "C" __declspec(dllexport) bool SA_SayW(const wchar_t *str);
extern "C" __declspec(dllexport) bool SA_BrlShowTextW(const wchar_t *str);
extern "C" __declspec(dllexport) bool SA_StopAudio();
extern "C" __declspec(dllexport) bool SA_IsRunning();
