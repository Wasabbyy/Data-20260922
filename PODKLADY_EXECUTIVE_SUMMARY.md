# Podklady pro executive summary: doplnění zadání

Tento soubor je určený pro toho, kdo píše executive summary a prezentaci k doplnění zadání (`zadani/osevni_plan_2.pdf`). Stačí ho přečíst celý, žádný kód k tomu není potřeba. Je seřazený podle osnovy našeho prvního executive summary (`Odevzdání/osevni_plan.tex`).

Čísla jsou vygenerovaná z výstupů v `osevni_plan/vystupy/doplneni/`. Podrobné odvození s dosazením do vzorců je v [`osevni_plan/DOPLNENI_ZADANI.md`](osevni_plan/DOPLNENI_ZADANI.md), první část projektu ve [`osevni_plan/VYSVETLENI.md`](osevni_plan/VYSVETLENI.md).

> **Stav:** výpočty jsou hotové a otestované. Doporučení odolného plánu a formulace v oddílu 9 jsou návrh, který má skupina projít.

## 1. Co po nás doplnění zadání chce

| Zadání (slide) | Úkol | Co jsme udělali | Kde je detail |
|---|---|---|---|
| Náklady jsou hrubý odhad a mohou růst rychleji než ceny (slide 2) | Vytvořit několik scénářů nákladů pro rok 2025 a posoudit, jak se při nich mění doporučený plán | 4 scénáře růstu nákladů podle historických let, citlivost na chybu odhadu od −20 % do +40 %, zvlášť polní plodiny a zelenina | `DOPLNENI_ZADANI.md`, oddíl 1 |
| Limit 20 % pro zeleninu je hrubý odhad (slide 3) | Zohlednit nejistou kapacitu zeleniny | Limit je v modelu parametr, plán pro limit 0 až 40 % rozlohy, cena jednoho hektaru limitu | oddíl 2 |
| Rozpočet na rok 2025 není známý (slide 3) | Zohlednit nejistý rozpočet, navrhnout úpravy modelu | Nové omezení rozpočtu v modelu, plán pro každou výši rozpočtu, varianta s rezervou | oddíl 3 |
| (slide 3) | Posoudit stabilitu doporučeného plánu | Odolný plán, společné hektary mezi plány, jádro plodin | oddíly 4 a 5 |

## 2. Hlavní sdělení ve čtyřech větách

1. Původní plán je citlivý na náklady. Kdyby náklady vzrostly jako v roce 2022 a ceny plodin ne, skončil by ztrátou ve 25,9 % scénářů místo 6,5 %.
2. Doporučujeme proto odolný plán. Má o 8,7 mil. Kč nižší očekávaný zisk, ale stojí o 47 mil. Kč méně a ztrátu má ve 2,3 % scénářů.
3. O ploše zeleniny nerozhoduje model, ale farmářův odhad kapacity a rozpočet. Model vždy využije všechnu zeleninu, kterou smí.
4. Stabilní část plánu je řepka, ječmen a kukuřice po 250 ha. Nestabilní je zelenina a brambory.

## 3. Výsledky k použití

### 3.1 Původní a odolný plán

| Plodina | původní plán (ha) | odolný plán (ha) |
|---|---|---|
| Ječmen | 226 | **250** |
| Kukuřice na zrno | 250 | **250** |
| Řepka | 250 | **250** |
| Cukrová řepa | 0 | **50** |
| Brambory | 74 | **0** |
| Zelí | 77 | **54** |
| Zelený česnek | 78 | **31** |
| Salát a čekanka | 45 | **26** |
| Cibule a šalotka | 0 | **89** |

|  | původní plán | odolný plán |
|---|---|---|
| náklady plánu (mil. Kč) | 156,9 | 109,8 |
| potřebný rozpočet při růstu nákladů jako 2022 (mil. Kč) | 176,4 | 123,4 |
| očekávaný zisk, základní náklady (mil. Kč) | 44,6 | 35,9 |
| CVaR 10 %, základní náklady (mil. Kč) | −3,4 | 2,9 |
| pravděpodobnost ztráty, základní náklady | 6,5 % | 2,3 % |
| očekávaný zisk, růst nákladů jako 2022 (mil. Kč) | 25,1 | 22,3 |
| CVaR 10 %, růst nákladů jako 2022 (mil. Kč) | −22,9 | −10,7 |
| pravděpodobnost ztráty, růst nákladů jako 2022 | 25,9 % | 15,7 % |
| největší lítost přes scénáře růstu nákladů (mil. Kč) | 5,65 | 1,15 |

Jak tabulku číst: odolný plán nechává polní jádro beze změny, vypouští brambory a v zelenině přesouvá plochu od česneku a salátu k cibuli. Cibule má ze zeleniny nejnižší náklady na hektar (235 520 Kč, salát 1 263 616 Kč), takže zdražení vstupů snáší nejlépe.

### 3.2 Scénáře nákladů

Základ jsou náklady 2024 zvýšené o inflaci roku 2024 (2,4 %). Další tři scénáře říkají: náklady porostou tolik jako v daném historickém roce, ceny plodin zůstanou podle našeho modelu. Násobek k říká, kolikrát jsou náklady vyšší než v základu. Pro rok 2022 je to $1{,}151 / 1{,}024 = 1,124$, tedy náklady o 12,4 % vyšší než v základu.

| Scénář nákladů | násobek k | původní plán: P(ztráta) | odolný plán: P(ztráta) | kolik ha původního plánu by se mělo změnit |
|---|---|---|---|---|
| základ (růst 2,4 %) | 1,000 | 6,5 % | 2,3 % | 0 |
| růst jako 2008 (6,3 %) | 1,038 | 11,4 % | 5,3 % | 149 |
| růst jako 2023 (10,7 %) | 1,081 | 18,1 % | 10,0 % | 189 |
| růst jako 2022 (15,1 %) | 1,124 | 25,9 % | 15,7 % | 232 |

Další čísla, která se dají použít:

- Očekávaný zisk původního plánu je nulový, když jsou náklady o 28 % vyšší než odhad (tržba 201,5 mil. Kč proti nákladům 156,9 mil. Kč).
- Rozhodují náklady zeleniny. Zdražení jen zeleniny o 20 % sníží její plochu v plánu z 200 na 40 ha. Stejné zdražení polních plodin plochu zeleniny nezmění.
- Kdyby byly náklady naopak o 10 % nižší než odhad, vyplatí se víc brambor a cukrové řepy a s původním plánem zůstane společných 562 ha z 1 000.

Graf: `osevni_plan/vystupy/doplneni/graf_naklady.png` (vlevo zisk podle výše nákladů, vpravo plán pro každou výši nákladů) a `graf_naklady_pole_zelenina.png`.

### 3.3 Limit zeleniny

- Limit je aktivní v celém rozsahu 0 až 400 ha. Kolik zeleniny limit povolí, tolik jí v plánu je.
- Jeden hektar limitu navíc zvedne hodnotu plánu o 59 tis. Kč (stínová cena při 200 ha).
- Nad 200 ha přidá každých 50 ha zeleniny 7,4 mil. Kč očekávaného zisku, zhorší nejhorší desetinu scénářů o 1,4 mil. Kč a zvedne náklady plánu o 29,1 mil. Kč.
- Bez zeleniny (limit 0 ha) je očekávaný zisk 11,1 mil. Kč, při 200 ha 44,6 mil. Kč a při 400 ha 74,3 mil. Kč.

Odolný plán pro jiné limity zeleniny:

| Limit zeleniny (ha) | 100 | 150 | 200 | 250 | 300 |
|---|---|---|---|---|---|
| zelenina celkem (ha) | 100 | 150 | 200 | 250 | 300 |
| náklady plánu (mil. Kč) | 76,7 | 93,2 | 109,8 | 126,4 | 143,8 |
| potřebný rozpočet při růstu nákladů jako 2022 (mil. Kč) | 86,2 | 104,8 | 123,4 | 142,1 | 161,6 |
| očekávaný zisk, základní náklady (mil. Kč) | 24,6 | 30,3 | 35,9 | 41,6 | 47,0 |
| P(ztráta), základní náklady | 2,2 % | 2,3 % | 2,3 % | 2,4 % | 2,4 % |

Skladba po plodinách je v `DOPLNENI_ZADANI.md`, oddíl 4.

### 3.4 Rozpočet

- Původní plán stojí 156,9 mil. Kč: zelenina (200 ha) 119,8 mil. Kč, polní plodiny (800 ha) 37,1 mil. Kč. Rozpočet proto omezuje skoro jen zeleninu.
- Odolný plán stojí 109,8 mil. Kč, při růstu nákladů jako 2022 123,4 mil. Kč.
- Pod 18,7 mil. Kč nejde oset celých 1 000 ha ani nejlevnějšími plodinami.
- Plán pro každou výši rozpočtu (optimalizovaný při základních nákladech):

| Rozpočet (mil. Kč) | 40 | 60 | 80 | 100 | 120 | 140 | 160 |
|---|---|---|---|---|---|---|---|
| zelenina v plánu (ha) | 72 | 139 | 200 | 200 | 200 | 200 | 200 |
| očekávaný zisk (mil. Kč) | 15,3 | 23,3 | 30,4 | 34,1 | 38,0 | 41,5 | 44,6 |
| P(ztráta) | 2,4 % | 2,5 % | 2,5 % | 2,0 % | 3,0 % | 5,0 % | 6,5 % |
| cena opatrnosti (mil. Kč) | 12,2 | 8,0 | 3,9 | 1,8 | 0,7 | 0,2 | 0,0 |

Cena opatrnosti říká, o kolik je plán s daným rozpočtem horší než původní plán bez omezení (v hodnotě plánu, viz slovníček). Při 100 mil. Kč je to jen 1,8 mil. Kč, protože menší rozpočet zároveň snižuje riziko. Pod 80 mil. Kč už rozpočet nestačí na 200 ha zeleniny.

Graf: `osevni_plan/vystupy/doplneni/graf_limit_zeleniny_rozpocet.png`.

### 3.5 Stabilita

- Řepka 250 ha je ve všech spočítaných plánech.
- Ječmen a kukuřice po 226 až 250 ha drží ve všech čtyřech scénářích růstu nákladů.
- Mezi původním plánem a plánem pro růst nákladů jako 2022 je společných 768 ha z 1 000.
- Zelenina a brambory jsou nestabilní část: plochu zeleniny určuje limit a rozpočet, skladbu náklady.

## 4. Metody jednou větou

| Co | Jak | Proč |
|---|---|---|
| Scénáře nákladů | náklady × násobek k, ceny a výnosy beze změny | rozdíl mezi plány jde jen za náklady |
| Růst nákladů | k = (1 + inflace historického roku) / (1 + inflace 2024), roky 2008, 2023 a 2022 | zadání číslo neuvádí, bereme tři roky s nejvyšší inflací od roku 2000 |
| Chyba odhadu | citlivost pro k od 0,80 do 1,40 | velikost chyby neznáme, hledáme, kde se plán láme |
| Limit zeleniny | parametr modelu, plán pro 0 až 400 ha, stínová cena | limit je odhad na obě strany |
| Rozpočet | nové lineární omezení: součet nákladů plodin × hektary ≤ rozpočet | úloha zůstává lineární program |
| Odolný plán | minimalizace největší lítosti přes scénáře nákladů (lineární program) | nepotřebuje pravděpodobnosti scénářů, které neznáme |
| Stabilita | společné hektary dvou plánů a jádro plodin | jednoduché číslo, kolik hektarů se mezi plány přesune |

Model z první části se jinak nezměnil: stejné predikce, stejných 5 000 scénářů, stejná účelová funkce mean-CVaR s $\lambda = 0{,}5$, vyhodnocení na nezávislé sadě scénářů.

## 5. Rozhodnutí, která jsme udělali, a proč

1. **Scénáře růstu nákladů podle skutečných let, ne podle vlastních čísel.** Zadání říká jen, že náklady mohou růst rychleji než ceny. Vlastní hodnotu (například +10 %) bychom neuměli obhájit. Roky 2008 (6,3 %), 2023 (10,7 %) a 2022 (15,1 %) jsou zažitá situace.
2. **Ve scénářích rostou jen náklady, ceny ne.** Přesně toho se farmář bojí. Je to přísný předpoklad: v roce 2022 vzrostly ceny všech 20 plodin (medián +28 %), v roce 2023 už jen 8 z 20 (medián −2 %) při inflaci 10,7 %. Scénář tedy odpovídá spíš roku 2023.
3. **Chyba farmářova odhadu jako citlivost, ne jako scénář.** Nevíme, jak velká chyba je. Místo jednoho vymyšleného čísla ukazujeme celý rozsah a bod, kde se plán mění.
4. **Jeden násobek nákladů, zvlášť pro polní plodiny a zeleninu.** Pokud chyba odhadu i rychlejší růst platí pro všechny plodiny stejně, jde matematicky o jeden násobek. Rozdíl dává smysl sledovat jen mezi skupinami plodin a ten vyšel jako podstatný.
5. **Limit zeleniny a rozpočet neodhadujeme, dáváme plán pro každou hodnotu.** Jsou to tvrdé horní meze. Plán pro 200 ha zeleniny nejde realizovat, když kapacita bude 150 ha. Zadání neříká, kdy se farmář rozpočet dozví, proto tabulka.
6. **Rozpočet s rezervou.** Rozpočet se počítá z nákladů, které jsou samy nejisté. Proto u doporučeného plánu uvádíme i náklady při růstu jako 2022.
7. **Odolný plán přes největší lítost.** Plán optimální jen pro nejhorší scénář by ignoroval ostatní. Průměr přes scénáře by potřeboval jejich pravděpodobnosti. Největší lítost nepotřebuje ani jedno a je to stále lineární program.
8. **Averzi k riziku ($\lambda = 0{,}5$) a scénáře tržeb jsme nechali stejné jako v první části.** Původní a nové plány jsou tak přímo srovnatelné.
9. **Odolný plán chrání jen proti růstu nákladů.** Proti nižšímu limitu zeleniny nebo rozpočtu jeden pevný plán chránit nejde (viz bod 5), tam je odpovědí tabulka.

## 6. Limity řešení

- Růst nákladů bereme z obecné inflace (CPI). Náklady v zemědělství se mohou vyvíjet jinak a řadu nákladů farmy nemáme.
- Ve scénářích se ceny plodin nepřizpůsobí růstu nákladů. Skutečný dopad zdražení může být menší.
- Stejný násobek nákladů pro všechny polní plodiny a pro všechnu zeleninu. Chybu odhadu u jedné konkrétní plodiny nemodelujeme.
- Limit zeleniny i rozpočet jsou tvrdé meze a celá rozloha se musí oset. Model nepřipouští úhor ani úvěr.
- Odolný plán závisí na zvolené sadě scénářů nákladů. Kdyby byly náklady nižší než odhad, je lepší původní plán.
- Limity z první části platí dál: národní výnosy místo farmových, krátké roční řady, citlivost zeleniny na model výnosů.

## 7. Doporučený další postup

- Zpřesnit náklady zeleniny. Má to největší vliv na plán (viz 3.2).
- Zjistit skutečnou kapacitu zeleniny a čím je daná. Hektar kapacity navíc má hodnotu kolem 59 tis. Kč.
- Až bude známý rozpočet, vybrat plán z tabulky v 3.4 nebo model přepočítat s přesnou hodnotou (parametr `rozpocet`).
- Pokud budou data, modelovat náklady a ceny společně, aby scénář růstu nákladů nebyl jen jednostranný.

## 8. Otázky na zadavatele

1. Kdy bude známá výše rozpočtu a dá se plán po tomto datu ještě změnit?
2. Čím je daná kapacita zeleniny (závlahy, pracovníci, sklady, odbyt)? Je to pevná mez, nebo ji lze za příplatek zvýšit?
3. Má farmář účetní údaje o skutečných nákladech z minulých let, hlavně u zeleniny?
4. Může část půdy zůstat neosetá, když rozpočet nebude stačit?

## 9. Návrh formulací do executive summary

Návrh podle osnovy prvního executive summary. Skupina ho má projít a upravit.

**Nejdůležitější dosažené výsledky.** Původní osevní plán jsme prověřili při nejistých nákladech, nejisté kapacitě zeleniny a nejistém rozpočtu. Plán je citlivý hlavně na náklady: při růstu nákladů jako v roce 2022 a nezměněných cenách by pravděpodobnost ztráty vzrostla ze 6,5 % na 25,9 %. Doporučujeme proto upravený plán: 250 ha ječmene, 250 ha kukuřice, 250 ha řepky, 50 ha cukrové řepy a 200 ha zeleniny (89 ha cibule, 54 ha zelí, 31 ha česneku, 26 ha salátu). Očekávaný zisk je 35,9 mil. Kč, pravděpodobnost ztráty 2,3 % a náklady plánu 110 mil. Kč, o 47 mil. Kč méně než u původního plánu. Stabilní částí plánu je řepka, ječmen a kukuřice, které zůstávají ve všech scénářích růstu nákladů.

**Klíčové použité metody.** Predikce cen a výnosů i scénáře z první části zůstaly beze změny. Náklady jsme měnili násobkem odvozeným z historické inflace (roky 2008, 2023 a 2022) a citlivostní analýzou v rozsahu −20 % až +40 %. Optimalizační model mean-CVaR jsme rozšířili o parametr kapacity zeleniny a o omezení rozpočtu. Upravený plán minimalizuje největší lítost přes scénáře nákladů, tedy největší ztrátu oproti plánu, který by byl pro daný scénář nejlepší. Stabilitu měříme počtem hektarů, které mají dva plány společné.

**Doporučený další postup.** Největší přínos má zpřesnění nákladů zeleniny: zdražení zeleniny o 20 % by snížilo její plochu v plánu z 200 na 40 ha. Dále doporučujeme ověřit skutečnou kapacitu zeleniny, protože model ji vždy využije celou. Po stanovení rozpočtu lze plán vybrat z připravené tabulky nebo model přepočítat.

**Možné limity řešení.** Růst nákladů vychází z obecné inflace a ve scénářích se mu ceny plodin nepřizpůsobují, skutečný dopad proto může být menší. Kapacita zeleniny i rozpočet jsou modelovány jako pevné meze. Upravený plán závisí na zvolené sadě scénářů nákladů.

**Otázky na zadavatele.** Kdy bude známý rozpočet a lze plán poté ještě změnit? Čím je daná kapacita zeleniny?

## 10. Návrh slidů k doplnění

1. **Co se změnilo a jak jsme to pojali.** Tabulka z oddílu 1.
2. **Náklady.** `graf_naklady.png` a tabulka z 3.2. Sdělení: plán je citlivý na náklady, rozhoduje zelenina.
3. **Limit zeleniny a rozpočet.** `graf_limit_zeleniny_rozpocet.png`. Sdělení: limit je vždy aktivní, rozpočet do 100 mil. Kč plán skoro nezhorší.
4. **Doporučený plán.** Tabulky z 3.1. Sdělení: o 8,7 mil. Kč nižší očekávaný zisk za menší riziko a o 47 mil. Kč nižší náklady.
5. **Stabilita, limity, otázky.** Oddíly 3.5, 6 a 8.

## Slovníček

| Pojem | Význam |
|---|---|
| původní plán | plán z první části projektu ($\lambda = 0{,}5$), je v prvním executive summary |
| odolný plán | plán doporučený po doplnění, má nejmenší největší lítost přes scénáře růstu nákladů |
| očekávaný zisk | průměrný zisk farmy přes 5 000 scénářů cen a výnosů |
| CVaR 10 % | průměrný zisk v 10 % nejhorších scénářů. Odpovídá na otázku „kolik vyděláme, když se to pokazí“ |
| $\lambda$ | váha rizika v optimalizaci. 0 = jen průměr, 1 = jen nejhorší scénáře, používáme 0,5 |
| hodnota plánu | 0,5 · očekávaný zisk + 0,5 · CVaR 10 %. To, co model maximalizuje |
| násobek k | kolikrát jsou náklady vyšší než základ (náklady 2024 × 1,024) |
| lítost | hodnota nejlepšího plánu pro daný scénář minus hodnota našeho plánu v tom scénáři |
| stínová cena | o kolik vzroste hodnota plánu, když se omezení uvolní o jednotku (1 ha zeleniny, 1 Kč rozpočtu) |
| cena opatrnosti | o kolik je plán s omezeným rozpočtem horší než plán bez omezení |
| společné hektary | kolik hektarů mají dva plány oseto stejnou plodinou |
