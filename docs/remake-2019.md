# Japonský remake z roku 2019 (studijní materiál)

`input/World-Clock/WorldClock.asm` a `.mzt` (totéž je v `input/World-Clock.zip`) je remake od 紅茶羊羹
(@youkan700) z webu „We Love MZ-700“: http://www.maroon.dti.ne.jp/youkan/mz700/index.html#WorldClock.
- Ve zdroji je nadpis „世界時計デモ 勝手に再現版“, tj. svévolně zrekonstruovaná verze dema.
- Licence není uvedena. Kód nepřebíráme, slouží jen ke studiu a ke kontrole rekonstrukce.
- Binárka má jméno `WORLD CLOCK`, 0C1Ch bajtů, nahrává se i startuje na 1200h.
- Na reálném MZ-700 je vidět na `input/20190630145846.jpg`, výstup je na `input/WorldClock.gif`.

## Kódování a překlad

- **Kódování je Shift-JIS (CP932), konce řádků CRLF.**
  - Číst přes `iconv -f CP932 -t UTF-8 input/World-Clock/WorldClock.asm`.
  - Originál neměnit.
- **Syntaxe není pro pasmo**, jméno assembleru ve zdroji chybí.
  - Používá `@@:` s `@b`/`@f`, `@1:` s `@1b`/`@1f`, `CHRMAP "MZ-ASCII"` a `REPT`.
  - pasmo 0.5.3 skončí na řádku 51: „Invalid definition, previously defined as EQU or label“.

## Jak funguje

- **Start:**
  - Test monitoru 1Z-009A/B (bajty `"009"` na 06F6h). Na jiném monitoru vypíše „WORKS ONLY ON MZ-700(JP)“.
  - Používá japonský monitor (`_GETL` 0003h, `_LETNL` 0006h, `_HLHEX` 0410h, `RST 18h`) a japonský CG-ROM
    (hiragana v titulku, katakana v textech).
- **Zadání času:** japonský čas HHMM přes `_GETL` do bufferu 11A3h. Číslo se čte od 11A3h+25, tj. za výzvou.
- **Obrazovka:**
  - `ScreenData` je 1000 B textu (D000h) a 1000 B atributů (D800h).
  - Mapa je z mozaiky F0h–FFh. Pozice měst jsou `0D000h + sloupec + řádek*40`.
- **Čas:**
  - `Hour` je japonský čas v BCD. Minuty jsou dvě číslice v kódu displeje (20h + číslice), dvojtečka je 4Fh.
  - `CityTable` obsahuje posun proti JST v BCD jako doplněk do 100 (94h = −6) a adresu ve VRAM. Posuny jsou pevné, bez letního času.
- **Přerušení:**
  - 8253: CTC1 v režimu 2 s počtem 131 (polovina 262 řádků NTSC), CTC2 v režimu 0 s počtem 1, vektor na 1039h.
  - CTC1 se spouští po VBLK a 22*8+4-131-1 HBLK, takže přerušení je svázané s paprskem na textovém řádku 22.
- **Pruh sekund:**
  - Řádek 22, sloupce 4–33, jeden znak trvá 2 s. V buňce se mění znak a barva pro jednotlivé řádky paprsku (Raster #4–#7).
  - Časování je kritické, autor sám píše, že správně běží jen na reálném HW.
  - Podle autora je pruh v inzerátu kreslený znakem 4×8 (3Ah).
- **Samomodifikující kód:** `UpdateAddrText`, `UpdateAddrAttr`, `IntCount`, `Tick`, `SPSAVE`.
