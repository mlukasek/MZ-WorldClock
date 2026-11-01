# Vývoj

## Stav (2026-11-01)

- **Fáze 0 (založení) hotová:**
  - repo, dokumentace, nástroje pro emulátor;
  - smoke test toolchainu prošel na MZ-700 EU (PAL), MZ-700 JP (NTSC), MZ-700 EU (NTSC) a MZ-800, s oběma překladači.
- **Fáze 1 (předloha) hotová:**
  - `data/historic.txt` zrekonstruovaný z katalogu 3/1983 ([original.md](original.md));
  - generátor `tools/mkhistoric.py` (C tabulky a náhled PNG).
- **Fáze 2 (základ a historický vzhled) hotová:**
  - `build.cmd` vytvoří `build/worldclock.mzf`, jeden program pro MZ-700 EU, MZ-700 JP a MZ-800;
  - testy v emulátoru procházejí na všech strojích, včetně nativního startu MZ-800 a hodinového běhu.
- **Fáze 3 (Unicard RTC) hotová:** čas z karty při startu, dorovnání každých 10 minut, zápis do karty z dialogu.
- **Fáze 4 (MZ-800) hotová:**
  - vlastní znaky v CG-RAM (hiragana titulku, pruh po 1 s), na MZ-1500 pruh po 1 s přes PCG;
  - moderní vzhled 320×200 (klávesa G): mapa s dnem a nocí, domovské pásmo, 9 měst, domovský čas, pruh sekund;
  - klávesa M prohodí kontinenty v obou vzhledech.
- **Další krok:** fáze 5, velké digitální a ručičkové hodiny. **Místo dochází:** program končí na 7DE4h, pod 8000h
  zbývá 540 B ([rozhodnuti.md](rozhodnuti.md), paměť).

## Plán vývoje

0. **Založení:** git, GPL-3.0, docs, `tools/emu`, smoke test vlastního crt0 na všech strojích. **Hotovo.**
   Repo: https://github.com/mlukasek/MZ-WorldClock.
1. **Rekonstrukce předlohy** (`data/historic.txt`, [original.md](original.md)). **Hotovo.**
2. **Bezpečný základ a historický vzhled.** **Hotovo.** Obnova CG-RAM při konci přijde ve fázi 4, až ji program
   bude měnit.
3. **Unicard RTC:** detekce, čtení, dorovnávání. **Hotovo.**
4. **MZ-800:**
   - hiragana v CG-RAM;
   - prototyp moderní mapy jako PNG ke schválení;
   - grafika 320×200, mapa z Natural Earth, den a noc, domovské pásmo, přepínání `G`. **Hotovo.**
5. **Velké digitální a ručičkové hodiny.**
6. **Reálný HW (autor), README se snímky, release MZF.**
7. **Později port na SAPI-1** (CGA-1V, hodiny DPI na B0h/B1h, `zcc +cpm`).

## Nástroje

| Co | Kde |
|---|---|
| z88dk nightly | `E:\SHARP_GIT\Tools\z88dk-nightly` (proměnná `Z88DK`). Verze 2.4 v `E:\SAPI_GIT\Tools-nepouzivat` chybně překládá ternární operátor. |
| Python 3 | build a testy jen se standardní knihovnou. Analytické skripty v `tools/ref/` navíc používají Pillow, numpy a scipy (`python -m pip install --user pillow numpy scipy`). |
| Emulátor | `..\mz800emu-2.0.5-preview` (proměnná `MZ800EMU_DIR`). Zdrojáky `..\mz800emu` jen ke čtení. |

Emulované stroje (`tools/emu/mzemu.py`, `Emu(exe, rom=..., unicard=...)`):

| Stroj | exe | ROM |
|---|---|---|
| MZ-700 EU | `mz700emu-pal.exe` | `rom='EU'` (1Z-013A, EU CG-ROM) |
| MZ-700 JP | `mz700emu-ntsc.exe` | `rom='JP'` (1Z-009B, JP CG-ROM) |
| MZ-700 EU NTSC (kontrola měření PAL/NTSC) | `mz700emu-ntsc.exe` | `rom='EU'` |
| MZ-800 | `mz800emu.exe` | po resetu v režimu MZ-700 |
| MZ-1500 | `mz1500emu.exe` | japonský monitor (hlavička 1Z-009B), NTSC |

`mzemu.py` píše vlastní ini do `build/emu/<exe>.ini` a emulátor spouští s `--no-save-ini`. Ve složce emulátoru se
nic nemění.

## Program

| Soubor | Co dělá |
|---|---|
| `src/mz/crt0.asm` | start na 2000h: `JP start`, testovací blok na 2003h, DI, SP C000h, BSS A000h |
| `src/mz/machine.c` | detekce (signatura ROM, GDG přes port CEh, počet řádků), přepnutí MZ-800 do režimu MZ-700, konec do monitoru s nastavenými hodinami (TIMST) |
| `src/mz/timebase.c` | CTC1 1 Hz z HSYNC, CTC2 čítač sekund, `clock_set` / `clock_now`, čekání na VBLK |
| `src/mz/kbd.c` | matice klávesnice přes 8255 |
| `src/mz/text700.c` | textová obrazovka, ASCII → kód displeje |
| `src/mz/histview.c` | historická obrazovka: hodiny měst (po minutě postupně, jedno město za snímek), dvojtečky, pruh |
| `src/mz/cgram.c`, `pcg1500.c` | vlastní znaky: CG-RAM MZ-800, PCG MZ-1500 |
| `src/mz/gfx800.c` | grafika MZ-800: zapnutí a vypnutí 320×200, mapování VRAM, text z CG-ROM se stínem, bod |
| `src/mz/modview.c` | moderní vzhled: mapa po řádcích, den a noc, okraj domovského pásma, města, domovský čas, pruh |
| `src/mz/hw.asm` | porty, 8255/8253 v obou režimech (`io_rd`, `io_wr`), řádek mapy do VRAM (`row_out`), dekódování pevniny (`land_decode`), volání monitoru |
| `src/mz/rtc_unicard.c` | Unicard: REVD, čtení a zápis RTC (porty 50h/51h) |
| `src/mz/rtcsync.c` | čas z karty: start na hraně sekundy, dorovnání každých 10 minut, zápis z dialogu |
| `src/mz/setup.c` | dialog datum / čas / domovské pásmo (klávesa `T`, bez času hned po startu) |
| `src/core/wctime.c`, `zones.c` | přenositelné jádro času a seznam pásem |
| `build/gen/historic.c` | generovaná data obrazovky (`tools/mkhistoric.py`) |
| `build/gen/glyphs.c`, `modern.c` | vlastní znaky (`tools/mkglyphs.py`), data moderního vzhledu (`tools/mkmodern.py`) |

**Testovací blok na 2003h** (`struct test_hook`, `src/mz/machine.h`):
- `"WCTH"`, příznaky (bit 0 = čas platí, bez dialogu), UTC (4 bajty), rezerva;
- testy ho zapisují přes `mem_write` po nahrání a před startem;
- program navíc ukládá poslední přečtený čas do `tb_last_utc` / `tb_last_frac`, testy je čtou podle `build/worldclock.map`.

## Data a generátory

- **`data/historic.txt`** popisuje historickou obrazovku: mapu 80×50 bloků, texty, titulky EU a JP, pruh a hodiny
  s pásmy.
  - `python tools/mkhistoric.py data/historic.txt build/gen` vytvoří `historic.c` a `.h`.
  - `python tools/mkhistoric.py data/historic.txt --png work/historic` vytvoří náhledy s fontem CG-ROM.
- **`tools/cgrom.py`** načítá CG-ROM ze zdrojů emulátoru, jen lokálně, do repa se nedávají. Vykresluje tabulky znaků
  a obrazovky do PNG.
- **Rekonstrukce předlohy** (`tools/ref/`): `align_catalog.py` zarovná fotku katalogu, `extract_map.py` z ní přečte
  mapu. Postup je v [original.md](original.md).
- **`data/glyphs.txt`**: vlastní znaky 8×8, `tools/mkglyphs.py` z nich dělá `glyphs.c`.
- **`data/world_land.txt`, `world_zones.txt`**: pevnina 320×160 a pásma 160×80 jako text, z Natural Earth (public
  domain).
  - `python tools/mkmodern.py build/gen` z nich a z `CITIES` vytvoří `modern.c` a `.h` (RLE, tabulky Slunce, města,
    místa popisků).
  - `python tools/mkmodern.py --from-naturalearth` je přegeneruje ze shapefilů v `input/naturalearth/`
    (`tools/worldmap.py`).
  - `python tools/mkmodern.py --png work/modern --utc ...` vykreslí referenční obrazovky.
- **`tools/modref.py`** je referenční renderer moderního vzhledu se stejnou celočíselnou aritmetikou jako
  `modview.c`.

## Překlad a testy

- **Program:** `build.cmd` (zsdcc) nebo `build.cmd sccz80` vytvoří `build/worldclock.mzf`.
  - Spouštět z `cmd` / PowerShellu (`cmd /c build.cmd`); z Git Bashe se .cmd nespustí.
- **Emulátor:** `python tests/emu/run_wc.py [--machine eu|jp|eu-ntsc|mz800|mz1500]` na všech strojích kontroluje:
  - detekci (model, JP, NTSC, řádky, dělitel);
  - titulek a časy 9 měst proti `zoneinfo`;
  - pruh sekund;
  - návrat do monitoru po BREAK.
- **Další varianty běhu:**
  - `--dialog`: čas se zadá klávesami do dialogu;
  - `--native-boot`: MZ-800 nastartovaný v režimu MZ-800. Simuluje se kódem na 1200h, preview to neumí.
  - `--rtc`: s připojenou Unicard. Program musí vzít čas z karty, emulovaná karta vrací místní čas hostitele.
    Evropské stroje ho čtou jako pražský, japonský jako tokijský.
  - `--drift 60`: hodina emulovaného času, porovnání hodin s emulátorem. Na PAL vychází −2,54 s/h, na NTSC
    +4,59 s/h. Emulátor jede přesně 50/60 Hz, program dělí reálnými 15611/15700. Trvá asi 3,5 min.
- **Moderní vzhled:** `python tests/emu/run_modern.py [--utc ...]` na MZ-800 porovná roviny I a II VRAM bajt po
  bajtu s `tools/modref.py`:
  - po G, po M (atlantický pohled), po změně minuty, po návratu M;
  - pak G zpět (historická obrazovka a vlastní znaky v CG-RAM) a BREAK (CG-RAM obnovená z CG-ROM).

- **Jádro času:** `python tests/core/run_core.py [--cc sdcc|sccz80]`.
  - Přeloží `tests/core/test_wctime.c` pro `+test` a spustí ho v `z88dk-ticks`.
  - Výsledky porovná se `zoneinfo`; na Windows je potřeba `python -m pip install --user tzdata`.

- **Smoke test toolchainu:**
  - překlad: `tests\smoke\build_smoke.cmd [sccz80|sdcc]` vytvoří `build\smoke-<cc>.mzf`;
  - běh: `python tests/smoke/run_smoke.py --cc sccz80|sdcc` na všech čtyřech strojích kontroluje text na obrazovce,
    zásobník a BREAK do monitoru;
  - snímky ukládá do `work/smoke/`.
- **MZF skládá `tools/mkmzf.py`**, ne appmake. Jméno s mezerou a kontrola, že program končí pod 8000h.

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
  - **zsdcc `-SO3 --opt-code-size` přeložil v `render()` výraz `v = x >> 3` (x 16bitové) chybně**: smyčka posunu
    `srl a; rra` dávala nesmysl (pro x = 28 vyšlo 160). Okraj pásma se pak kreslil na špatná místa. Obejito vlastní
    funkcí `border_dots()`, která porovnává v pixelech. Při podivném chování v C podezírat i překladač a podívat se
    do `build/*.asm` (`zcc ... -S` nebo `--list`).
  - **Inicializovaná statická data se při novém spuštění bez nahrání (J 2000) neobnoví**, BSS se vynuluje. Klíče
    cache proto patří do BSS s 0 = prázdné (`half_yday`, `border_home` v `modview.c`).
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
  - **Breakpointy si emulátor sám ukládá** do `<arch>-breakpoints.bpt` ve své složce (`auto_save`) a při dalším
    startu je načte (`auto_load`). Zapomenutý breakpoint pak zastaví každý další běh a test vypadá jako zaseknutý.
    `mzemu.py` proto v ini vypíná `auto_load` i `auto_save` a soubor přesměruje do `build/emu/`.
  - Profilovat jde vzorkováním PC: `run` po jednom snímku a `get_registers`, PC přiřadit funkci podle
    `build/worldclock.map`.
- **Hardware** (podrobnosti v [rozhodnuti.md](rozhodnuti.md)):
  - Na MZ-800 mapuje `IN (E0h)` v režimu 320×200 VRAM na 8000h–9FFFh a CG-ROM na 1000h–1FFFh současně. Kód, který
    běží s namapovanou VRAM, ani jeho data nesmí ležet v 1000h–1FFFh ani 8000h–9FFFh.
  - Na MZ-700 nikdy nedělat `IN (E0h)`.
  - V nativním režimu MZ-800 je 8255/8253 na portech D0h–D7h a na E000h jsou registry nedostupné.
  - Do 8255 PA zapisovat `F0h | sloupec`. PA4/PA5 jsou strobe joysticku, PA7=0 nuluje časovač kurzoru.
