# Metodika analýzy osevního plánu pro rok 2025

## 1. Cíl analýzy

Cílem je odhadnout ceny a hektarové výnosy 20 dostupných plodin pro rok
2025 a na jejich základě navrhnout osevní plán pro farmu o výměře 1 000 ha.
Plán má současně zohlednit očekávanou ekonomickou marži a riziko nepříznivého
vývoje.

Výpočty jsou reprodukovatelné skriptem
[`analyze_crop_plan_2025.py`](./analyze_crop_plan_2025.py). Výsledky jsou
uloženy v souborech [`predikce_2025.csv`](./predikce_2025.csv),
[`osevni_plan_2025.csv`](./osevni_plan_2025.csv) a
[`citlivost_osevniho_planu_2025.csv`](./citlivost_osevniho_planu_2025.csv).

## 2. Datové zdroje a jednotky

Použity jsou:

- `plodiny.xlsx` – názvy plodin, CPC kódy, produkční skupiny a referenční
  náklady na hektar pro rok 2024,
- `plodiny_ceny.csv` – roční ceny zemědělských výrobců v Kč/t,
- `plodiny_vynosy.csv` – roční hektarové výnosy v kg/ha.

Historické řady obsahují roky 1993–2024. Data o makroekonomice nejsou
automaticky použita, protože vstupní XLSX je široká tabulka s nejednoznačně
identifikovatelnými názvy ukazatelů. Počasí není použito jako vysvětlující
proměnná, protože pro rok 2025 by před začátkem sezóny nebyly známé jeho
skutečné hodnoty. Tím se předchází úniku budoucí informace do predikce.

Při propojování souborů se názvy normalizují: převádějí se na malá písmena,
odstraňuje se diakritika, závorkové doplňky a nadbytečné znaky. Tím se například
propojí názvy `Maize (corn)` a `Maize corn` bez ručního přepisování zdrojových
dat.

## 3. Referenční marže

Pro každou plodinu se používá:

```text
tržba na ha = cena [Kč/t] × výnos [kg/ha] / 1 000
marže na ha = tržba na ha − náklady [Kč/ha]
```

Dělení 1 000 je nutné proto, že cena je v Kč/t, zatímco výnos je v kg/ha.
Náklady pro predikční rok 2025 nejsou k dispozici, proto se konzervativně
používají referenční náklady z roku 2024. Výsledná marže je tedy ekonomická
marže vůči těmto referenčním nákladům, nikoli úplný účetní zisk farmy.

## 4. Ekonometrická predikce

### 4.1 Naivní model

Naivní predikce předpokládá, že nejlepší odhad příští hodnoty je poslední
pozorovaná hodnota:

```text
y_hat_(t+1) = y_t
```

Jde o důležitou základní metodu. Složitější model má smysl pouze tehdy, pokud
prokazatelně předčí tuto baseline. Naivní model je vhodný zejména tehdy, když
je řada silně volatilní a dlouhodobý trend by vedl k extrapolaci mimo realistický
rozsah.

### 4.2 Lineární trend

Trendový model odhaduje vztah:

```text
y_t = alpha + beta × t + epsilon_t
```

Parametr `beta` zachycuje průměrnou změnu hodnoty v čase. Odhad pro rok 2025
je extrapolací regresní přímky za poslední známé období. Model je jednoduchý,
interpretovatelný a při 32 ročních pozorováních méně náchylný k přeučení než
komplexní ARIMA nebo regresní model s mnoha exogenními proměnnými.

Trend však neznamená kauzální vztah. Neříká například, že čas sám o sobě
způsobuje růst ceny. Zachycuje pouze průměrný historický pohyb a může selhat
při strukturální změně trhu.

### 4.3 Holtovo exponenciální vyrovnávání

Holtova metoda je exponenciálně vážený model úrovně a trendu. Novější
pozorování dostávají vyšší váhu než starší, takže model rychleji reaguje na
změnu trhu než obyčejná regrese přes celý historický vzorek. V analýze jsou
porovnány dvě varianty:

- **Holt** – aditivní trend pokračuje bez omezení,
- **Holt s tlumeným trendem** – trend se při delší extrapolaci postupně
  zmenšuje.

Tlumený trend je praktická alternativa k lineární regresi: zachová informaci o
směru vývoje, ale nepředpokládá, že stejná historická rychlost růstu bude trvat
navždy. Nevýhodou je, že vyhlazovací parametry jsou odhadovány z krátké řady a
výsledek může záviset na posledních několika pozorováních.

### 4.4 ARIMA benchmark

ARIMA (autoregressive integrated moving average) modeluje vlastní dynamiku
časové řady pomocí tří částí:

- **AR (`p`)** – závislost na vlastních minulých hodnotách,
- **I (`d`)** – počet diferencování, které odstraňuje trend nebo nestacionaritu,
- **MA (`q`)** – závislost na minulých náhodných chybách.

V implementaci se porovnávají jednoduché specifikace `ARIMA(1,1,0)`,
`ARIMA(0,1,1)`, `ARIMA(1,0,0)` a nově také `ARIMA(1,1,1)`. Nejde o
automatický výběr desítek parametrů,
protože 32 ročních pozorování je relativně malý vzorek. ARIMA se odhaduje
pouze z minulých hodnot a nepoužívá budoucí počasí ani rok 2025.

ARIMA je vhodná tam, kde má řada vlastní časovou setrvačnost nebo korelované
meziroční změny. Její nevýhodou je citlivost na specifikaci, strukturální
zlomy a krátké časové řady. Proto je v analýze pouze jedním z kandidátů, nikoli
automaticky preferovanou metodou.

### 4.5 Expanding-window backtesting

Modely (naivní, trendový, dvě Holtovy varianty a tři ARIMA specifikace) se
nevybírají podle R²
z celého vzorku. Pro každý rok od roku 2003 se model odhadne pouze z předchozích
let a následně predikuje další skutečný rok.
Tím vznikne časově korektní sada predikčních chyb:

```text
MAE = průměr |skutečná hodnota − predikce|
```

Použití MAE (mean absolute error) je praktické, protože je ve stejných
jednotkách jako predikovaná veličina a není tak citlivé na jednotlivé extrémní
chyby jako kvadratická chyba. Vybere se metoda s nižší průměrnou MAE. V každém řádku souboru
`predikce_2025.csv` je v polích `Metoda_ceny` a `Metoda_vynosu` uvedena vybraná
metoda.

Tento postup respektuje časovou posloupnost a nepoužívá náhodné rozdělení na
trénovací a testovací data, které by u časových řad mohlo do tréninku
nepřípustně přimíchat budoucí informace.

## 5. Nejistota a scénáře

Bodová predikce sama o sobě není dostačující pro rozhodování o osevním plánu.
Pro každou řadu se proto určí odhad chyby a vytvoří se přibližný interval:

```text
dolní hranice = max(predikce − 1,96 × směrodatná chyba, predikce × 5 %, 0)
horní hranice = predikce + 1,96 × směrodatná chyba
```

U trendového modelu se chyba odvozuje z reziduí trendové regrese a z
backtestovací MAE. U naivního modelu se používají meziroční změny. Pět
procentní minimální šířka chrání před nerealisticky úzkým intervalem v řadách,
kde byla poslední hodnota shodou okolností stabilní.

Intervaly jsou orientační a nelze je interpretovat jako přesné statistické
konfidenční intervaly. Nezachycují plně korelace mezi plodinami ani možný
společný šok počasí, energií nebo trhu.

Z intervalů se počítají tři jednoduché scénáře:

- **základní scénář** – bodová predikce ceny a výnosu,
- **nepříznivý scénář** – dolní hranice ceny a výnosu,
- **příznivý scénář** – horní hranice ceny a výnosu.

Toto je konzervativní scénářová aproximace. Není to Monte Carlo simulace
společného rozdělení rizik, protože dostupný postup neodhaduje korelační
strukturu mezi cenami a výnosy.

## 6. Optimalizační model

Rozhodovací proměnná `x_i` znamená počet hektarů přidělených plodině `i`.
Použitá omezení jsou:

```text
Σ x_i = 1 000
x_i ≥ 0
Σ x_i pro zeleninové plodiny ≤ 200
```

Optimalizuje se rizikově upravené skóre:

```text
max Σ x_i × (E[M_i] − λ × D_i)
```

`E[M_i]` je očekávaná marže na hektar a `D_i` je downside riziko:

```text
D_i = max(E[M_i] − M_i,nepříznivý, 0)
```

Parametr `lambda` (`λ`) vyjadřuje averzi k riziku. Při `λ = 0` se maximalizuje
pouze očekávaná marže. Vyšší hodnota více penalizuje plodiny, u kterých může
nepříznivý scénář výrazně snížit očekávaný výsledek. Protože je účelová funkce
lineární a omezení jsou lineární, používá se lineární programování (`scipy
.optimize.linprog`).

Ve výchozím výpočtu je použito `λ = 0,5`. Citlivost se počítá pro
`λ = 0`, `0,25`, `0,5` a `1`. Pokud se plán mezi hodnotami výrazně mění,
výsledek je citlivý na preferenci vedení vůči riziku a neměl by být prezentován
jako jediná přesná varianta.

## 7. Interpretace výsledku

Výchozí řešení bez limitu maximálního podílu plodiny přiděluje 800 ha řepce a
200 ha zelí. To není chyba optimalizačního solveru; je to přímý důsledek toho,
že model obsahuje pouze limit zeleniny a žádný maximální podíl jedné plodiny,
osevní postup, agronomickou diverzifikaci ani omezení odbytu. V předchozí
specifikaci bez ARIMA vycházela celá plocha řepky; změna je způsobena novými
predikcemi a nikoli ruční úpravou plánu.

Jako alternativu skript počítá diverzifikovaný plán v souboru
`osevni_plan_2025_diverzifikovany.csv`. V něm je maximální plocha jedné
plodiny omezena na 25 % farmy, tedy 250 ha. Toto omezení není vydáváno za
empiricky odhadnutý agronomický fakt; jde o transparentní scénář, který
ukazuje dopad požadavku, aby výsledek nebyl koncentrován v jediné plodině.
Při 1 000 ha znamená 25% limit, že plán musí použít nejméně čtyři plodiny.

### Robustní scénářová optimalizace

Další alternativou je robustní lineární programování. Místo optimalizace pouze
základní marže hledá plán, který maximalizuje nejhorší celkovou marži přes tři
explicitní scénáře:

- nepříznivý: dolní cena a dolní výnos,
- základní: bodová predikce,
- příznivý: horní cena a horní výnos.

Formálně se maximalizuje pomocná proměnná `z`:

```text
max z
z ≤ Σ x_i × M_i,s pro každý scénář s
```

Současně se zachovává limit 200 ha zeleniny a v robustní variantě také
maximálně 250 ha jedné plodiny. Výstup je uložen v
`osevni_plan_2025_robustni.csv`. Robustní výstup nyní používá přísnější limit
200 ha na jednu plodinu (20 % farmy), takže plán musí obsahovat alespoň pět
plodin. Tento postup je transparentnější než
jediné odečtení rizikové penalizace, ale může být konzervativní: výsledek je
citlivý na šířku zvolených intervalů a nepracuje s pravděpodobností scénářů.

### Které další metody nebyly použity

- **SARIMA** není vhodná jako hlavní rozšíření: roční data nemají dost
  pozorování pro spolehlivý odhad sezónní komponenty.
- **ARIMAX** a regresní modely s počasím/makrem vyžadují jednoznačně připravené
  exogenní ukazatele dostupné v okamžiku predikce. Dodaný makroekonomický XLSX
  je široký a jeho proměnné nejsou spolehlivě identifikované.
- **VAR/VECM** by odhadoval mnoho parametrů současně pro 20 plodin, což je při
  32 ročních pozorováních nepřiměřené.
- **GARCH** potřebuje hustší řadu pro modelování volatility; 32 ročních
  pozorování je pro tento účel příliš málo.
- **Random forest/gradient boosting** by zde měl více parametrů než
  informací, zejména bez validovaných exogenních proměnných.
- **CVaR a Monte Carlo** by byly vhodné jako další krok, pokud budou k dispozici
  delší řady a společné rozdělení cen, výnosů a počasí. Současná robustní
  scénářová LP je interpretovatelná alternativa bez předstírání přesných
  pravděpodobností.

Výsledek proto znamená:

> Za zadaných omezení a podle použitých predikcí je nejvýhodnější kombinace
> řepky a zelí podle rizikově upravené marže.

Neznamená to, že je 1 000 ha řepky prakticky doporučitelný osevní postup.
Pro provozní doporučení by bylo nutné doplnit pouze ekonomicky nebo agronomicky
obhájená omezení, například maximální podíl jedné plodiny, minimální
diverzifikaci, osevní postup, kapacitu mechanizace a odbytové limity.

## 8. Hlavní omezení

1. Historie obsahuje pouze 32 ročních pozorování; složité modely by byly
   náchylné k přeučení.
2. Predikce cen a výnosů jsou modelovány odděleně; není odhadnuta jejich
   společná korelace.
3. Náklady 2025 jsou nahrazeny náklady 2024, bez inflační úpravy.
4. Intervaly nejistoty jsou praktické odhady, nikoli plně specifikované
   pravděpodobnostní intervaly.
5. Limit 25 % v diverzifikovaném scénáři je ilustrativní citlivostní
   předpoklad, nikoli odhad optimálního agronomického limitu.
6. Model nezahrnuje dotace, fixní náklady, kapacitu práce, osevní postup,
   pojištění ani omezení odbytu.
7. Historický vztah nemusí platit po strukturální změně trhu.

Výsledky je proto vhodné používat jako reprodukovatelný analytický základ a
scénářovou podporu rozhodování, nikoli jako jistou předpověď skutečné marže.
