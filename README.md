# Návrh osevního plánu 2025

Případové studie I, FIS VŠE, ZS 2026/2027. Farma má 1 000 ha a vybírá z 20 plodin, zelenina smí zabrat nejvýš 20 % plochy. Úkolem je predikovat ceny a výnosy na sezónu 2025 (data končí rokem 2024) a rozdělit půdu s ohledem na očekávanou marži a riziko.

> **Stav:** výsledky jsou návrh k diskusi ve skupině. Executive summary zatím není hotové.

## Struktura repozitáře

| Co | Kde |
|---|---|
| Vstupní data (FAOSTAT, ČSÚ, počasí) | kořen repozitáře: `plodiny*.{xlsx,csv}`, `makroekonomicke_ukazatele.xlsx`, `pocasi_*.csv` |
| **Úkol 1: marže 2024** | `compute_margins_2024.py` → `marze_2024.csv` |
| **Predikce a osevní plán** | `osevni_plan/` (kód, testy a výsledky) |
| Podrobné vysvětlení postupu s dosazenými čísly | [`osevni_plan/VYSVETLENI.md`](osevni_plan/VYSVETLENI.md) |
| Hlavní tabulky a grafy | `osevni_plan/vystupy/` |
| Podpůrné tabulky | `osevni_plan/vystupy/detaily/` |
| Korelace scénářových marží plodin | `graf_korelace_marzi_2025.png` a označené dvojice v `detaily/pary_korelace_marzi_2025.csv` |
| Souběh slabých národních výnosů | `graf_soubehu_slabych_vynosu_narodni.png`; metodika a závěr v [`osevni_plan/ANALYZA_NARODNI_SOUBEH.md`](osevni_plan/ANALYZA_NARODNI_SOUBEH.md) |

Spuštění (Python 3.10+):

```bash
pip install -r osevni_plan/requirements.txt
python3 compute_margins_2024.py        # úkol 1
python3 osevni_plan/spust.py           # predikce + plán (~10 s)
python3 -m pytest osevni_plan/test_reseni.py -q
```

---

## Úkol 1: referenční marže 2024

$M_i = P_i \cdot Y_i / 1000 - C_i$ (cena Kč/t × výnos kg/ha / 1000 − náklady Kč/ha)

Příklad, pšenice: $4\,772 \cdot 5\,956{,}7 / 1000 - 25\,000 = 3\,425$ Kč/ha.

| Plodina | Cena (Kč/t) | Výnos (kg/ha) | Náklady (Kč/ha) | **Marže (Kč/ha)** |
|---|---:|---:|---:|---:|
| Rajčata | 46 297 | 232 667 | 10 652 000 | **119 770** |
| Okurky a nakládačky | 30 891 | 76 593 | 2 276 000 | **90 022** |
| Salát a čekanka | 51 956 | 25 108 | 1 234 000 | **70 496** |
| Papriky a chilli | 26 484 | 46 643 | 1 165 000 | **70 291** |
| Květák a brokolice | 32 265 | 18 087 | 534 000 | **49 577** |
| Mrkev a tuřín | 9 788 | 40 905 | 355 000 | **45 376** |
| Zelený česnek | 124 000 | 4 525 | 521 000 | **40 100** |
| Zelí | 8 996 | 33 921 | 270 000 | **35 143** |
| Cibule a šalotka | 11 363 | 23 325 | 230 000 | **35 047** |
| Brambory | 8 558 | 28 814 | 217 000 | **29 578** |
| Cukrová řepa | 914 | 69 560 | 54 000 | **9 578** |
| Kukuřice na zrno | 4 564 | 8 142 | 30 000 | **7 159** |
| Ječmen | 5 933 | 5 271 | 25 000 | **6 273** |
| Oves | 7 929 | 3 813 | 24 000 | **6 233** |
| Pšenice | 4 772 | 5 957 | 25 000 | **3 425** |
| Řepka | 11 217 | 2 758 | 28 000 | **2 932** |
| Slunečnice | 9 624 | 2 504 | 23 000 | **1 101** |
| Len olejný | 14 370 | 1 296 | 18 000 | **628** |
| Žito | 4 697 | 4 347 | 20 000 | **419** |
| Hrách na zrno | 6 221 | 1 670 | 12 000 | **−1 614** |

Marže je jen malá část tržby. U okurek je tržba 2,37 mil. Kč/ha a marže 90 tis. Kč/ha (3,8 %), takže pokles ceny o 10 % udělá z marže ztrátu 147 tis. Kč/ha. Proto musí plán pracovat s rizikem, nejen s průměrem.

---

## Predikce 2025: postup v kostce

1. **Modely.** Pracujeme s logaritmy cen a výnosů, porovnali jsme 6 modelů cen a 8 modelů výnosů. Každý se porovnává s naivní predikcí („příští rok jako letos“).
2. **Test.** Používáme backtest s rolujícím počátkem: pro každý rok 2003–2024 se model odhadne jen z dřívějších dat a predikuje jeden rok dopředu. Metriky jsou MAE, CRPS (kvalita celého rozdělení) a pokrytí intervalů.
3. **Výběr.** Vybírá se model s nejnižší MAE přes všechny plodiny. Pro ceny i výnosy vychází **kombinace** dvou jednoduchých modelů:
   - ceny: průměr naivní predikce a návratu reálné ceny k 15letému průměru, o 5 % lepší než naivka,
   - výnosy: průměr trendu z 15 let a průměru z 5 let, o 16 % lepší než naivka.
4. **Nejistota.** Ročníkový bootstrap: scénář = chyby predikcí všech plodin z jednoho historického roku najednou. Tím se zachová to, že se ceny obilovin hýbou spolu (korelace 0,93). 5 000 scénářů roku 2025.
5. **Počasí a makro** jsme testovali. Predikci nezlepšily, a to ani kdybychom počasí roku 2025 znali dopředu.

Predikce bodově i s 80% intervaly: `osevni_plan/vystupy/predikce_2025.csv`.

![Predikce 2025](osevni_plan/vystupy/graf_predikce_2025.png)

---

## Osevní plán 2025

Maximalizujeme $(1-\lambda)\,E[\text{zisk}] + \lambda\,\text{CVaR}_{10\%}[\text{zisk}]$, kde CVaR 10 % je průměrný zisk v 10 % nejhorších scénářů. Řeší se jako lineární program. Omezení: 1 000 ha celkem, zelenina ≤ 200 ha, jedna plodina ≤ 250 ha.

**Návrh (λ = 0,5):**

| Plodina | ha |
|---|---:|
| Kukuřice na zrno | 250 |
| Řepka | 250 |
| Ječmen | 226 |
| Brambory | 74 |
| Zelený česnek | 78 |
| Zelí | 77 |
| Salát a čekanka | 45 |

| (mil. Kč) | λ = 0 (jen průměr) | **λ = 0,5** | λ = 1 (jen riziko) |
|---|---:|---:|---:|
| očekávaný zisk | 82,4 | **44,6** | 28,7 |
| medián zisku | 35,4 | **36,3** | 27,7 |
| CVaR 10 % | −107,0 | **−3,4** | 5,3 |
| pravděpodobnost ztráty | 34 % | **7 %** | 1 % |

![Osevní plán 2025](osevni_plan/vystupy/graf_osevni_plan_2025.png)

**Rozhodovací backtest 2011–2024.** Celý postup (výběr modelu, scénáře, optimalizace) jsme pustili pro každý rok jen s daty do předchozího roku a spočítali skutečný zisk plánu:

| Strategie | součet 2011–2024 (mil. Kč, ceny 2024) | ztrátové roky |
|---|---:|---:|
| **mean-CVaR, λ = 0,5** | **402** | 0 |
| max. očekávání, λ = 0 | 387 | 1 |
| mean-CVaR, výnosy tříletý průměr | 380 | 0 |
| plán podle loňských marží | 39 | 4 |
| rovnoměrně polní plodiny | 158 | 0 |

![Rozhodovací backtest](osevni_plan/vystupy/graf_rozhodovaci_backtest.png)

---

## K diskusi ve skupině

- **Model výnosů mění zeleninovou část plánu.** Kombinace a tříletý průměr jsou v backtestu statisticky nerozlišitelné, ale u zeleniny dávají jiné výnosy a marže je tam malý zbytek z velké tržby. Stabilní jádro plánu je v obou případech stejné: řepka, ječmen a zelí (`vystupy/citlivost_plan_2025.csv`, oddíl 7 ve [`VYSVETLENI.md`](osevni_plan/VYSVETLENI.md)).
- **Volba λ** je rozhodnutí o averzi k riziku. Tabulka výše ukazuje, co se za ni platí.
- **Předpoklady:** náklady 2025 = náklady 2024 × 1,024 (inflace 2024), národní výnosy místo farmových, cena nezávisí na produkci farmy. Celý seznam je v oddílu 9 ve [`VYSVETLENI.md`](osevni_plan/VYSVETLENI.md).
