# Rozhodnutí

Nová rozhodnutí dopisovat na konec, s datem a důvodem.

## 2026-11-01: zadání (autor)

- **Předloha:** dobová fotka z inzerátu a katalogu, ne remaky.
- **Historický vzhled ukazuje dnešní skutečné časy** (UTC posuny včetně letního času). Vzhled je dobový. Inzerát
  ukazuje standardní časy.
- **Titulek:**
  - EU MZ-700: `*** S H A R P   W O R L D  C L O C K ***` (EU CG-ROM nemá hiraganu; katalog MZ-1200 měl
    „WORLD CLOCK“);
  - JP MZ-700: hiragana `せかいどけい` z CG-ROM;
  - MZ-800: hiragana z vlastních znaků v CG-RAM.
- **Jeden MZF pro MZ-700 EU, MZ-700 JP i MZ-800**, stroj se pozná za běhu.
- **Moderní vzhled na MZ-800:** den a noc, domovské město a pásmo, velké digitální hodiny, ručičkové hodiny.
  Přepínání klávesou.
- **Unicard RTC drží místní čas.** Výchozí pásmo RTC je Praha (SEČ/SELČ, EU), v nastavení jde změnit. Bez RTC se
  program zeptá na datum, čas a pásmo.
- **Pruh sekund:** plný za 60 s, bez rasterových triků. Původně krok 1 s po půlkách buňky, upřesněno níže
  (předloha): MZ-700 krok 2 s.
- **Jazyk:** co nejvíc v C (z88dk nightly). Kód a komentáře anglicky, dokumentace česky.
- **Licence GPL-3.0**, veřejné repo `mlukasek/MZ-WorldClock`. Push jen na pokyn autora.

## 2026-11-01: paměť a start

- **Load a exec 2000h, kód a data v 2000h–7FFFh.**
  - Na MZ-800 mapuje `IN (E0h)` spolu s VRAM i CG-ROM na 1000h–1FFFh.
  - V režimu MZ-700 mapuje CG-RAM na C000h–CFFFh.
- **Zásobník pod 8000h.** Monitor má zásobník na 10F0h, tj. v okně CG-ROM.
- **BSS na A000h**, nuluje se při startu a není v MZF. A000h–BFFFh je RAM v každém používaném režimu.
- **Vlastní crt0** (`src/mz/crt0.asm`, odvozený od z88dk `mz_crt0`):
  - první instrukce je DI;
  - žádná konzole z88dk, protože volá monitor;
  - konec obnoví SP monitoru a skočí na 00ADh (stejné v 1Z-013A, 1Z-013B a 1Z-009B). Stroj uvede do pořádku program
    před návratem z `main()`.
- **Detekce stroje** po `OUT (E4h)`, který sjednotí mapu na všech strojích:

  | Stroj | Rozpoznání |
  |---|---|
  | MZ-800 | 0000h = `C3 00 E8` (1Z-013B skáče do IPL) |
  | JP | banner na 06F3h začíná „1Z-009“ |
  | EU | jinak |

  Ověřeno ze ROM v emulátoru. Na reálném stroji ještě ne.
- **Bez přerušení.** Čas se počítá v CTC1 (1 Hz z HSYNC) a CTC2 (čítač sekund) jako v monitoru, snímky
  pollingem /VBLK. Podrobnosti budou v `vyvoj.md`.

## 2026-11-01: předloha (autor)

- **Popisek `L.ANGELS`** podle letáku (inzerátu). Katalog z 3/1983 má `L.A.`. Nejdřív bylo zvoleno `L.A.`, autor to
  změnil na původní z inzerátu. Podrobnosti v [original.md](original.md).
- **Mapa co nejvěrněji podle katalogu**, i tam, kde se remake liší. Týká se to bloku (21, 15) ve Středozemním moři, který
  remake má navíc. Nejisté okrajové bloky rozhoduje druhé čtení ([original.md](original.md)).
- **Pruh sekund:**
  - MZ-700: znak 3Ah, krok 2 s, tj. 30 buněk za 60 s. Žádný CG-ROM nemá čtvrtinu buňky pro krok 1 s.
  - MZ-800: jemně přes vlastní znaky v CG-RAM, krok 1 s po půlkách nebo jemněji.
- **Titulek EU:** `WORLD CLOCK` bez mezer ve sloupcích 20–30 místo hiragany (20–31). Hvězdičky a `S H A R P`
  zůstávají na místě. Varianta s mezerami by se mezi hvězdičky nevešla.

## 2026-11-01: nástroje

- **Pillow, numpy a scipy** (nainstalované přes `pip --user`) jen pro analytické skripty v `tools/ref/`.
- **Build a testy zůstávají jen na standardní knihovně Pythonu.**

## 2026-11-01: překladač zsdcc

- **Měření:**
  - smoke test: zsdcc 598 B, sccz80 776 B;
  - jádro času (`tests/core/run_core.py`, 8358 vektorů): zsdcc 175 tis. T na vektor, sccz80 193 tis. T.
- **Výchozí je zsdcc** (`zcc -compiler=sdcc`). Build i testy s sccz80 zůstávají funkční.

## 2026-11-01: jádro času

- **Čas je počet sekund od 2000-01-01 00:00** (`wc_time_t`, 32 bitů), roky 2000–2099.
  - V tomto rozsahu je přestupný každý čtvrtý rok, kalendář proto nepotřebuje cykly přes roky.
  - První verze s cyklem trvala asi 1 milion T na jeden místní čas, tj. 0,3 s na Z80.
- **Letní čas podle dnešních pravidel**, použitých na každý rok: EU, USA, Austrálie (jih).
- **Místní čas → UTC:**
  - opakovaná hodina na konci letního času se bere jako letní čas (dřívější okamžik);
  - čas v přeskočené hodině se bere jako standardní.
- **Ověření:** `tests/core/run_core.py` proti `zoneinfo` (Python, balíček tzdata).
  - Každý přechod 2008–2099 v 11 pásmech ±1 s a ±1 h, plus náhodné časy.
