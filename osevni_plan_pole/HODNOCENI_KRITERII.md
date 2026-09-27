# Posouzení požadavků kurzu

Tento přehled posuzuje důkazy v řešení `osevni_plan_pole/` spolu s navazující analytickou částí `osevni_plan/`. Nejde o záruku hodnocení vyučujícím; ukazuje, co lze z výpočtů obhájit a co zůstává mimo model.

**Celkový verdikt:** matematický model, rozhodovací optimalizace a reprodukovatelný výpočet jsou dobře doložené. Statistická a ekonometrická část je v tomto samostatném běhu převzatá z hlavního řešení a je teď exportovaná i do vlastních výstupů. Pokročilá operační optimalizace je zastoupena MILP s mean-CVaR; pokročilá kauzální ekonometrie ani ekologická a sociální udržitelnost z dostupných dat vyhodnoceny nejsou. Tyto limity je potřeba při prezentaci říct nahlas.

Stavy: **splněno** = výpočet a výstup poskytují přímý důkaz; **částečně** = je doložená část kompetence, ale zůstává pojmenovaná mezera.

| Požadavek | Stav | Důkaz a hranice tvrzení |
|---|---|---|
| Statistické metody a vztahy mezi proměnnými | Splněno v rámci celého řešení | Rolující backtest predikuje roky 2003–2024 bez úniku budoucnosti; MAE, bias, CRPS, intervalové pokrytí a Diebold–Mariano testy porovnávají modely. Pole-běh ukládá oba souhrny, DM testy a korelace chyb ceny/výnosu téže plodiny. ARIMA dosahuje MAE 0,154 a CRPS 0,121 proti naivním 0,164 a 0,128; DM test rozdílu CRPS dává p = 0,109, takže zlepšení není potvrzené na 5% hladině. Korelace popisuje souběh, nikoli příčinný vliv. |
| Optimalizace jako podpora rozhodování | Splněno | MILP vybírá hektary plodin a celočíselné počty polí; více polí může mít stejnou plodinu. Plány pro různé váhy rizika jsou vyhodnoceny na oddělených testovacích scénářích. |
| Matematický model a analytický postup pro ekonomický problém | Splněno | Marže v každém scénáři je cena krát výnos minus náklad. Cíl je kompromis očekávaného zisku a CVaR nejhorších 10 % výsledků. Omezení zahrnují plochu farmy, zeleninu, maximum plodiny, plochu pole a meze. Rovnice a předpoklady jsou v `VYSVETLENI.md`. |
| Kritické vyhodnocení a identifikace slabin | Splněno jako dokumentace; model má vědomá omezení | Citlivost porovnává 20/2, 30/1, 30/2 a 40/2 ha. Ziskové metriky zůstávají podobné, ale počet polí a produkční plocha se mění. Model nezná geometrii parcel, půdní kvalitu, vzdálenost, rotaci plodin ani skutečné náklady na údržbu mezí. |
| Srozumitelná prezentace a praktická doporučení | Splněno | CSV poskytují agregovaný plán, detailní rozpis polí, rizikové metriky i citlivost. Doporučení: `lambda=0,5` používat jako kompromisní scénář, nikoli jako automatický příkaz k výsadbě; před realizací ověřit konkrétní parcely, osevní postup a kapacity podniku. |
| Obhajoba postupu, software, předpoklady, robustnost a alternativy | Splněno s výhradou prostorových dat | Model používá Python, pandas/NumPy, SciPy `milp` (MILP řešič HiGHS) a navazující predikční modely. Robustnost se testuje změnou limitu pole a výměry mezí i vahou rizika. Alternativou je původní agregovaný LP bez polí; přesnější alternativou by bylo MILP s konkrétní sítí parcel a jejich sousedností, pro které ale nejsou vstupní data. |
| Etika, transparentnost a reprodukovatelnost | Splněno pro reprodukovatelnost; zdroje je třeba citovat při odevzdání | Vstupy jsou agregované po plodinách a rocích, ne osobní údaje. Datový horizont, modely, počty scénářů, seedy a verze Pythonu/knihoven se ukládají do `vystupy_pole/metodika_behu.json`. Oddělené optimalizační a testovací seedy omezují optimismus. V odevzdané práci je stále nutné uvést původ, licenci a datum získání každého datového souboru. |
| Ekonomická a společenská udržitelnost | Částečně | Ekonomická odolnost je měřena očekávaným ziskem, mediánem, CVaR10 a pravděpodobností ztráty. Environmentální dopad mezí může být kladný, ale není oceněn; model neměří biodiverzitu, erozi, vodu, emise, zaměstnanost ani sociální dopady. Nelze proto tvrdit, že nejziskovější plán je celkově udržitelný. |
| Kombinace matematiky, pravděpodobnosti, statistiky, optimalizace a programování | Splněno | Logaritmické predikce a rolling backtest vytvářejí rozdělení chyb, bootstrap z nich scénáře, pravděpodobnostní metriky hodnotí predikce a MILP volí osevní plán. Python skript celý postup reprodukuje. |
| Pokročilá ekonometrie a operační výzkum | Částečně | Operační výzkum je zastoupen MILP a mean-CVaR. Ekonometrická část obsahuje časové řady včetně ARIMA a testy predikční přesnosti, ale ročních pozorování je málo a modely nejsou kauzální. ARIMA je lepší než naivní benchmark podle bodových metrik, ale rozdíl není statisticky průkazný; nevybírá se jako výsledný model. Výsledek proto nepředstavuje důkaz pokročilé strukturální ani kauzální ekonometrie. |

## Výsledek citlivosti předpokladů

Pro doporučené `lambda=0,5` a stejnou dvojici optimalizačních/testovacích scénářů vyšly tyto hodnoty:

| Produkční plocha pole / mez (ha) | Počet polí | Produkční plocha (ha) | Očekávaný zisk (mil. Kč) | Medián (mil. Kč) | CVaR10 (mil. Kč) | P(ztráta) |
|---|---:|---:|---:|---:|---:|---:|
| 20 / 2 | 47 | 906 | 43,43 | 35,28 | −3,74 | 6,8 % |
| 30 / 1 | 35 | 965 | 44,18 | 35,90 | −3,57 | 6,6 % |
| 30 / 2 | 33 | 934 | 43,72 | 35,47 | −3,63 | 6,7 % |
| 40 / 2 | 25 | 950 | 43,93 | 35,67 | −3,58 | 6,6 % |

Ekonomické rizikové ukazatele jsou v těchto čtyřech testovaných variantách blízké. Rozpis půdy ani počet polí však není neměnný. To podporuje použití plánu jako rozhodovacího scénáře, nikoli jako přesného parcelního plánu.

## Kritická omezení modelu

- PDF neurčuje velikost polí ani šířku mezí. Hodnoty 20–40 ha a 1–2 ha jsou scénáře, ne zjištěné parametry farmy.
- „2 ha mez na pole“ je modelována jako pevná plocha za parcelu. Skutečná plocha meze závisí na obvodu a tvaru parcely; bez mapových dat ji nelze odhadnout.
- Detailní CSV přiděluje plodinu abstraktnímu číslu pole. Neobsahuje polohu, sousedství, půdní vlastnosti, přístup ani střídání plodin.
- Předpokládají se společné ceny a hektarové marže pro všechny parcely dané plodiny. Prostorová variabilita výnosu a půdy chybí.
- Model optimalizuje marži po odečtení produkčních nákladů, ale neoceňuje práci, investice do závlahy, skladování, logistiku, údržbu mezí ani externality.
- Historické roční řady jsou krátké a mohou obsahovat strukturální zlomy. Výsledky nejsou kauzální predikcí ani garancí zisku.
- Čtyři citlivostní scénáře pokrývají jen malou část možných parametrů; neprokazují robustnost vůči změně cenových/ výnosových modelů, nákladů, plodinových kvót ani šoků mimo historickou zkušenost.
- Seedy jsou pevné a zajišťují reprodukovatelný konkrétní běh, nikoli jistotu, že stejné optimální řešení vznikne ve všech verzích numerického řešiče při více rovnocenných optimech.

## Doporučení pro obhajobu

1. Prezentovat agregovaný plán a pole-variantu vedle sebe; rozdíl vysvětlit zejména ztrátou půdy na meze a celočíselným počtem polí.
2. Jako základ uvést `lambda=0,5`; ukázat, že testovaná citlivost 20/2 až 40/2 mění očekávaný zisk jen přibližně o 0,75 mil. Kč, avšak počet polí z 25 na 47.
3. Výslovně označit 30 ha a 2 ha jako pracovní předpoklad, nikoli jako údaj ze zadání.
4. Praktickou realizaci podmínit kontrolou mapy parcel, půdy, rotace plodin a provozních nákladů. Před tvrzením o udržitelnosti doplnit environmentální a sociální ukazatele.
