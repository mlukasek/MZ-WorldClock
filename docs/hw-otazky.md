# Otázky k ověření na reálném HW

Reálné stroje má autor. U každé otázky je, proč na ní záleží.

## Výsledky (autor, 2026-11-01)

- **MZ-800 (reálný):** program běží v obou polohách přepínače SW1.
  - Spuštěno z Unicard Manageru a z manažeru UniCMT, ne z kazety. Start z kazety zatím neověřen.
  - Čas z Unicard RTC se bere správně.
- **MZ-1500 (emulátor):** běží, titulek v hiraganě.
- **Japonský MZ-700 fyzicky:** zatím nezkoušeno.

## MZ-700

1. **Co vrací `IN A,(CEh)` na MZ-700?** Plovoucí sběrnice, FFh, nebo něco jiného? Je to druhá kontrola detekce MZ-800.
   - V emulátoru vrací poslední bajt na sběrnici, tj. operand CEh.
2. **Neudělá `OUT (E4h),A` na MZ-700 nic nečekaného?** Program ho volá hned při startu na všech strojích.
   - Podle dokumentace mapuje ROM na 0000h a VRAM s I/O na D000h–FFFFh, tedy stav po startu.
3. **Matice japonské klávesnice (1Z-009):** sedí poloha písmen, která program používá (`M`, `G`, `T`)?
   - BREAK je sloupec 8, bit 7.

## MZ-800

4. **Polarita bitu 6 na portu CEh (/VBLN)** na reálném stroji, a jestli jde souběžně s PC7 8255.
5. **Stav po startu přepínačem SW1 v režimu MZ-800** (nativní IPL): nahraje se MZF z kazety či Unicard, a program
   se správně přepne do režimu MZ-700?
   - Z Unicard Manageru a UniCMT ano. Z kazety neověřeno.
6. **4barevný režim 320×200 bez rozšíření VRAM:** emulátor má rozšíření vždy.
   - Hodiny poznají rozšíření tak, že zapíšou vzorek do roviny III a čtou ho zpět. Bez rozšíření má číst FFh. Na
     stroji bez rozšíření musí být hodiny ve 4 barvách (černá, modrá, červená, žlutá), test to jen simuluje.
   - S rozšířením: 16 barev (DMD 02h), barvy 4–15 jdou mimo paletu. Odpovídají barvy emulátoru (titulek
     světle azurový, jména světle červená, ciferník ve dne světle modrý)?
7. **Přechody klávesou G:** obrazovka má na chvíli zčernat a pak se nový vzhled kreslí na čisto. Neproblikne mezi
   tím na reálném MZ-800 nějaký nepořádek (zbytky textu, CG-RAM)?
8. **Nahrání od 1200h** v režimu MZ-800 (SW1) z Unicard Manageru, UniCMT a z kazety.

## Unicard

9. **Která verze firmwaru je v kartě**, a vrací příkazy 62h/63h (RTC) platné hodnoty? V jakém stavu je stavový bajt?
   - Čtení času funguje (MZ-800). Verze firmwaru nezjištěna.
10. **Jak se RTC nastavuje** (web, shell, CP/M utility) a jestli drží čas i po vypnutí (baterie).
11. **Zápis času z dialogu (příkazy 61h, 60h):** přijme ho karta, zůstane po vypnutí a čte se pak zpět správně?
   - Emulátor zápis neumí, je to ověřené jen proti dokumentaci firmwaru.
12. **Doba čekání na hranu sekundy karty při startu:** obrazovka se objeví hned. Časy naskočí nejvýš po 1 s?

## MZ-1500

13. **PCG:** je pořadí bitů ve vzorech (bit 7 vlevo) a priorita BFP na reálném stroji tak, jak to dělá emulátor? Je
    půlbuňka pruhu purpurová a navazuje na plné buňky (znak 3Ah)?
14. **Po návratu do monitoru (BREAK)** je obrazovka v pořádku, bez zbytků PCG?
