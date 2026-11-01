# Otázky k ověření na reálném HW

Reálné stroje má autor. U každé otázky je, proč na ní záleží.

## MZ-700

1. **Co vrací `IN A,(CEh)` na MZ-700?** Plovoucí sběrnice, FFh, nebo něco jiného? Je to druhá kontrola detekce MZ-800.
   - V emulátoru vrací poslední bajt na sběrnici, tj. operand CEh.
2. **Neudělá `OUT (E4h),A` na MZ-700 nic nečekaného?** Program ho volá hned při startu na všech strojích.
   - Podle dokumentace mapuje ROM na 0000h a VRAM s I/O na D000h–FFFFh, tedy stav po startu.
3. **Matice japonské klávesnice (1Z-009):** sedí poloha písmen, která program používá (`M`, `D`, `A`, `H`, `T`)?
   - BREAK je sloupec 8, bit 7.

## MZ-800

4. **Polarita bitu 6 na portu CEh (/VBLN)** na reálném stroji, a jestli jde souběžně s PC7 8255.
5. **Stav po startu přepínačem SW1 v režimu MZ-800** (nativní IPL): nahraje se MZF z kazety či Unicard, a program
   se správně přepne do režimu MZ-700?
6. **4barevný režim 320×200 bez rozšíření VRAM:** emulátor má rozšíření vždy.

## Unicard

7. **Která verze firmwaru je v kartě**, a vrací příkazy 62h/63h (RTC) platné hodnoty? V jakém stavu je stavový bajt?
8. **Jak se RTC nastavuje** (web, shell, CP/M utility) a jestli drží čas i po vypnutí (baterie).
