# Vývoj

## Stav (2026-11-01)

- **Fáze 0 (založení) hotová:**
  - repo, dokumentace, nástroje pro emulátor;
  - smoke test toolchainu prošel na MZ-700 EU (PAL), MZ-700 JP (NTSC), MZ-700 EU (NTSC) a MZ-800, s oběma překladači.
- **Další krok:** fáze 1, rekonstrukce předlohy podle skenu katalogu.

## Plán vývoje

0. **Založení:** git, GPL-3.0, docs, `tools/emu`, smoke test vlastního crt0 na všech strojích. **Hotovo.**
1. **Rekonstrukce předlohy:**
   - sken katalogu `smz72.JPG` do `input/` (jen lokálně, [zdroje.md](zdroje.md));
   - `data/historic.txt` (mozaika 80×50, texty, atributy);
   - náhled PNG s fontem CG-ROM a porovnání;
   - kódy displeje hiragany v JP CG-ROM;
   - tvar pruhu a pravítka;
   - zapsat do `docs/original.md`.
2. **Bezpečný základ a historický vzhled:**
   - start, konec a detekce na všech strojích, včetně nativního startu MZ-800 a obnovy CG-RAM;
   - timebase, klávesnice;
   - jádro času v C (UTC, letní čas);
   - historická obrazovka;
   - dialog `T` (datum, čas, pásmo).
3. **Unicard RTC:** detekce, čtení, dorovnávání.
4. **MZ-800:**
   - hiragana v CG-RAM;
   - prototyp moderní mapy jako PNG ke schválení;
   - grafika 320×200, mapa z Natural Earth, den a noc, domovské pásmo, přepínání `M`.
5. **Velké digitální a ručičkové hodiny.**
6. **Reálný HW (autor), README se snímky, release MZF.**
7. **Později port na SAPI-1** (CGA-1V, hodiny DPI na B0h/B1h, `zcc +cpm`).

## Nástroje

| Co | Kde |
|---|---|
| z88dk nightly | `E:\SHARP_GIT\Tools\z88dk-nightly` (proměnná `Z88DK`). Verze 2.4 v `E:\SAPI_GIT\Tools-nepouzivat` chybně překládá ternární operátor. |
| Python 3 | jen standardní knihovna |
| Emulátor | `..\mz800emu-2.0.5-preview` (proměnná `MZ800EMU_DIR`). Zdrojáky `..\mz800emu` jen ke čtení. |

Emulované stroje (`tools/emu/mzemu.py`, `Emu(exe, rom=..., unicard=...)`):

| Stroj | exe | ROM |
|---|---|---|
| MZ-700 EU | `mz700emu-pal.exe` | `rom='EU'` (1Z-013A, EU CG-ROM) |
| MZ-700 JP | `mz700emu-ntsc.exe` | `rom='JP'` (1Z-009B, JP CG-ROM) |
| MZ-700 EU NTSC (kontrola měření PAL/NTSC) | `mz700emu-ntsc.exe` | `rom='EU'` |
| MZ-800 | `mz800emu.exe` | po resetu v režimu MZ-700 |

`mzemu.py` píše vlastní ini do `build/emu/<exe>.ini` a emulátor spouští s `--no-save-ini`. Ve složce emulátoru se
nic nemění.

## Překlad a testy

- **Smoke test toolchainu:**
  - překlad: `tests\smoke\build_smoke.cmd [sccz80|sdcc]` vytvoří `build\smoke-<cc>.mzf`;
  - běh: `python tests/smoke/run_smoke.py --cc sccz80|sdcc` na všech čtyřech strojích kontroluje text na obrazovce,
    zásobník a BREAK do monitoru;
  - snímky ukládá do `work/smoke/`.
- **MZF skládá `tools/mkmzf.py`**, ne appmake. Jméno s mezerou a kontrola, že program končí pod 7F00h.

Volby zcc pro MZ:
- `zcc +mz -crt0=src\mz\crt0.asm -pragma-define:CRT_ENABLE_STDIO=0 -pragma-define:CLIB_OPEN_MAX=0 -m`;
- přidat `-compiler=sdcc` pro zsdcc;
- BSS dává crt0 na A000h.

## Pasti

- **z88dk:**
  - Klasické `crt_rules.inc` nepřevádí `CRT_ORG_BSS` na `__crt_org_bss`. Dělá to náš crt0.
  - `-Cz--blockname -Cz"JMÉNO S MEZEROU"` rozdělí jméno, proto MZF skládá `tools/mkmzf.py`.
  - zsdcc hlásí warning 346 u čtení adresy 0000h (`MEM8(0)`), je neškodný.
  - Ze sesterských projektů (`E:\SAPI_GIT\MZPico-firmware\external\manager\CLAUDE.md`, `E:\SAPI_GIT\SAPI-BomberNet\docs\vyvoj.md`):
    - makra C v inline asm se rozvinou i se závorkami, takže `ld de,(X)` je nepřímé čtení;
    - apostrof v komentáři asm potichu vypne rozvinutí maker ve zbytku bloku;
    - u `__smallc __naked` je poslední argument na `(iy+0)`;
    - printf a conio z88dk na MZ volají monitor, nepoužívat je.
  - **Konvence asm pro C:** fastcall (`__z88dk_fastcall`), argument v HL a výsledek v L/HL. Stejné pro sccz80 i zsdcc.
- **Emulátor (2.0.5-preview):**
  - `get_video_text_dump` na `mz800emu` vrací chybná data (vypadá to na font). Text se čte přes `mem_read` z D000h
    a D800h, což je CPU pohled v režimu MZ-700.
  - `run_mzf` spustí program na zásobníku monitoru se zapnutým přerušením, proto je v crt0 první DI.
  - `get_platform_info` hlásí na MZ-800 `mode: native` i v režimu MZ-700, neřídit se tím.
  - Preview neumí start s přepínačem SW1 v režimu MZ-800 (`--mode-switch` je až v HEAD). Nativní start se simuluje
    podstrčeným kódem.
  - Unicard RTC vrací místní čas hostitele a nenásleduje emulovaný čas. Nastavení času (60h/61h) není implementováno.
  - Emulátor jede přesně 50/60 snímků za sekundu (15 600 / 15 720 řádků/s). S počty 15611/15700 jdou hodiny o
    −2,54 s/h (PAL) a +4,59 s/h (NTSC), na reálném HW ne.
  - Klávesy přes `input_press_key`, `run(N)` a `input_release_key`, tj. `Emu.key()`.
- **Hardware** (podrobnosti v [rozhodnuti.md](rozhodnuti.md)):
  - Na MZ-700 nikdy nedělat `IN (E0h)`.
  - V nativním režimu MZ-800 je 8255/8253 na portech D0h–D7h a na E000h jsou registry nedostupné.
  - Do 8255 PA zapisovat `F0h | sloupec`. PA4/PA5 jsou strobe joysticku, PA7=0 nuluje časovač kurzoru.
