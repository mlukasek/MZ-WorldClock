@echo off
rem Build the toolchain smoke test: build\smoke-<compiler>.mzf (load and exec 2000h).
rem   tests\smoke\build_smoke.cmd [sccz80|sdcc]     default sccz80
setlocal
cd /d "%~dp0..\.."
if "%Z88DK%"=="" set Z88DK=E:\SHARP_GIT\Tools\z88dk-nightly
set PATH=%Z88DK%\bin;%PATH%
set ZCCCFG=%Z88DK%\lib\config
set CC=sccz80
if not "%1"=="" set CC=%1
set COMP=
if /i "%CC%"=="sdcc" set COMP=-compiler=sdcc
if not exist build mkdir build
zcc +mz %COMP% -O2 -m -crt0=src\mz\crt0.asm ^
  -pragma-define:CRT_ENABLE_STDIO=0 -pragma-define:CLIB_OPEN_MAX=0 ^
  -o build\smoke-%CC%.bin tests\smoke\smoke.c src\mz\hw.asm || exit /b 1
python tools\mkmzf.py build\smoke-%CC%.bin build\smoke-%CC%.mzf --name "SMOKE TEST" || exit /b 1
for %%f in (build\smoke-%CC%.mzf) do echo %%f: %%~zf bytes
