# Local build notes (dev branch)

Fixes and gotchas for building with `build.bat` on a local MSYS2 MinGW64 toolchain.
These live on `dev` only; keep them out of fix branches sent upstream.

## Workflow
- Build and test on `dev`. Commit fixes on `master` (or a fix branch) without
  the build changes below, then rebase or merge `dev` onto it to pick them up.
- `build.bat` applies `patches/fsr_vulkan_mingw.patch` to `gpu/third_party/fsr-vulkan`,
  so that submodule always shows as modified after a build. Don't commit it.
- Build output is long; log it with `cmd /c build.bat *> out\build_log.txt`.

## Fixes in `gpu/CMakeLists.txt`
| Symptom | Cause | Fix |
|---|---|---|
| `implicit declaration of function 'SetProcessInformation'` in `src/runtime_thread.c` | MSYS2 MinGW defaults `_WIN32_WINNT` to `0x601` (Windows 7), hiding Win8+ APIs. CI passes `-D_WIN32_WINNT=0x0A00`; `build.bat` doesn't. | Define `_WIN32_WINNT=0x0A00` unless `CMAKE_C_FLAGS` already sets it. |
| `bbport.exe` link fails: `pre_import_hook`, `runtime_thread_get_tcb`, ... `defined in discarded section` | LTO is on (`BB_LTO`) and applies to `bbport`. `src/probe.c` calls these from top-level asm, which LTO can't see, so it drops them. | Compile `src/probe.c` with `-fno-lto`. |

## Harmless warnings
- `-Wodr` warnings for `FfxShaderModel` / `FfxGpuJobDescription` between the FSR 3 and FSR 4 headers.
- `WIN32_LEAN_AND_MEAN` / `VK_USE_PLATFORM_WIN32_KHR` redefined.
- CMake policy `CMP0218` warning from `third_party/sirit`.
