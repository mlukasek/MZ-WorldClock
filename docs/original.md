# Předloha: obrazovka dema z dobových fotek

Rekonstrukce 2026-11-01. Výsledek je [data/historic.txt](../data/historic.txt), náhled vytvoří
`python tools/mkhistoric.py data/historic.txt --png work/historic`.

## Zdroje

| Zdroj | Rozlišení obrazovky | Použití |
|---|---|---|
| Katalog MZ-700, 3/1983, strana MZ-731 (`input/catalog/smz72.JPG`, [zdroje.md](zdroje.md)) | asi 175×110 px fotky na 320×200 bodů, tj. 0,56 px na bod | rozvržení, popisky, mapa |
| Leták MZ-700 (`input/mz-700c2.jpg`) | asi 110×80 px | kontrola, barvy |
| Japonský remake z roku 2019 ([remake-2019.md](remake-2019.md)) | přesná data, ale odvozená z letáku | hypotéza pro zarovnání, druhé čtení nejistých bloků |

Obě fotky ukazují stejný okamžik: Tokio 00:00 a ostatní města ve standardním čase (bez letního). Pruh sekund je
naplněný zhruba z poloviny.

## Postup

1. **Zarovnání fotky s obrazovkou** (`tools/ref/align_catalog.py`, Pillow + numpy + scipy).
   - Kubický polynom mapuje body obrazovky na pixely fotky, zachytí perspektivu i zakřivené sklo obrazovky CRT.
   - **Jisté body:**
     - šest hvězdiček titulku;
     - čára pod titulkem (detekovaná po sloupcích fotky);
     - čára pravítka, jeho dva sloupky a pět rysek.
   - **Uvnitř** korelace modré barvy na fotce s mapou remaku: 0,91.
   - Geometrická chyba u jistých bodů je 0,71 px fotky rms, tj. asi 1,3 bodu obrazovky.
   - Mapa a popisky remaku vychází na stejných pozicích ve všech čtyřech kvadrantech, posun je (0, 0) s korelací 0,93–0,99.
2. **Čtení bloků mozaiky.** Blok mozaiky je tečka 3×3 body v buňce 4×4.
   - V každém z 80×50 bloků se změří modrá ve středu tečky.
   - Histogram je čistě dvoustavový.
   - `tools/ref/extract_map.py`: blok svítí od 0,6, tmavý je do 0,15.
   - **Nejisté bloky:** 85 bloků je mezi 0,15 a 0,6, převážně na okrajích pevnin. Rozhodne je druhé čtení (remake).
     V 10 z nich by se prosté prahování na 0,45 lišilo od remaku. Všechny jsou na hranici rozlišení fotky.
   - **Jediný jasný rozdíl proti remaku:** blok (řádek 21, sloupec 15) je na fotce tmavý (0,08).
     - Na obrazovce 40×25 je to pravá dolní tečka buňky na řádku 10, sloupci 7: Středozemní moře, dva řádky pod
       dvojtečkou času u Paříže.
     - Okolní pevnina má 0,82–0,98, sousední bloky moře 0,03–0,09.
     - Remake tam má tečku navíc. **Autor potvrdil: co nejvěrněji podle katalogu, blok zůstává tmavý.**
3. **Popisky a časy:** v každé buňce textu se změří červená (názvy) a žlutá (časy). Všechny jsou ve stejných buňkách
   jako v remaku. Jediná výjimka je popisek Los Angeles (viz Rozdíly mezi fotkami).
4. **Kontrola:** náhled vedle vyrovnané fotky (`work/ref/cmp_catalog_jp.png`).

## Rozvržení (40×25)

| Prvek | Řádek | Sloupce | Znaky | Barva |
|---|---|---|---|---|
| Titulek | 0 | `***` 2–4, `S H A R P` 8–16, `せ か い ど け い` 20–31, `***` 34–36 | text, hiragana ze sady 1 JP CG-ROM | azurová |
| Čára pod titulkem | 1 | 2–36 | 36h (horní 2 řádky buňky) | azurová |
| Mapa | 2–21 | | mozaika F0h–FFh | modrá |
| Názvy měst | | | text | červená |
| Časy HH:MM | pod názvy | | text, dvojtečka 4Fh | žlutá |
| Pruh sekund | 22 | 4–33 (30 buněk) | 3Ah (spodní polovina buňky) | purpurová |
| Pravítko | 23 | 3–34 | 3Fh 32h 3Ch… 33h… 37h, rysky po 5 sloupcích, tj. 6 úseků po 10 s | zelená |

Hiragana titulku: 90h せ, 94h か, 85h い, 93h と a BCh ゛, 9Ch け, 85h い. Kódy jsou ze sady 1 (bit 7 atributu).
Znak ど jsou dvě buňky, と a dakuten. Na fotce to potvrzují rozestupy.

Města a pozice (řádek, sloupec):

| Název | Čas | Pásmo dnes |
|---|---|---|
| MOSCOW (4, 9) | (5, 9) | UTC+3 |
| PARIS (7, 5) | (8, 5) | UTC+1, letní čas EU |
| PEKIN (9, 13) | (10, 13) | UTC+8 |
| L.ANGELS (7, 22) | (8, 24) | UTC−8, letní čas USA |
| TOKYO (11, 19) | (12, 19) | UTC+9 |
| WASHINGTON (10, 29) | (11, 33) | UTC−5, letní čas USA |
| REO (15, 34) | (16, 33) | UTC−3 (bez letního času od 2019) |
| S.AFRICA (18, 2) | (19, 4) | UTC+2 |
| SYDNEY (19, 17) | (20, 17) | UTC+10, letní čas AU |

## Rozdíly mezi fotkami

- **Popisek Los Angeles:** leták (a remake) má `L.ANGELS` ve sloupcích 22–29. Katalog má `L.A.` ve sloupcích 22–25
  a za ním je vidět mapa. **Použito `L.ANGELS` podle letáku, tj. inzerátu, hlavního zdroje autora** (rozhodnutí
  autora). Bloky mapy pod popiskem zůstávají v datech tmavé jako pod ostatními popisky.
- Jinak se fotky neliší v ničem, co jde rozlišit.

## Jistota

- **Jisté:**
  - rozvržení titulku, čáry a pravítka;
  - texty a buňky popisků a časů;
  - barvy;
  - znak pruhu (3Ah), na fotce je to spodní polovina buňky;
  - tvar mapy kromě okrajových bloků.
- **Nejisté na ±1 blok:** okraje pevnin (85 bloků, rozhodnutých podle druhého čtení) a vztah mapy k titulku a pravítku.
- **Neznámé:**
  - jak se pruh sekund pohyboval: plný za 30 nebo za 60 s, po celých znacích, nebo plynule. Pravítko se 6 úseky
    ukazuje na 60 s.
  - jestli dvojtečka blikala.
  - jak program začínal (zadání času).

## Znaky CG-ROM

- **Mozaika F0h–FFh** je v EU, JP i MZ-800 CG-ROM stejná. Tečky jsou oddělené (3×3 body s mezerou), bit 0 je vlevo
  nahoře, bit 1 vpravo nahoře, bit 2 vlevo dole, bit 3 vpravo dole.
- **Pruh:** v žádném CG-ROM (EU, JP, MZ-800, obě sady) není plná čtvrtina buňky 4×4 bodů. Pruh se spodní polovinou
  buňky (3Ah) proto na MZ-700 roste jen po celých znacích, tj. po 2 s při 60 s na 30 buněk. Plné poloviny buňky jsou
  jen svislé: 7Bh vlevo, 3Bh vpravo.
- `python tools/cgrom.py sheet EU|JP|800 work/cg/x.png` vykreslí všech 512 znaků.
