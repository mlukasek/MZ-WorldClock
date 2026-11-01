@echo off
rem Build of MZ-WorldClock for the Sharp MZ-700 (EU, JP) and MZ-800 (docs\vyvoj.md):
rem   build.cmd            build\worldclock.mzf (load and exec 2000h) with zsdcc
rem   build.cmd sccz80     the same with sccz80
rem Needs z88dk nightly (Z88DK, default E:\SHARP_GIT\Tools\z88dk-nightly) and Python 3.
setlocal
cd /d "%~dp0"
if "%Z88DK%"=="" set Z88DK=E:\SHARP_GIT\Tools\z88dk-nightly
set PATH=%Z88DK%\bin;%PATH%
set ZCCCFG=%Z88DK%\lib\config
set COMP=-compiler=sdcc
if /i "%1"=="sccz80" set COMP=
if not exist build\gen mkdir build\gen

python tools\mkhistoric.py data\historic.txt build\gen || exit /b 1
python tools\mkglyphs.py data\glyphs.txt build\gen || exit /b 1

zcc +mz %COMP% -O2 -m -crt0=src\mz\crt0.asm ^
  -pragma-define:CRT_ENABLE_STDIO=0 -pragma-define:CLIB_OPEN_MAX=0 ^
  -Isrc\core -Isrc\mz -Ibuild\gen -o build\worldclock.bin ^
  src\mz\main.c src\mz\machine.c src\mz\timebase.c src\mz\kbd.c src\mz\text700.c src\mz\histview.c ^
  src\mz\setup.c src\mz\rtc_unicard.c src\mz\rtcsync.c src\mz\cgram.c src\mz\pcg1500.c ^
  src\core\wctime.c src\core\zones.c build\gen\historic.c build\gen\glyphs.c src\mz\hw.asm || exit /b 1

python tools\mkmzf.py build\worldclock.bin build\worldclock.mzf --name "WORLD CLOCK" || exit /b 1
for %%f in (build\worldclock.mzf) do echo build\worldclock.mzf: %%~zf bytes
