# Zdroje a pátrání po originálu

Pátrání proběhlo 2026-11-01 na webu, japonsky i anglicky.

## Originální program pro MZ-700: nenalezen

- **Hledáno:**
  - dump (.mzt/.mzf/.m12);
  - výpis v časopisech (I/O, Oh!MZ, ASCII, ベーマガ);
  - demo a předváděcí kazety (店頭デモ);
  - Internet Archive, sharpmz.net, seznamy her MZ-700.
- **Výsledek:** nenalezeno.
  - Japonská komunita sama neví, jestli program existoval, nebo byl jen „projekční fake“ pro fotku.
    Otázka AKD: http://mzakd.cool.coocan.jp/starthp/gbg.html
  - Demo kazeta MZ-800 obsahuje jen OPENING, MUSIC a COLOR PLOTTER.
- **Manuál MZ-700**, oddíl 2.3.8 TI$, s. 60, má jen textovou ukázku: zadá se newyorský čas a vypíše se 10 měst.
  https://www.manualslib.com/manual/1004153/Sharp-Mz-700.html?page=62

## Dobové fotky obrazovky

- **`input/mz-700c2.jpg`:** leták MZ-700 („こんなMZを待っていた。“), malé rozlišení.
- **Katalog MZ-700 z 3/1983 (パソ-016), strana MZ-731, 1447×1024:** https://ratscats.client.jp/p-sh/smz72.JPG
  - Přehled skenů: https://ratscats.client.jp/s-mz715.html
  - Časy podle odečtu: Moskva 18:00, Paříž 16:00, Peking 23:00, L.A. 07:00, Tokio 00:00, Washington 10:00,
    J. Afrika 17:00, Rio 12:00, Sydney 01:00. Sedí na Tokio 00:00 se standardními posuny bez letního času.
- **Oficiální placené reprinty katalogů** (COCORO BOOKS, MZ-700 11/1982, anglický 1/1984) mohou mít lepší rozlišení:
  https://galapagosstore.com/web/catalog/sharp/top
- **Katalog MZ-1200** měl podle AKD variantu „*** WORLD CLOCK ***“ zeleně. Sken nenalezen.

## Příbuzné: MZ-80B

- Muzeum 夢の図書館 (Microcomputer Museum Japan) v 11/2025 rozběhlo originální demo „WORLD CLOCK SHARP“ z reklam
  na MZ-80B z roku 1981. Potřebuje grafickou desku 320×200.
  https://x.com/Dream_Library_/status/1984618808334827618
- Fotka je `input/G4rIGo-bQAEXAT-.jpeg`: grafická mapa, 8 měst a ručičkové hodiny LOCAL TIME (TOKYO).

## Remaky (studijní materiál, kód nepřebírat)

- **紅茶羊羹 (@youkan700), 2019:** `input/World-Clock`, viz [remake-2019.md](remake-2019.md).
- **ひろっぴ (@ihirppi), 2019, Hu-BASIC:** teorie, že pruh roste o znak za sekundu a je plný za 30 s.
  https://ihiroppi.blue.coocan.jp/str0/index.html
- **AKD (@akd1500), 2022, `wclock1200.zip`:** obrazovka „*** WORLD CLOCK ***“ podle katalogu MZ-1200.
  http://mzakd.cool.coocan.jp/starthp/mzts/wclock1200.zip
- **iOS aplikace doto clock (masayuki morisita, 2021–2024):** zdroj obrázků `input/001-0x` a `input/313x145bb*`.
  https://apps.apple.com/jp/app/doto-clock/id1552829897

## Koho se zeptat na originál

- Muzeum 夢の図書館: má originál pro MZ-80B, možná ví víc.
- AKD (@akd1500), 紅茶羊羹 (@youkan700).

## Unicard

- Projekt „MZ800 Unicard 2nd generation“ (mz800ukp1, GPLv2): https://sourceforge.net/p/mz800ukp1/
- Příkazy RTC a příklad `example5.s` jsou v `STM32fw/doc/examples/`.
- Lokálně: `E:\SAPI_GIT\unicard-mk3b`, popis `E:\SAPI_GIT\SAPI_DPI-firmware\docs\unicard.md`.
