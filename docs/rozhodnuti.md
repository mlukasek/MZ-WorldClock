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

  Ověřeno ze ROM v emulátoru. Detekci MZ-800 upřesňuje oddíl o MZ-1500 níže.
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

## 2026-11-01: historický vzhled a čas

- **Časová základna** (`src/mz/timebase.c`), bez přerušení a s DI:
  - CTC1 v režimu 2 dělí HSYNC na 1 Hz (počet 15611 PAL / 15700 NTSC, jako TIMST monitoru);
  - CTC2 v režimu 0 s počtem 0 je volně běžící čítač sekund, PC2=0 maskuje INT;
  - CTC2 se načítá trikem z TIMST: CTC1 dočasně s počtem 10;
  - čtení CTC2, CTC1, CTC2 se opakuje, dokud se CTC2 nezmění;
  - `clock_set` restartuje CTC1, takže nová sekunda začíná přesně v okamžiku nastavení.
- **PAL / NTSC se měří:** řádky mezi dvěma VBLK přes CTC1, tj. 312 nebo 262. Nebere se z ROM.
- **Dvojtečky blikají 1 Hz:** svítí v první polovině sekundy. Originál nebyl k dispozici, fotky ukazují dvojtečky.
- **Pruh:** po minutě prázdný, každé 2 s o buňku víc, plný (30) v poslední sekundě minuty.
- **Výchozí domovské pásmo:** Praha (EU stroje), Tokio (japonský monitor).
- **Dialog:**
  - sekundy začínají od 0 v okamžiku stisku CR;
  - bez času po startu nabídne `BREAK` konec do monitoru.
- **Konec:**
  - před návratem se čeká na uvolnění kláves, aby monitor neviděl BREAK;
  - hodiny monitoru se nastaví na místní čas domovského pásma (TIMST), PC2=1, EI, smaže se obrazovka.

## 2026-11-01: Unicard RTC

- **Detekce:** REVD (06h), stav po STSR `(s0 & 83h) == 02h`, `s1 == 06h`, `s2 == 4`. Bity 2–5 bajtu 0 hlásí otevřené
  soubory, proto maska. Bez karty porty plavou a stav nesedí.
- **Čtení:** datum (62h), čas (63h) a znovu datum. Když se datum mezitím změnilo, opakuje se. Hodnoty jsou binárně.
  - Rok mimo 2020–2099 nebo neplatné údaje znamenají nenastavené hodiny a program nabídne dialog. Typický případ je
    výchozí rok 1980 na MZPico.
- **Karta drží místní čas domovského pásma.** Výchozí je Praha, na japonském stroji Tokio.
- **Start:**
  - čeká se na změnu sekundy karty a hodiny se nastaví na její hraně;
  - čekání trvá nejvýš 2 s vlastních hodin, pak se vezme přečtený čas;
  - s nalezenou kartou se historická obrazovka vykreslí hned, aby po dobu čekání nebyla vidět hlavička monitoru.
- **Za běhu:** každých 10 minut se karta čte jednou za snímek, dokud se nezmění sekunda. Hodiny se pak nastaví, přesnost
  je jeden snímek.
- **Ruční nastavení (T):**
  - čas se zapíše i do karty (61h, 60h);
  - když ho karta nepřijme, program ji dál nenásleduje, jinak by ruční čas při dorovnání přepsala;
  - emulovaná Unicard zápis neumí;
  - při změně pásma v dialogu se platný čas přepočítá na stejný okamžik v novém pásmu.

## 2026-11-01: MZ-1500 a detekce GDG

- **MZ-1500 je cílový stroj** (autor, 2026-11-01). Funguje jako japonský MZ-700, titulek je v hiraganě.
- **Monitor MZ-1500** začíná stejně jako 1Z-013B na MZ-800 skokem do IPL (`C3 00 E8`). V hlavičce ale má
  „1Z-009B“ a od 1Z-009B MZ-700 se liší jen ve 2 bajtech. CG-ROM je shodný s japonským MZ-700.
  - Samotná signatura ROM tak MZ-800 nepozná. Na MZ-1500 by program zapnul grafiku MZ-800, kterou nemá.
- **O MZ-800 rozhoduje hardware:** bit 6 stavového portu CEh (/VBLN) musí sledovat PC7 8255 (/VBLK).
  - Měří se 2000 vzorků přes několik snímků: aspoň 2 hrany VBLK a shoda v 98 % vzorků.
  - Kvůli neověřené polaritě se připouští i obrácená.
  - Na MZ-700 a MZ-1500 port CEh neexistuje a čtení vrací konstantní hodnotu sběrnice.
- **Modely:**
  - MZ-800, když je GDG;
  - MZ-1500, když skok do IPL, bez GDG a hlavička „1Z-009“;
  - jinak MZ-700.
- **Japonský stroj:** hlavička „1Z-009“, tj. MZ-700 JP i MZ-1500.
- **Zápis `OUT (CEh),08h` se dělá před ověřením.** Na MZ-1500 porty CCh–CFh neexistují, zápis je neškodný.
- **PCG MZ-1500** program zatím nepoužívá (nápad: jemnější pruh sekund jako na MZ-800).

## 2026-11-01: prohození kontinentů (klávesa M, autor)

- **Výchozí je dobový pohled**, Pacifik uprostřed.
- **M prohodí kontinenty:** Amerika vlevo, Evropa uprostřed, Asie vpravo, jak je dnes zvykem v Evropě. Další M vrátí
  dobový pohled.
- **Mapa se cyklicky pootočí o 44 bloků** (22 znaků). Řez je ve sloupci bloků 44, ten je prázdný (Pacifik), takže se
  žádná pevnina nerozdělí a mozaika se posouvá po celých znacích.
- **Názvy a hodiny se posouvají s mapou.** Celou obrazovku posunout nejde: popisky pokrývají sloupce 2–38 v různých
  řádcích (TOKYO 19–23, L.ANGELS 22–29), každý řez by některý rozdělil.
  - TOKYO a SYDNEY by přetekly přes okraj, mají vlastní místo (sekce `[atlantic]` v `data/historic.txt`).
  - `tools/mkhistoric.py` kontroluje, že nic nepřetéká a nic se nepřekrývá.
- **Přepínání historického a moderního vzhledu na MZ-800** proto nebude na M, ale na **G** (grafika).

## 2026-11-01: vlastní znaky na MZ-800 (CG-RAM)

- **Znaky jsou v `data/glyphs.txt`**, vlastní kresba 8×8 (GPL), ne kopie znakového generátoru Sharp. Tabulku
  z nich dělá `tools/mkglyphs.py`.
- **Pruh v krocích po 1 s** (autor): půlka znaku 3Ah, tedy jeho levá spodní čtvrtina.
  - Je na stejném kódu 3Ah v sadě 1, půlbuňka je pak tentýž znak s bitem 7 atributu.
  - Pruh vypadá stejně jako na fotkách, jen plynuleji.
  - MZ-700 zůstává u kroku 2 s.
- **Hiragana titulku na MZ-800** (せ か い と ゛ け): na kódech sady 1 jako v japonském CG-ROM, takže MZ-800 bere
  japonský titulek z dat beze změny.
- **Nahrání do CG-RAM:**
  - `IN (E0h)` v režimu MZ-700 mapuje CG-ROM na 1000h a CG-RAM na C000h, `IN (E1h)` je odmapuje;
  - na konci programu se CG-RAM znovu zkopíruje z CG-ROM, jako to dělá IPL;
  - test to ověřuje přes regiony emulátoru `cgram_700` a `cgrom`.
- **Pruh se počítá v půlkách buňky:** jemný režim `s+1`, hrubý `(s+1) & ~1`. V obou je plný v poslední sekundě minuty
  a jemný je vždy aspoň tak dlouhý jako hrubý.

## 2026-11-01: PCG na MZ-1500 (autor)

- **Pruh v krocích po 1 s i na MZ-1500**, přes PCG. Vzhled zůstává jako na fotkách.
- **Programování PCG** (podle zdrojů mz800emu a IPL MZ-1500; skutečný HW ještě neověřen, `hw-otazky.md`):
  - Režim: `OUT (F0h),03h` je režim MZ-1500 s prioritou BFP (text dole, nenulové body PCG navrch), `OUT (F0h),00h`
    je režim MZ-700 jako po IPL. Port jde jen zapisovat.
  - Banky: `OUT (E5h),1..3` mapuje banku vzorů 1–3 (bity indexu barvy) na D000h–EFFFh, 8 bajtů na znak, **bit 7 je
    nejlevější bod** (u CG-ROM bit 0). `OUT (E6h)` je odmapuje. Mezitím nejsou dostupné VRAM, I/O na E000h ani
    F000h–FFFFh. Kód je na 2000h–7FFFh a běží s DI.
  - Buňky: PCGLO na D400h + pozice (číslo znaku), PCGHI na DC00h + pozice, bit 3 = PCG zapnuto. Vypnuto se píše
    71h, to je hodnota z CLS monitoru.
  - Barva: IPL nastavuje identickou paletu, index 3 (roviny 1 a 2) je purpurová.
- **Půlbuňka pruhu na MZ-1500** je prázdná textová buňka se zapnutým PCG znakem 1, tj. glyf `BAR_HALF` s převráceným
  pořadím bitů.
- **Konec:** `OUT (F0h),00h`, bajty buněk vrátí CLS monitoru.
- **Program porty F0h a E5h na jiných strojích nepoužívá.** Na MZ-800 je F0h paleta, na MZ-700 je E5h „zakázaný“
  režim paměti.
