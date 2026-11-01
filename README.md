# World Clock pro Sharp MZ-700 a MZ-800

Vzkříšení dema světových hodin „SHARP せかいどけい“, které Sharp v letech 1982–83 ukazoval v inzerátech a katalozích
počítače MZ-700. Na obrazovce je mapa světa z modrých bloků, devět měst s časy a pruh sekund. Originální program se
nikdy nenašel, předlohou jsou dobové fotky ([docs/zdroje.md](docs/zdroje.md)).

**Stav: ve vývoji.**

## Cíl

- **Jeden program pro všechny stroje:** Sharp MZ-700 v evropské (PAL) i japonské (NTSC) verzi, MZ-800 a MZ-1500.
  Program sám pozná, na čem běží.
- **Historický vzhled** jako v inzerátu, s dnešními skutečnými časy včetně letního času.
- **Moderní vzhled na MZ-800** v grafice 320×200: den a noc na mapě, domovské město a pásmo, velké digitální
  a ručičkové hodiny. Přepíná se klávesou.
- **Čas** z hodin karty Unicard, pokud je v počítači. Jinak se program na čas zeptá.
- **Později port na SAPI-1** s kartou CGA-1V.

## Překlad

Potřeba je z88dk (nightly) a Python 3. Postup je v [docs/vyvoj.md](docs/vyvoj.md).

## Licence

GPL-3.0, viz [LICENSE](LICENSE). Sharp, MZ-700 a MZ-800 jsou ochranné známky společnosti Sharp Corporation. Projekt
s ní nijak nesouvisí.
