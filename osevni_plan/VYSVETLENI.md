# Osevní plán 2025: postup, modely a výsledky

Tenhle dokument podrobně vysvětluje řešení ve složce `osevni_plan/`. Všechna čísla pochází z běhu `python3 osevni_plan/spust.py`. Hlavní tabulky a grafy jsou ve `vystupy/`, podpůrné ve `vystupy/detaily/`. Stručný přehled je v `README.md` v kořeni repozitáře.

Tento dokument popisuje **první část projektu** (původní zadání, `zadani/osevni_plan_1.pdf`): predikci cen a výnosů a původní osevní plán. Executive summary k ní je ve složce `Odevzdání/`.

**Druhá část** (doplnění zadání z `zadani/osevni_plan_2.pdf`: nejisté náklady, nejistý limit zeleniny a nejistý rozpočet) je v samostatném dokumentu [`DOPLNENI_ZADANI.md`](DOPLNENI_ZADANI.md). Ten končí odolným plánem, který doporučujeme po doplnění. Podklady pro executive summary k doplnění jsou v [`PODKLADY_EXECUTIVE_SUMMARY.md`](../PODKLADY_EXECUTIVE_SUMMARY.md).

---

## 1. Logika celého řešení

Zadání má dvě části: predikci cen a výnosů a osevní plán. Spojuje je jedna věc. Optimalizace nepotřebuje jedno číslo pro každou plodinu, ale **rozdělení marže**, protože má brát v úvahu riziko. Predikční část proto nekončí bodovým odhadem, ale 5 000 scénáři roku 2025. Každý scénář obsahuje cenu i výnos všech 20 plodin najednou.

```
data 1993–2024 ──> modely (backtest + pravidlo výběru) ──> bodová predikce 2025
                                                          + historické chyby predikcí
                                                          ──> 5 000 scénářů (cena, výnos) × 20 plodin
                                                          ──> scénáře marže
                                                          ──> LP optimalizace (mean-CVaR) ──> osevní plán
```

**Pravidlo proti úniku informací.** Počasí i makro soubory obsahují rok 2025. Loader (`data.py`) všechno ořízne na roky ≤ 2024 a test `test_zadna_data_po_2024` to hlídá. Druhý test (`test_modely_nevidi_budoucnost`) přepíše všechna data po roce T na nesmysl a ověří, že se predikce z roku T nezmění.

---

## 2. Dílčí úkol: marže 2024

$M_i = P_i \cdot Y_i / 1000 - C_i$

Pšenice: $M = 4\,772 \cdot 5\,956{,}7 / 1000 - 25\,000 = 28\,425 - 25\,000 = 3\,425$ Kč/ha.

Tržba z hektaru pšenice je 28 tis. Kč, náklady 25 tis. Kč, na hektaru tedy zbyde 3,4 tis. Kč. Tabulka pro všech 20 plodin je v `marze_2024.csv` v kořeni repozitáře (skript `compute_margins_2024.py`). `data.py` počítá totéž a výsledky se shodují.

Z tabulky je vidět jedna důležitá věc: **referenční náklady jsou nastavené tak, že marže je jen malá část tržby.** U okurek je tržba 2,37 mil. Kč/ha a marže 90 tis. Kč/ha (3,8 %). Když cena okurek klesne o 10 %, tržba klesne o 237 tis. Kč a marže se změní z +90 tis. na −147 tis. Kč/ha. U zeleniny proto malá chyba v predikci ceny nebo výnosu převrátí zisk ve ztrátu. Tohle je hlavní důvod, proč musí optimalizace pracovat s rizikem, a taky důvod, proč je plán citlivý na volbu modelu výnosů zeleniny (oddíl 7).

---

## 3. Predikce: proč jednoduché modely

Máme 32 ročních pozorování (1993–2024) na řadu a 40 řad (20 cen, 20 výnosů). Model s mnoha parametry se na 30 bodech přeučí. Proto:

- modelujeme **logaritmy**: chyba 0,10 v logaritmu ≈ chyba 10 %, takže se dají srovnávat plodiny s cenou 900 Kč/t (cukrová řepa) i 124 000 Kč/t (česnek),
- kde to jde, **sdílíme parametry mezi plodinami**,
- každý model porovnáváme s **naivní predikcí** („příští rok bude jako letos“).

### 3.1 Modely cen (`modely.py`)

| Model | Rovnice | Nápad |
|---|---|---|
| `naivni` | $\ln \hat P_{T+1} = \ln P_T$ | benchmark, náhodná procházka |
| `drift` | $\ln P_T + \overline{\Delta \ln P}$ | procházka s průměrným růstem |
| `ar_sdileny` | $r_{T+1} = \mu_i + \varphi (r_T - \mu_i)$ | reálná cena se vrací k průměru, $\varphi$ společné pro všechny plodiny |
| `ar_plodina` | totéž, $\varphi_i$ pro každou plodinu zvlášť | bez sdílení |
| `ar_sdileny_kurz` | + zpožděná změna kurzu CZK/EUR a inflace | makroekonomické proměnné |
| `kombinace` | průměr `naivni` a `ar_sdileny` (v logaritmech) | kombinace predikcí |

$r_t = \ln(P_t / \text{CPI}_t)$ je reálná log-cena v cenách roku 2024. Průměr $\mu_i$ se počítá z posledních 15 let, protože reálné ceny plodin od 90. let zhruba o polovinu klesly (pšenice 2 947 Kč/t v roce 1993 odpovídá asi 10 200 Kč/t v cenách 2024). Průměr přes celou historii by predikci táhl k cenám 90. let.

**Dosazení pro pšenici (predikce 2025):**

- průměrná reálná cena 2010–2024: $e^{\mu} = 6\,286$ Kč/t,
- cena 2024: 4 772 Kč/t, odchylka $r_{2024} - \mu = \ln(4772/6286) = -0{,}276$ (o 24 % pod průměrem),
- odhad $\varphi = 0{,}385$ z 20 plodin × 14 let,
- reálná predikce: $6\,286 \cdot e^{0{,}385 \cdot (-0{,}276)} = 6\,286 \cdot 0{,}899 = 5\,653$ Kč/t,
- převod do nominálu očekávanou inflací 2,4 % (inflace 2024, poslední známá): $5\,653 \cdot 1{,}024 = 5\,789$ Kč/t,
- kombinace s naivní predikcí: $\sqrt{4\,772 \cdot 5\,789} = 5\,256$ Kč/t.

$\varphi = 0{,}385$ znamená, že se z odchylky od průměru za rok udrží asi 39 % a zbytek zmizí. Pšenice je teď levná, takže model čeká růst. Kombinace tenhle odhad z poloviny stahuje zpátky k letošní ceně.

### 3.2 Modely výnosů

| Model | Rovnice | Nápad |
|---|---|---|
| `naivni` | $\ln \hat Y_{T+1} = \ln Y_T$ | benchmark |
| `prumer3` | průměr $\ln Y$ za poslední 3 roky | kandidát z druhého řešení skupiny |
| `prumer5` | průměr $\ln Y$ za posledních 5 let | tlumí náhodné výkyvy |
| `trend` | $\ln Y = a + b t$ přes celou historii | technologický pokrok |
| `trend15` | lineární trend z posledních 15 let | reaguje na zlomy |
| `trend15_robustni` | Theil–Sen trend (medián sklonů) | odolný vůči extrémním rokům |
| `trend15_pocasi` | trend + srážky + teplota, efekt počasí sdílený v podskupině plodin | vysvětlující proměnné |
| `kombinace` | průměr `trend15` a `prumer5` | kombinace predikcí |

**Dosazení pro pšenici:** trend15 dává 6 438 kg/ha, průměr pěti let 6 183 kg/ha, kombinace $\sqrt{6\,438 \cdot 6\,183} = 6\,309$ kg/ha.

### 3.3 Počasí

**Model.** Pro podskupinu plodin $s$ (obiloviny, olejniny, okopaniny a luskoviny, zelenina):

$\ln Y_{i,t} = a_i + b_i t + \gamma_{s,1}\,\text{srážky}_t + \gamma_{s,2}\,\text{teplota}_t + \varepsilon_{i,t}$

Každá plodina má vlastní úroveň $a_i$ a trend $b_i$, efekt počasí $\gamma_s$ sdílí celá podskupina. Odhad je jedna společná OLS regrese. Počítá se přes Frisch–Waughovu–Lovellovu větu: z log-výnosů **i z počasí** se odstraní lineární trend a $\gamma_s$ se odhadne z očištěných dat. Očištění počasí je nutné, protože teplota v letech 2010–2024 rostla o 0,13 °C ročně. Bez něj by se oteplování pletlo s technologickým trendem výnosů. Test `test_pocasi_je_spolecna_ols` ověřuje, že výsledek je shodný s přímou regresí se všemi konstantami a trendy.

**Problém s predikcí.** Počasí za rok 2025 v době plánování (konec roku 2024) neznáme. Do modelu se proto dosazuje očekávané počasí: lineární trend srážek a teploty za posledních 15 let prodloužený na rok T+1.

**Test „co kdybychom počasí znali“ (oracle).** Průměrná absolutní chyba log-výnosu 2011–2024:

- s očekávaným počasím: 0,1419,
- se skutečným počasím roku T+1: 0,1449.

Se znalostí skutečného počasí je predikce dokonce **horší**. Odhadnuté efekty jsou malé a nestabilní (pro obiloviny −1,0 % výnosu na +94 mm srážek, +1,3 % na +1 °C) a na 15 letech se odhadují hlavně z šumu. Máme k dispozici jen **roční** úhrn srážek a průměrnou teplotu za celou ČR, ale výnos ovlivňuje hlavně počasí v období růstu (duben–červen). Diebold–Mariano test mezi trendem s počasím a bez něj: p = 0,85.

Závěr pro prezentaci: **roční meteorologická data jsme otestovali a predikci nezlepšují.** Nejistota počasí se do scénářů dostane jinak, přes historické chyby predikcí (oddíl 5).

---

## 4. Jak jsme modely testovali

### 4.1 Backtest s rolujícím počátkem

Pro každý rok T = 2002, 2003, …, 2023:
1. vezmeme jen data do roku T,
2. každý model odhadneme znovu a predikujeme rok T+1,
3. uložíme chybu $e = \ln(\text{skutečnost}) - \ln(\text{predikce})$.

Dostaneme 22 let chyb mimo vzorek (2003–2024). Každá predikce vznikla bez znalosti roku, který predikuje.

### 4.2 Metriky

**MAE** (průměrná absolutní chyba v logaritmu). MAE 0,14 = predikce se průměrně mýlí o ~14 %.

**CRPS** hodnotí celé rozdělení, ne jen bod. Pro vzorek scénářů $X$ a skutečnost $y$:
$\text{CRPS} = E|X - y| - \tfrac12 E|X - X'|$.
První člen trestá rozdělení, které je od skutečnosti daleko, druhý odečítá šířku rozdělení, takže model nemůže „podvádět“ tím, že bude mít obrovský interval. Pro bodovou predikci se CRPS rovná absolutní chybě.

**Pokrytí intervalů.** Pokud je 80% interval dobře nastavený, má skutečnost padnout dovnitř v 80 % případů.

Pravděpodobnostní predikce pro rok t = bodová predikce + chyby stejného modelu z let **před** t (vyhlazený bootstrap, oddíl 5). Vyhodnocujeme roky 2011–2024, aby bylo k dispozici aspoň 8 let historie chyb: 14 let × 20 plodin = 280 predikcí pro každý model.

### 4.3 Pravidlo výběru modelu

**Vybíráme model s nejnižší MAE přes všechny plodiny a roky.** Výběr děláme souhrnně, ne pro každou plodinu zvlášť: na 14–22 testovacích letech na plodinu by „nejlepší model pro řepku“ byl z velké části náhoda. MAE jsme zvolili proto, že je k dispozici od prvního roku backtestu (2003). Pravidlo tak jde použít i **vnořeně**, jen s chybami známými do roku T. To potřebujeme v rozhodovacím backtestu (oddíl 8).

Pro finální plán se pravidlo aplikuje na chyby 2003–2024. Při vnořeném použití (výběr v každém roce T = 2010, …, 2023 jen z chyb do roku T) vychází **kombinace pro ceny i výnosy ve všech 14 letech**. Výběr modelu je tedy stabilní a nezávisí na tom, že známe celé období.

### 4.4 Výsledky backtestu

**Ceny** (`vystupy/backtest_ceny_souhrn.csv`, graf `graf_backtest_modelu.png`):

| Model | MAE | CRPS | CRPS vs. naivní | pokrytí 80 % | pokrytí 95 % |
|---|---|---|---|---|---|
| **kombinace** | **0,140** | 0,108 | **0,947** | 81 % | 91 % |
| naivni | 0,148 | 0,114 | 1,000 | 83 % | 93 % |
| ar_sdileny | 0,149 | 0,114 | 1,002 | 76 % | 91 % |
| ar_plodina | 0,145 | 0,115 | 1,007 | 80 % | 92 % |
| drift | 0,149 | 0,117 | 1,025 | 82 % | 94 % |
| ar_sdileny_kurz | 0,151 | 0,121 | 1,065 | 90 % | 95 % |

Ceny zemědělských komodit se chovají skoro jako náhodná procházka, a proto je naivní predikce těžko k poražení. Samotný AR model je na tom stejně jako naivka, model s kurzem a inflací je horší. Průměr AR modelu a naivky je o 5,3 % lepší než každý z nich zvlášť, protože oba dělají chyby v jiných letech a průměrováním se část chyb vyruší. Diebold–Mariano test kombinace vs. naivka: t = −1,97, p = 0,07. Na 14 letech je to hraniční výsledek, ne průkazný.

**Výnosy:**

| Model | MAE | bias | CRPS | CRPS vs. naivní | pokrytí 80 % | pokrytí 95 % |
|---|---|---|---|---|---|---|
| prumer3 | 0,140 | +0,041 | **0,106** | 0,823 | 81 % | 91 % |
| prumer5 | 0,144 | +0,060 | 0,107 | 0,831 | 83 % | 91 % |
| **kombinace** | **0,138** | +0,032 | 0,108 | 0,838 | 82 % | 91 % |
| trend | 0,161 | −0,012 | 0,111 | 0,862 | 81 % | 90 % |
| trend15 | 0,142 | +0,005 | 0,112 | 0,873 | 83 % | 91 % |
| trend15_pocasi | 0,142 | +0,005 | 0,112 | 0,873 | 82 % | 92 % |
| trend15_robustni | 0,149 | −0,001 | 0,117 | 0,910 | 82 % | 92 % |
| arima | 0,154 | +0,007 | 0,121 | 0,943 | 83 % | 91 % |
| naivni | 0,164 | +0,026 | 0,128 | 1,000 | 80 % | 91 % |

U výnosů se naivka porazit dá: výnos je z velké části náhodné počasí, takže „letošek“ je špatný odhad. Nejlepší tři modely jsou prakticky stejně dobré: kombinace má nejnižší MAE, tříletý průměr nejnižší CRPS. Rozdíly mezi nimi nejsou statisticky významné (kombinace vs. prumer3: p = 0,42 v CRPS, p = 0,50 v MAE). Podle pravidla z oddílu 4.3 vychází kombinace. Tříletý průměr ale držíme jako rovnocenného kandidáta a v oddílech 7 a 8 ukazujeme, co by jeho volba změnila.

ARIMA(1,1,0) s lineárním trendem je lepší než naivní predikce (MAE 0,154, CRPS 0,121), ale horší než průměr posledních tří let i kombinace. Rozdíl CRPS proti naivnímu modelu není průkazný (Diebold–Mariano p = 0,109). Přidáváme ji proto jako ověřený srovnávací model, ne jako kandidáta pro finální plán. U krátkých ročních řad jsou odhady citlivé; podrobné testy aktuálního běhu jsou v `osevni_plan_pole/vystupy_pole/detaily/testy_diebold_mariano.json`.

**Kalibrace:** 80% intervaly pokryjí 81–83 % případů, 95% intervaly jen 91 %. Na krajích jsou intervaly tedy mírně úzké: rok horší než nejhorší rok v historii chyb scénáře neobsahují. Graf `vystupy/detaily/graf_kalibrace_pit.png` ukazuje PIT histogram: kdyby bylo rozdělení ideální, sloupce by byly stejně vysoké.

---

## 5. Nejistota a scénáře 2025: ročníkový bootstrap

Bodová predikce + nejistota. Jak?

1. Vezmeme matici chyb vybraných modelů z backtestu: 22 let (2003–2024) × 40 veličin (20 cen, 20 výnosů).
2. Pro jeden scénář vylosujeme **historický rok s** a přičteme k bodové predikci **chyby všech 40 veličin z roku s**, cen i výnosů najednou.
3. Aby scénářů nebylo jen 22 různých, přidáme malý šum (vyhlazený bootstrap).

Proč celý rok najednou: zachovají se tím skutečné vazby mezi plodinami, aniž bychom museli odhadovat kovarianční matici 40 × 40 z 22 pozorování (taková matice je singulární, protože veličin je víc než let).

**Vyhlazení bez zkreslení.** Šum musí mít stejné korelace jako chyby a nesmí měnit průměr ani rozptyl. Používáme Silvermanovu variantu se zachováním rozptylu:

$x = \bar e + \dfrac{(e_s - \bar e) + b\,\varepsilon}{\sqrt{1 + b^2}}, \qquad \varepsilon \sim N(0, \Sigma), \qquad b = 0{,}9 \cdot n^{-1/5}$

Pro $n = 22$ let je $b = 0{,}9 \cdot 22^{-0{,}2} = 0{,}48$. Šum $\varepsilon$ má kovarianční matici chyb $\Sigma$, takže korelace zachovává. Dělení $\sqrt{1 + 0{,}48^2} = 1{,}11$ vrací rozptyl zpátky na původní hodnotu. Průměr zůstává $\bar e$. $\varepsilon$ generujeme jako náhodnou kombinaci centrovaných řádků matice chyb, takže to funguje i se singulární $\Sigma$.

Kontrola: korelace chyb cen pšenice a ječmene je 0,931, ve scénářích 0,934. Průměrná marže salátu je 332 tis. Kč/ha bez vyhlazení a 330 tis. Kč/ha s vyhlazením, takže vyhlazení průměr nemění. Test `test_bootstrap_zachova_prumer_a_korelace` to hlídá.

Co z chyb vyplývá:

- **Ceny obilovin se hýbou spolu**: korelace chyb pšenice–ječmen 0,93, pšenice–kukuřice 0,94. Diverzifikace mezi obilovinami cenové riziko skoro nesnižuje.
- **Cena a výnos téže plodiny**: u obilovin korelace ≈ 0 (cena se tvoří na světovém trhu, český výnos ji neovlivní), u brambor −0,37 a cibule −0,38 (lokální trh: špatná úroda zvedne cenu, přirozené zajištění).

**Dosazení, pšenice 2025:** bodová predikce ceny 5 256 Kč/t, výnosu 6 309 kg/ha, náklady $25\,000 \cdot 1{,}024 = 25\,600$ Kč/ha (náklady 2024 navýšené o inflaci 2024).
Medián scénářů: cena 5 252 Kč/t, výnos 6 441 kg/ha. Medián výnosu je vyšší než bodová predikce, protože chyby výnosu mají v průměru +3 % (model mírně podceňuje) a bootstrap tenhle bias přenese do scénářů.
Marže: průměr 8 810 Kč/ha, 10% kvantil −1 290 Kč/ha, 90% kvantil 21 130 Kč/ha, ztráta ve 14 % scénářů.

Celá tabulka je v `vystupy/predikce_2025.csv`, rozdělení marží v `graf_marze_2025.png`.

**Rajčata:** v letech 2022–2024 skočil výnos z ~35 t/ha na 233 t/ha (nejspíš přechod na skleníky, tomu odpovídají i náklady 10,7 mil. Kč/ha). Kombinace polovinou váhy bere průměr 5 let, takže predikuje jen 127 t/ha a marži −5,2 mil. Kč/ha. Rajčata proto v žádném plánu nevychází.

---

## 6. Optimalizace: mean-CVaR

### 6.1 Formulace

Proměnné: $x_i \ge 0$ hektary plodiny $i$. Zisk farmy ve scénáři $k$: $Z_k = \sum_i M_{k,i}\, x_i$.

$\max_x \; (1-\lambda)\, E[Z] + \lambda\, \text{CVaR}_{10\%}[Z]$

**CVaR 10 %** = průměrný zisk v 10 % nejhorších scénářů. Odpovídá na otázku „kolik vyděláme, když se to pokazí“. Oproti rozptylu trestá jen špatné výsledky, ne překvapení nahoru. Díky přepisu podle Rockafellara a Uryaseva (2000) je to lineární program:
$\text{CVaR}_\alpha = \max_\eta \; \eta - \tfrac{1}{\alpha K} \sum_k \max(\eta - Z_k, 0)$.

$\lambda$ je averze k riziku: $\lambda = 0$ maximalizuje jen očekávání, $\lambda = 1$ jen špatné scénáře.

### 6.2 Omezení

| Omezení | Hodnota | Zdroj |
|---|---|---|
| celková výměra | $\sum x_i = 1\,000$ ha | zadání |
| zelenina | $\le 200$ ha | zadání (20 %). Po doplnění zadání je limit parametr, viz `DOPLNENI_ZADANI.md`, oddíl 2 |
| jedna plodina | $\le 250$ ha | zadání uvádí maximální zastoupení jedné plodiny jako příklad realistického omezení |

Optimalizujeme na 5 000 scénářích a riziko plánu měříme na **jiných** 5 000 scénářích (jiný seed). Jinak by výsledky vyšly příliš optimisticky, protože optimalizace se „naučí“ konkrétní vylosované scénáře.

### 6.3 Plán 2025

(`vystupy/osevni_plan_2025.csv`, `graf_osevni_plan_2025.png`)

| Plodina (ha) | λ = 0 | λ = 0,25 | **λ = 0,5** | λ = 0,75 | λ = 1 |
|---|---|---|---|---|---|
| Ječmen | 50 | 69 | **226** | 250 | 250 |
| Kukuřice na zrno | 250 | 250 | **250** | 50 | 0 |
| Řepka | 250 | 250 | **250** | 250 | 212 |
| Brambory | 250 | 231 | **74** | 0 | 0 |
| Cukrová řepa | 0 | 0 | 0 | 250 | 250 |
| Oves | 0 | 0 | 0 | 0 | 88 |
| Zelí | 0 | 0 | **77** | 84 | 98 |
| Zelený česnek | 0 | 70 | **78** | 23 | 12 |
| Salát a čekanka | 200 | 131 | **45** | 20 | 12 |
| Cibule a šalotka | 0 | 0 | 0 | 73 | 79 |

| (mil. Kč) | λ = 0 | λ = 0,25 | **λ = 0,5** | λ = 0,75 | λ = 1 |
|---|---|---|---|---|---|
| očekávaný zisk | 82,4 | 69,5 | **44,6** | 32,3 | 28,7 |
| medián | 35,4 | 39,3 | **36,3** | 30,5 | 27,7 |
| CVaR 10 % | −107,0 | −50,5 | **−3,4** | 5,0 | 5,3 |
| P(ztráta) | 34 % | 25 % | **7 %** | 1 % | 1 % |

Čtení tabulky: při $\lambda = 0$ dá optimalizace celou zeleninovou kvótu (200 ha) na salát. Průměrná marže salátu je kolem 330 tis. Kč/ha, ale medián jen 56 tis. a ztráta nastane ve 46 % scénářů. Průměr táhne několik extrémně dobrých scénářů. Proto je očekávaný zisk 82 mil. Kč, ale medián jen 35 mil. Kč a v nejhorší desetině scénářů farma průměrně ztratí 107 mil. Kč.

Plán s $\lambda = 0{,}5$ má skoro stejný medián (36 mil. Kč), očekávaný zisk 45 mil. Kč a nejhorší desetinu scénářů zlepší ze −107 mil. na −3 mil. Kč. Pravděpodobnost ztrátového roku klesne z 34 % na 7 %.

S rostoucím $\lambda$ ubývají **brambory** (ztráta v 39 % scénářů) a **salát**, přibývá **ječmen**, **cukrová řepa** a **zelí** (nižší, ale stabilní marže). Pšenice nevychází v žádném plánu: cenu má korelovanou s ječmenem 0,93 a ječmen má vyšší i stabilnější marži. Pokud skupina chce pšenici z agronomických důvodů, stačí přidat minimální plochu jako omezení.

---

## 7. Citlivostní analýza plánu 2025

Plán s $\lambda = 0{,}5$ při změně modelu výnosů a způsobu tvorby scénářů (`vystupy/citlivost_plan_2025.csv`, `vystupy/detaily/citlivost_riziko_2025.csv`):

| Plodina (ha) | hlavní | bez vyhlazení | výnosy prumer3 | prumer3, bez vyhlazení |
|---|---|---|---|---|
| Ječmen | 226 | 230 | 250 | 250 |
| Kukuřice na zrno | 250 | 250 | 191 | 0 |
| Řepka | 250 | 250 | 250 | 250 |
| Cukrová řepa | 0 | 0 | 109 | 250 |
| Len olejný | 0 | 0 | 0 | 50 |
| Brambory | 74 | 70 | 0 | 0 |
| Zelí | 77 | 38 | 83 | 115 |
| Zelený česnek | 78 | 117 | 2 | 0 |
| Salát a čekanka | 45 | 44 | 0 | 0 |
| Cibule a šalotka | 0 | 0 | 106 | 80 |
| Okurky | 0 | 0 | 10 | 5 |
| **očekávaný zisk (mil. Kč)** | 44,6 | 47,4 | 28,4 | 26,4 |
| **CVaR 10 % (mil. Kč)** | −3,4 | 0,4 | 1,7 | 6,1 |
| **průměrná marže salátu (tis. Kč/ha)** | ≈ 330 | ≈ 330 | ≈ 0 | ≈ 0 |

Co z toho plyne:

- **Vyhlazení plán skoro nemění.** Polní část je stejná, v zelenině se přelévá pár desítek hektarů mezi zelím a česnekem.
- **Model výnosů plán mění výrazně**, hlavně u zeleniny. Příklad salátu: výnosy 2022–2024 byly 18,7, 22,5 a 25,1 t/ha. Tříletý průměr dá ~22 t/ha, kombinace ~26 t/ha. Rozdíl 15 % ve výnosu posune tržbu o ~200 tis. Kč/ha, a protože marže salátu je jen malý zbytek z tržby 1,3 mil. Kč/ha, průměrná marže klesne z ~330 tis. Kč/ha na nulu. (Průměr salátu kolísá mezi sadami scénářů o ±10 tis. Kč/ha, protože ho táhne pár extrémních scénářů.)
- **Stabilní jádro plánu** je ve všech variantách: řepka 250 ha, ječmen 226–250 ha a zelí jako hlavní zelenina. Kukuřice je ve třech ze čtyř variant.

Oba modely výnosů jsou v backtestu statisticky nerozlišitelné, takže tahle nejistota je reálná a do závěrů patří. Rozhodovací backtest (oddíl 8) ji částečně rozsuzuje.

---

## 8. Rozhodovací backtest: pomohl by model farmě?

Přesná predikce není cíl, cílem je lepší osevní plán. Proto jsme pro každý rok T = 2010–2023 udělali celý postup jen s daty do roku T:

1. **výběr modelu** pravidlem z oddílu 4.3 jen z chyb známých do roku T,
2. predikce a scénáře z chyb do roku T,
3. optimalizace,

a pak spočítali **skutečný** zisk plánu podle cen a výnosů roku T+1. Test je tak nezávislý na tom, že jsme finální model vybrali podle celého období. Zisky jsou přepočtené na ceny 2024. Historické náklady jsou náklady 2024 zpětně přepočtené přes CPI (předpoklad, jiná data nemáme).

(`vystupy/rozhodovaci_backtest_souhrn.csv`, `graf_rozhodovaci_backtest.png`, vybrané modely v `vystupy/detaily/rozhodovaci_backtest_vybery_modelu.csv`)

| Strategie (mil. Kč/rok) | průměr | medián | směr. odch. | nejhorší rok | ztrátové roky | součet 2011–2024 |
|---|---|---|---|---|---|---|
| **mean-CVaR (λ = 0,5)** | **28,8** | **26,5** | 15,2 | 5,5 | 0 | **402** |
| max. očekávání (λ = 0) | 27,6 | 21,1 | 19,2 | −4,7 | 1 | 387 |
| mean-CVaR, výnosy prumer3 | 27,2 | 23,1 | 14,7 | 10,8 | 0 | 380 |
| jen CVaR (λ = 1) | 25,7 | 20,8 | 11,6 | 9,5 | 0 | 360 |
| rovnoměrně polní plodiny | 11,3 | 10,4 | 5,6 | 2,4 | 0 | 158 |
| naivní: plán podle loňských marží | 2,8 | 18,5 | 44,1 | −112,2 | 4 | 39 |

Co z toho plyne:

- **Plán podle loňských marží je katastrofa**: bez modelu nejistoty sází celou zeleninovou kvótu na plodinu, která loni vyšla nejlíp, a ve 4 ze 14 let prodělá (2016: −112 mil. Kč). Predikce s nejistotou má pro rozhodnutí velkou hodnotu.
- **λ = 0,5 vyšlo nejlíp i v průměru**, nejen v riziku: 402 mil. Kč proti 387 mil. Kč u λ = 0, bez jediného ztrátového roku. Maximalizace očekávání v roce 2022 prodělala 4,7 mil. Kč.
- **Tříletý průměr výnosů** dává plán s menším rozptylem a lepším nejhorším rokem (10,8 vs. 5,5 mil. Kč), ale celkově o 22 mil. Kč méně (380 vs. 402). Je to jedno 14leté období, takže to je argument, ne důkaz.

---

## 9. Předpoklady a omezení (projít se skupinou)

1. **Náklady 2025** = náklady 2024 × (1 + inflace 2024) = × 1,024. V této části nejistotu nákladů nemodelujeme, řeší ji `DOPLNENI_ZADANI.md`.
2. **Národní výnos místo farmového.** Data jsou za celou ČR, jednotlivá farma má rozptyl výnosu větší. Riziko je tedy spíš podhodnocené.
3. **Očekávaná inflace** = poslední známá inflace. V roce 2022 (15 %) by to byl špatný odhad, pro rok 2025 (2,4 %) je rozumný.
4. **Cena nezávisí na tom, kolik farma vyprodukuje.** Model předpokládá, že farma je pro trh malá.
5. **Rajčata**: model zlom v produkci (skleníky) zachytí jen z poloviny.
6. **Historie chyb** má 22 let. Rok horší než nejhorší rok 2003–2024 scénáře neobsahují, proto 95% intervaly pokryjí jen 91 %.
7. **Volba modelu výnosů** (kombinace vs. tříletý průměr) mění zeleninovou část plánu. Viz oddíl 7.
8. **Výběr $\lambda = 0{,}5$** je rozhodnutí o averzi k riziku, ne výsledek výpočtu. Tabulka v oddílu 6.3 ukazuje, co se za něj platí.

---

## 10. Návrh hlavních závěrů (pro budoucí executive summary)

Závěry níže platí pro původní zadání. Závěry po doplnění zadání jsou v `DOPLNENI_ZADANI.md`, oddíl 7.

- Ceny plodin jsou skoro nepředvídatelné: nejlepší model (průměr naivní predikce a návratu reálné ceny k průměru) je jen o 5 % lepší než „příští rok jako letos“. Výnosy predikovat jde lépe (o 16–18 %).
- Roční meteorologická a makroekonomická data predikci nezlepšila, a to ani kdybychom počasí znali dopředu.
- Doporučený plán 2025 (λ = 0,5): kukuřice a řepka po 250 ha, ječmen 226 ha, brambory 74 ha, zelenina 200 ha (česnek 78, zelí 77, salát 45). Očekávaný zisk 44,6 mil. Kč, ztráta v 7 % scénářů.
- Stabilní jádro plánu nezávislé na volbě modelu: řepka, ječmen a zelí. Zbytek zeleniny závisí na modelu výnosů.
- V historickém backtestu 2011–2024 (s výběrem modelu jen z minulých dat) by doporučený postup vydělal 402 mil. Kč bez jediného ztrátového roku. Plán podle loňských marží by vydělal 39 mil. Kč a prodělal ve 4 letech.

---

## 11. Co se změnilo po review

| Připomínka | Ověření | Oprava |
|---|---|---|
| Výběr modelu podle celého období, rozhodovací backtest tedy není nezávislý | platí | výběr je pravidlo (nejnižší MAE), v rozhodovacím backtestu se aplikuje vnořeně jen na minulá data; vybírá kombinaci ve všech 14 letech |
| Šum ve vyhlazeném bootstrapu snižuje korelace (pšenice–ječmen 0,93 → 0,75) a zvyšuje průměr (salát +42 tis. Kč/ha) | platí | šum s kovariancí chyb a zpětné zmenšení rozptylu; korelace 0,931 → 0,934, salát 332 → 330 tis.; citlivostní analýza s vyhlazením i bez něj |
| Odhad počasí neodpovídá deklarované společné regresi | platí (počasí nebylo očištěno o trend) | FWL: detrend výnosů i počasí; ověřeno testem proti přímé OLS; závěr se nezměnil |
| Zařadit tříletý průměr výnosů mezi kandidáty | – | přidán do backtestu, citlivostní analýzy i rozhodovacího backtestu |
| Kapacita trhu u zeleniny | nebyla v zadání | odstraněno, zůstávají jen omezení ze zadání |

---

## Soubory

| Soubor | Obsah |
|---|---|
| `data.py` | načtení dat ze složky `data/`, ořez na ≤ 2024, marže 2024 |
| `modely.py` | 6 modelů cen, 9 modelů výnosů (včetně ARIMA) |
| `backtest.py` | rolující backtest, vyhlazený bootstrap scénářů, CRPS, pokrytí, pravidlo výběru, DM test |
| `optimalizace.py` | mean-CVaR lineární program, omezení (limit zeleniny, rozpočet), stínové ceny, plán s nejmenší největší lítostí |
| `naklady_rozpocet.py` | doplnění zadání: scénáře nákladů, limit zeleniny, rozpočet, odolný plán, stabilita |
| `spust.py` | celý řetězec včetně doplnění zadání, citlivostní analýza, tabulky a grafy |
| `test_reseni.py` | 20 testů (únik informací, marže, ARIMA, LP, bootstrap, regrese počasí, rozpočet, scénáře nákladů, čísla v textu) |

Spuštění:
```bash
pip install -r osevni_plan/requirements.txt
python3 osevni_plan/spust.py
python3 -m pytest osevni_plan/test_reseni.py -q
```
