# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MZ-WorldClock: kontext projektu

Vzkříšení dema světových hodin „SHARP せかいどけい“ z inzerátů a katalogů Sharp MZ-700 (1982–83). Originál se
nenašel, předlohou jsou dobové fotky ([docs/zdroje.md](docs/zdroje.md)).

- **Jeden MZF** pro MZ-700 EU (PAL, 1Z-013A), MZ-700 JP (NTSC, 1Z-009, japonský CG-ROM), MZ-800 a MZ-1500 (jako
  japonský MZ-700). Stroj se pozná za běhu. MZ-800 podle GDG, ne podle ROM.
- **Historický vzhled** v textovém režimu MZ-700 na všech strojích. **Moderní vzhled** v grafice 320×200 jen na MZ-800.
- **Čas** z Unicard RTC (místní čas), jinak se zadá.
- **Později port na SAPI-1** (CGA-1V).
- **Co nejvíc kódu v C** (z88dk nightly), asm jen tam, kde je to nutné.

Autor: Martin Lukášek. Komunikace **česky**.

## Kde co je

- **Pro práci začni v `docs/vyvoj.md`:** stav, plán fází, nástroje, překlad, testy, pasti.
- `docs/rozhodnuti.md`: rozhodnutí autora a technická rozhodnutí. Nová dopisovat.
- `docs/hw-otazky.md`: otázky k ověření na reálném HW.
- `docs/zdroje.md`: pátrání po originálu, dobové fotky, remaky, odkazy.
- `docs/original.md`: rekonstrukce obrazovky z fotek, rozvržení, jistota. Data jsou v `data/historic.txt`.
- `docs/remake-2019.md`: rozbor japonského remaku v `input/World-Clock/`. Je jen ke studiu, kód nepřebírat.
- **Kód:**
  - `src/core/`: přenositelné C bez HW;
  - `src/mz/`: HAL Sharp, vlastní `crt0.asm` (exec 2000h, load 1200h se studenou částí, DI, SP C000h, BSS A000h);
  - `tools/`: generátory v Pythonu, `mkmzf.py`, `emu/mzemu.py` (ovládání emulátoru přes MCP rouru);
  - `tests/`.
- `input/`: cizí materiály bez licence, jen lokálně (v `.gitignore`).
- **Emulátor:** `..\mz800emu-2.0.5-preview\`, zdrojáky `..\mz800emu` jen ke čtení. Sesterský projekt se stejným stylem
  práce: `..\MZ-700-Bad-Apple`.

## Pravidla

- **Jazyk:** kód, komentáře a skripty **anglicky**, dokumentace **česky**.
- **Necommitovat** obsah `input/`, ROM, CG-ROM ani nic z nich odvozeného (fonty Sharp). Licence projektu je GPL-3.0.
- **Git:** lokální commity průběžně, **push jen na výslovný pokyn**. Veřejné repo:
  https://github.com/mlukasek/MZ-WorldClock (`origin`, větev `main`).
- **Toolchain:**
  - z88dk **nightly** (`E:\SHARP_GIT\Tools\z88dk-nightly`), target `+mz` s naším `src/mz/crt0.asm`;
  - konzoli z88dk (printf, conio) nepoužívat, volá monitor;
  - asm moduly přes z88dk-z80asm, konvence fastcall;
  - pasmo pro tento projekt není potřeba.
- **Python 3:** build a testy jen se standardní knihovnou. Analytické skripty v `tools/ref/` smí používat Pillow,
  numpy a scipy.
- **Měřit, nehádat:**
  - chování ověřovat v emulátoru (`tools/emu/mzemu.py`);
  - jádro v C přes `z88dk-ticks` proti referenci v Pythonu.
- **Emulátor spouštět přes `mzemu.py`** (vlastní ini, `--no-save-ini`). Soubory v jeho složce se smí měnit i mazat,
  když je to potřeba (autor 2026-11-01: nic důležitého tam není, dá se obnovit). Zdrojáky `..\mz800emu` jen ke čtení.
- **Reálný HW má autor.** Otázky k ověření sbírat v `docs/hw-otazky.md`.
- **Každá změna:**
  - `cmd /c build.cmd`;
  - `python tests/emu/run_wc.py`, `--dialog` a `--native-boot` na všech emulovaných strojích;
  - po změně jádra času `python tests/core/run_core.py`;
  - po změně časové základny i `--drift 60`.
