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
- **Pruh sekund:** plný za 60 s, krok 1 s (30 buněk po půlkách), bez rasterových triků.
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

## 2026-11-01: překladač

- **Smoke test:** zsdcc 598 B, sccz80 776 B.
- **Volbu odkládám:** rozhodne se měřením velikosti a rychlosti na jádru (čas, letní čas, terminátor).
- **Build obou překladačů zůstává funkční.**
