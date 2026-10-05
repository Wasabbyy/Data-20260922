# Doplnění zadání: nejisté náklady, limit zeleniny a rozpočet

Tento dokument popisuje druhou část projektu. První část (predikce cen a výnosů a původní osevní plán) je ve [`VYSVETLENI.md`](VYSVETLENI.md). Stručné podklady pro executive summary jsou v [`PODKLADY_EXECUTIVE_SUMMARY.md`](../PODKLADY_EXECUTIVE_SUMMARY.md) v kořeni repozitáře.

Všechna čísla pochází z běhu `python3 osevni_plan/spust.py`, tabulky a grafy jsou v `osevni_plan/vystupy/doplneni/`. Test `test_cisla_v_textu_odpovidaji_vystupum` hlídá, že čísla v textu odpovídají poslednímu běhu.

## Výsledek na jedné stránce

|  | původní plán (1. část) | **odolný plán (doporučený po doplnění)** |
|---|---|---|
| Ječmen (ha) | 226 | **250** |
| Kukuřice na zrno (ha) | 250 | **250** |
| Řepka (ha) | 250 | **250** |
| Cukrová řepa (ha) | 0 | **50** |
| Brambory (ha) | 74 | **0** |
| Zelí (ha) | 77 | **54** |
| Zelený česnek (ha) | 78 | **31** |
| Salát a čekanka (ha) | 45 | **26** |
| Cibule a šalotka (ha) | 0 | **89** |
| náklady plánu (mil. Kč) | 156,9 | **109,8** |
| základní náklady: očekávaný zisk / CVaR 10 % (mil. Kč) / P(ztráta) | 44,6 / −3,4 / 6,5 % | **35,9 / 2,9 / 2,3 %** |
| růst nákladů jako 2022: očekávaný zisk / CVaR 10 % (mil. Kč) / P(ztráta) | 25,1 / −22,9 / 25,9 % | **22,3 / −10,7 / 15,7 %** |
| největší lítost přes scénáře růstu nákladů (mil. Kč) | 5,65 | **1,15** |

CVaR 10 % je průměrný zisk v 10 % nejhorších scénářů. Lítost říká, o kolik je plán v daném scénáři horší než plán optimální přímo pro ten scénář (oddíl 4).

Původní plán je optimální jen tehdy, když náklady vyjdou podle farmářova odhadu. Odolný plán obětuje 8,7 mil. Kč očekávaného zisku, ale stojí o 47 mil. Kč méně a při růstu nákladů ztrácí méně často. Proto ho po doplnění zadání doporučujeme. Jak jsme k němu došli, popisují oddíly 1 až 4.

---

## Co se v zadání změnilo

Druhá prezentace (`zadani/osevni_plan_2.pdf`) mění tři věci. Náklady jsou jen hrubý odhad farmáře a mohou růst rychleji než prodejní ceny. Limit 20 % rozlohy pro zeleninu je také jen hrubý odhad. Farmář navíc zatím nezná rozpočet na rok 2025.

Predikce cen a výnosů se nemění. Všechny výpočty v tomto dokumentu používají stejných 5 000 scénářů tržeb jako původní plán (oddíl 5 a 6 ve `VYSVETLENI.md`), takže rozdíl mezi plány jde vždy jen za změněný parametr. Kód je v `naklady_rozpocet.py` a `optimalizace.py`, výsledky se stejně jako dřív měří na nezávislé testovací sadě scénářů.

Dva pojmy, které se dál opakují. **Původní plán** je plán s $\lambda = 0{,}5$ z první části projektu (oddíl 6.3 ve `VYSVETLENI.md`). Je to plán z prvního executive summary. **Hodnota plánu** je $0{,}5 \cdot E[Z] + 0{,}5 \cdot \text{CVaR}_{10\%}[Z]$, tedy přesně to, co LP maximalizuje. Původní plán má hodnotu $0{,}5 \cdot 44,6 + 0{,}5 \cdot (−3,4) = 20,6$ mil. Kč.

## 1. Scénáře nákladů

Náklady plodiny $i$ ve scénáři: $C_i(k) = C_i^{2025} \cdot k$, kde $C_i^{2025}$ = náklady 2024 × 1,024 (stejný základ jako v první části) a $k$ je násobek vůči tomuto základu. Marže ve scénáři je tržba $- \; C_i(k)$.

**Růst nákladů.** Zadání číslo neuvádí, proto bereme skutečné roky z `makroekonomicke_ukazatele.xlsx`. Když náklady porostou jako v roce $r$ místo základních 2,4 %:

$k_r = (1 + \pi_r) / (1 + \pi_{2024})$

Pro rok 2022: $k = 1{,}151 / 1{,}024 = 1,124$. Pšenice pak stojí $25 600 \cdot 1,124 = 28 774$ Kč/ha, o 3 174 Kč/ha víc než v základu. Její průměrná marže klesne z 8 812 na 5 637 Kč/ha. Ceny plodin zůstávají podle modelu. Scénář tedy říká „náklady porostou jako v roce 2022 a ceny se tomu nepřizpůsobí“, což je obava ze zadání. Roky 2008, 2023 a 2022 jsou tři roky s nejvyšší inflací od roku 2000 (průměr 2000–2024 je 3,2 %).

**Chyba farmářova odhadu.** K té nemáme žádná data, zadání říká jen „významně“. Nevymýšlíme proto scénář typu „+25 %“, ale počítáme citlivost pro $k$ od 0,80 do 1,40 a hledáme, kde se plán láme. Pokud chyba odhadu i rychlejší růst platí pro všechny plodiny stejně, jde o jediný násobek: odhad o 10 % níž a růst jako 2022 dají $1{,}10 \cdot 1,124 = 1,236$. Zvlášť proto sledujeme jen rozdíl mezi polními plodinami a zeleninou.

**Kdy plodina přestane vydělávat.** Průměrná marže je nulová při $k$ = průměrná tržba / náklady. Ječmen: $36 632 / 25 600 = 1,43$, náklady by musely být o 43 % vyšší (`vystupy/doplneni/naklady_bod_zvratu.csv`):

| Plodina | náklady (Kč/ha) | průměrná tržba (Kč/ha) | k pro nulovou průměrnou marži | k pro nulovou mediánovou marži |
|---|---|---|---|---|
| Ječmen | 25 600 | 36 632 | 1,43 | 1,36 |
| Kukuřice na zrno | 30 720 | 42 633 | 1,39 | 1,34 |
| Řepka | 28 672 | 41 597 | 1,45 | 1,42 |
| Cukrová řepa | 55 296 | 62 288 | 1,13 | 1,11 |
| Brambory | 222 208 | 252 172 | 1,14 | 1,10 |
| Zelí | 276 480 | 355 304 | 1,28 | 1,21 |
| Zelený česnek | 533 504 | 696 339 | 1,30 | 1,24 |
| Salát a čekanka | 1 263 616 | 1 588 942 | 1,26 | 1,04 |
| Cibule a šalotka | 235 520 | 329 759 | 1,40 | 1,34 |

Celý původní plán má průměrnou tržbu 201,5 mil. Kč a náklady 156,9 mil. Kč. Očekávaný zisk je nulový při $k = 201,5 / 156,9 = 1,28$. U salátu je vidět rozdíl mezi průměrem a mediánem: v polovině scénářů prodělá už při nákladech o 4 % vyšších.

**Výsledky scénářů** (`vystupy/doplneni/naklady_scenare.csv`, `naklady_scenare_plany.csv`). V buňkách je očekávaný zisk / CVaR 10 % (mil. Kč) / pravděpodobnost ztráty:

| Scénář | k | původní plán | plán přepočítaný pro scénář | odolný plán (oddíl 4) | společné ha (původní a přepočítaný) |
|---|---|---|---|---|---|
| základ (růst 2,4 %) | 1,000 | 44,6 / −3,4 / 6,5 % | 44,6 / −3,4 / 6,5 % | 35,9 / 2,9 / 2,3 % | 1000 |
| růst jako 2008 (6,3 %) | 1,038 | 38,6 / −9,4 / 11,4 % | 32,6 / −2,0 / 6,1 % | 31,7 / −1,3 / 5,3 % | 851 |
| růst jako 2023 (10,7 %) | 1,081 | 31,9 / −16,2 / 18,1 % | 26,0 / −4,6 / 8,6 % | 27,0 / −6,0 / 10,0 % | 811 |
| růst jako 2022 (15,1 %) | 1,124 | 25,1 / −22,9 / 25,9 % | 20,7 / −7,1 / 12,1 % | 22,3 / −10,7 / 15,7 % | 768 |

Čtení posledního řádku: když náklady porostou jako v roce 2022 a farma oseje původní plán, vydělá v průměru 25,1 mil. Kč, v nejhorší desetině scénářů průměrně ztratí 22,9 mil. Kč a ztrátou skončí 25,9 % scénářů. Plán přepočítaný pro tyto náklady má průměr 20,7 mil. Kč, ale ztrátu jen ve 12,1 % scénářů. Od původního plánu se liší na 232 ha z 1 000.

| Plodina (ha) | základ = původní plán | jako 2008 | jako 2023 | jako 2022 | **odolný plán** |
|---|---|---|---|---|---|
| Ječmen | 226 | 250 | 250 | 250 | **250** |
| Oves | 0 | 0 | 0 | 50 | **0** |
| Kukuřice na zrno | 250 | 250 | 250 | 250 | **250** |
| Řepka | 250 | 250 | 250 | 250 | **250** |
| Cukrová řepa | 0 | 50 | 50 | 0 | **50** |
| Brambory | 74 | 0 | 0 | 0 | **0** |
| Zelí | 77 | 58 | 45 | 30 | **54** |
| Zelený česnek | 78 | 37 | 19 | 0 | **31** |
| Salát a čekanka | 45 | 30 | 21 | 12 | **26** |
| Cibule a šalotka | 0 | 75 | 115 | 158 | **89** |

Polní jádro (ječmen, kukuřice, řepka) se nemění. S rostoucími náklady mizí brambory a v zelenině se plocha přesouvá od česneku a salátu k cibuli. Cibule má ze zeleniny nejnižší náklady na hektar (235 520 Kč) a nejvyšší bod zvratu (1,40), takže zdražení snáší nejlépe.

**Citlivost na chybu odhadu** (`vystupy/doplneni/naklady_citlivost.csv`, `graf_naklady.png`). Zisky v mil. Kč:

| k | 0,80 | 0,90 | 1,00 | 1,10 | 1,20 | 1,30 | 1,40 |
|---|---|---|---|---|---|---|---|
| původní plán: očekávaný zisk | 76,0 | 60,3 | 44,6 | 28,9 | 13,2 | −2,5 | −18,2 |
| původní plán: P(ztráta) | 0,0 % | 0,4 % | 6,5 % | 21,4 % | 42,8 % | 65,3 % | 80,6 % |
| přepočítaný plán: očekávaný zisk | 121,4 | 75,7 | 44,6 | 23,4 | 11,2 | 2,1 | −0,4 |
| přepočítaný plán: P(ztráta) | 2,1 % | 3,1 % | 6,5 % | 9,8 % | 19,3 % | 42,2 % | 59,6 % |
| přepočítaný plán: zelenina (ha) | 200 | 200 | 200 | 200 | 139 | 4 | 0 |
| společné ha s původním plánem | 495 | 562 | 1000 | 785 | 633 | 550 | 476 |

Plán je na úroveň nákladů citlivý oběma směry. Při nákladech o 10 % nižších se vyplatí brambory a cukrová řepa a s původním plánem zůstane společných jen 562 ha. Při nákladech o 20 % vyšších zelenina klesne na 139 ha a při 25 % na 17 ha. Jediná plodina, která je v plánu v plné výši 250 ha v celém rozsahu, je řepka.

**Polní plodiny, nebo zelenina?** (`vystupy/doplneni/naklady_mrizka_pole_zelenina.csv`, `graf_naklady_pole_zelenina.png`). Když zdražíme jen zeleninu o 20 %, plocha zeleniny klesne z 200 na 40 ha. Když zdražíme jen polní plodiny o 20 %, zelenina zůstane na 200 ha a mění se jen skladba polní části. Do zdražení zeleniny o 10 % se plná plocha 200 ha drží vždy. Pro plán je tedy podstatné zpřesnit hlavně odhad nákladů zeleniny.

## 2. Nejistý limit zeleniny

V `optimalizace.py` je limit zeleniny nově parametr `max_zelenina`. Plán jsme přepočítali pro limit 0 až 400 ha, tedy 0 až 40 % rozlohy (`vystupy/doplneni/limit_zeleniny.csv`, `limit_zeleniny_plany.csv`, `graf_limit_zeleniny_rozpocet.png`):

| Limit zeleniny (ha) | 0 | 100 | 150 | 200 | 250 | 300 | 400 |
|---|---|---|---|---|---|---|---|
| očekávaný zisk (mil. Kč) | 11,1 | 28,8 | 36,8 | 44,6 | 51,7 | 59,3 | 74,3 |
| CVaR 10 % (mil. Kč) | −0,2 | −0,4 | −2,0 | −3,4 | −4,5 | −6,0 | −9,1 |
| P(ztráta) | 4,7 % | 4,8 % | 5,8 % | 6,5 % | 6,8 % | 7,1 % | 7,7 % |
| náklady plánu (mil. Kč) | 38,9 | 100,3 | 128,7 | 156,9 | 185,2 | 214,9 | 273,4 |
| stínová cena (tis. Kč za ha limitu) | 507,2 | 62,9 | 60,3 | 58,6 | 57,7 | 57,0 | 56,4 |
| společné ha s původním plánem | 726 | 868 | 935 | 1000 | 932 | 864 | 733 |

| Plodina (ha) | 0 ha | 100 ha | 150 ha | 200 ha | 250 ha | 300 ha | 400 ha |
|---|---|---|---|---|---|---|---|
| Ječmen | 250 | 250 | 250 | 226 | 158 | 98 | 0 |
| Kukuřice na zrno | 230 | 250 | 250 | 250 | 250 | 242 | 209 |
| Řepka | 250 | 250 | 250 | 250 | 250 | 250 | 250 |
| Cukrová řepa | 250 | 108 | 41 | 0 | 0 | 0 | 0 |
| Brambory | 20 | 42 | 59 | 74 | 92 | 110 | 141 |
| Zelí | 0 | 36 | 56 | 77 | 102 | 123 | 167 |
| Zelený česnek | 0 | 38 | 58 | 78 | 95 | 115 | 154 |
| Salát a čekanka | 0 | 27 | 36 | 45 | 53 | 62 | 79 |

**Limit je aktivní v celém rozsahu.** Model při $\lambda = 0{,}5$ vždy využije všechnu zeleninu, kterou mu limit dovolí. Stínová cena říká, o kolik vzroste hodnota plánu, když limit povolí o 1 ha. Při 200 ha je to 58,6 tis. Kč. Kontrola na testovací sadě: přechod z 200 na 250 ha zvedne hodnotu z 20,58 na 23,63 mil. Kč, tedy o $(23,63 - 20,58) / 50 = 61$ tis. Kč na hektar.

Nad 200 ha přidá každých 50 ha zeleniny navíc v průměru 7,4 mil. Kč očekávaného zisku a ubere 1,4 mil. Kč v nejhorší desetině scénářů. Zároveň zvedne náklady plánu o 29,1 mil. Kč. Plochu zeleniny v plánu tedy neurčuje model, ale farmářův odhad kapacity. Skladba zeleniny je přitom stabilní: od 100 ha výš jsou to zelí, česnek a salát zhruba v poměru 39 : 39 : 23. V polní části zůstává řepka na 250 ha, při vyšším limitu ustupuje ječmen.

## 3. Nejistý rozpočet

Rozpočet je jedno lineární omezení navíc, úloha zůstává LP:

$\sum_i C_i \, x_i \le B$

Původní plán stojí 156,9 mil. Kč, z toho zelenina (200 ha) 119,8 mil. Kč a polní plodiny (800 ha) 37,1 mil. Kč. Rozpočet proto omezuje skoro jen zeleninu. Nejlevnější osetí celé farmy je 250 ha hrachu, lnu, žita a slunečnice: $250 \cdot (12\,288 + 18\,432 + 20\,480 + 23\,552) = 18,7$ mil. Kč. Pod touto částkou úloha nemá řešení a `vyres` to ohlásí chybou.

Výši rozpočtu neznáme, proto dáváme plán pro každou výši (`vystupy/doplneni/rozpocet.csv`, `rozpocet_plany.csv`):

| Rozpočet (mil. Kč) | 25 | 40 | 60 | 80 | 100 | 120 | 140 | 160 |
|---|---|---|---|---|---|---|---|---|
| zelenina (ha) | 11 | 72 | 139 | 200 | 200 | 200 | 200 | 200 |
| očekávaný zisk (mil. Kč) | 9,5 | 15,3 | 23,3 | 30,4 | 34,1 | 38,0 | 41,5 | 44,6 |
| CVaR 10 % (mil. Kč) | −0,1 | 1,3 | 1,9 | 2,9 | 3,5 | 1,7 | −0,8 | −3,4 |
| P(ztráta) | 4,3 % | 2,4 % | 2,5 % | 2,5 % | 2,0 % | 3,0 % | 5,0 % | 6,5 % |
| cena opatrnosti (mil. Kč) | 15,8 | 12,2 | 8,0 | 3,9 | 1,8 | 0,7 | 0,2 | 0,0 |
| stínová cena (Kč hodnoty za 1 Kč rozpočtu) | 0,27 | 0,21 | 0,20 | 0,16 | 0,08 | 0,03 | 0,01 | 0,00 |
| společné ha s původním plánem | 549 | 508 | 634 | 757 | 809 | 867 | 946 | 1000 |

| Plodina (ha) | 25 mil. | 40 mil. | 60 mil. | 80 mil. | 100 mil. | 120 mil. | 140 mil. | 160 mil. |
|---|---|---|---|---|---|---|---|---|
| Ječmen | 250 | 250 | 250 | 250 | 250 | 250 | 250 | 226 |
| Žito | 35 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Oves | 64 | 149 | 71 | 50 | 0 | 0 | 0 | 0 |
| Kukuřice na zrno | 73 | 29 | 148 | 250 | 250 | 250 | 250 | 250 |
| Řepka | 250 | 250 | 250 | 250 | 250 | 250 | 250 | 250 |
| Len olejný | 66 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Hrách na zrno | 250 | 250 | 142 | 0 | 0 | 0 | 0 | 0 |
| Cukrová řepa | 0 | 0 | 0 | 0 | 50 | 43 | 5 | 0 |
| Brambory | 0 | 0 | 0 | 0 | 0 | 7 | 45 | 74 |
| Zelí | 0 | 0 | 5 | 22 | 44 | 59 | 74 | 77 |
| Zelený česnek | 0 | 0 | 0 | 0 | 18 | 43 | 62 | 78 |
| Salát a čekanka | 0 | 2 | 5 | 9 | 21 | 32 | 39 | 45 |
| Cibule a šalotka | 11 | 70 | 128 | 169 | 117 | 66 | 25 | 0 |

**Cena opatrnosti** je hodnota původního plánu minus hodnota plánu s daným rozpočtem. Říká, o kolik přijdeme, když budeme plánovat s rozpočtem $B$, přestože by peněz bylo dost. Při $B = 100$ mil. Kč je to 1,8 mil. Kč: očekávaný zisk klesne ze 44,6 na 34,1 mil. Kč, ale CVaR se zlepší z −3,4 na 3,5 mil. Kč a pravděpodobnost ztráty klesne z 6,5 % na 2,0 %. Menší rozpočet vytlačí drahý česnek a salát ve prospěch cibule, a tím snižuje i riziko. Pod 80 mil. Kč už rozpočet nestačí na 200 ha zeleniny a cena opatrnosti roste rychle: 3,9 mil. Kč při 80 mil. a 10,1 mil. Kč při 50 mil. Kč. Stínová cena při $B = 100$ říká, že milion korun rozpočtu navíc zvedne hodnotu plánu o 82 tis. Kč.

**Rozpočet s rezervou.** Rozpočet se počítá z nákladů, které jsou samy nejisté. Varianta „s rezervou“ v `rozpocet.csv` proto hlídá omezení při nákladech o 12,4 % vyšších (růst jako 2022): $\sum_i 1,124 \cdot C_i \, x_i \le B$. Při $B = 100$ mil. Kč pak plán stojí při základních nákladech 89,0 mil. Kč a zbytek je rezerva.

**Rozpočet a limit zeleniny najednou** (`vystupy/doplneni/rozpocet_x_zelenina.csv`). Hektary zeleniny v plánu:

| Zelenina v plánu (ha) | B = 40 | B = 60 | B = 80 | B = 100 | B = 120 | B = 160 | bez limitu |
|---|---|---|---|---|---|---|---|
| limit 100 ha | 72 | 100 | 100 | 100 | 100 | 100 | 100 |
| limit 200 ha | 72 | 139 | 200 | 200 | 200 | 200 | 200 |
| limit 300 ha | 72 | 139 | 206 | 290 | 300 | 300 | 300 |

Při nízkém rozpočtu rozhoduje rozpočet a na limitu zeleniny nezáleží. Při vysokém rozpočtu rozhoduje limit. Hranice leží zhruba u 50 mil. Kč pro limit 100 ha, 80 mil. Kč pro 200 ha a 120 mil. Kč pro 300 ha.

## 4. Plán odolný vůči růstu nákladů
**Odolný plán podle λ** je navíc v samostatné tabulce `vystupy/doplneni/odolny_plan_podle_lambda.csv`. Každý sloupec minimalizuje největší lítost přes stejné čtyři scénáře růstu nákladů, ale s jinou vahou CVaR; sloupec `lambda_0.5` odpovídá nastavení doporučeného odolného plánu níže. Původní tabulky a doporučení zůstávají beze změny.


Původní plán je optimální jen pro základní náklady. Hledáme proto jeden plán, který se v žádném ze čtyř scénářů růstu nákladů příliš neliší od plánu optimálního pro daný scénář. **Lítost** plánu $x$ ve scénáři $s$ je hodnota nejlepšího plánu pro $s$ minus hodnota plánu $x$ v $s$. Odolný plán minimalizuje největší lítost přes scénáře:

$\min_x \max_s \; [\, V_s(x_s^*) - V_s(x) \,]$

Je to opět LP (`optimalizace.minimax_litost`), každý scénář má vlastní proměnné pro CVaR. Pravděpodobnosti scénářů k tomu nepotřebujeme, což se hodí, protože je neznáme.

| Lítost (mil. Kč) | základ (růst 2,4 %) | růst jako 2008 (6,3 %) | růst jako 2023 (10,7 %) | růst jako 2022 (15,1 %) |
|---|---|---|---|---|
| původní plán | 0,00 | 0,67 | 2,81 | 5,65 |
| odolný plán | 1,15 | 0,03 | 0,14 | 0,96 |

Příklad: ve scénáři růstu jako 2022 má plán optimální pro tento scénář hodnotu $0{,}5 \cdot 20,67 + 0{,}5 \cdot (−7,13) = 6,77$ mil. Kč a původní plán $0{,}5 \cdot 25,13 + 0{,}5 \cdot (−22,89) = 1,12$ mil. Kč. Lítost původního plánu je 5,65 mil. Kč. Odolný plán má největší lítost 1,15 mil. Kč, a to v základním scénáři.

Odolný plán je v posledním sloupci tabulky plánů v oddílu 1: ječmen 250 ha, kukuřice na zrno 250 ha, řepka 250 ha, cukrová řepa 50 ha, zelí 54 ha, zelený česnek 31 ha, salát a čekanka 26 ha, cibule a šalotka 89 ha. Stojí 109,8 mil. Kč, o 47,1 mil. Kč méně než původní plán. Při základních nákladech má očekávaný zisk 35,9 mil. Kč místo 44,6, zato CVaR 2,9 mil. Kč místo −3,4 a ztrátu ve 2,3 % scénářů místo 6,5 %. Při růstu nákladů jako 2022 má ztrátu v 15,7 % scénářů, původní plán ve 25,9 %.

Platí to i mimo čtyři scénáře: pro všechna $k$ od 1,05 do 1,40 má odolný plán menší lítost než původní (při $k = 1{,}20$ je to 3,1 proti 11,4 mil. Kč). Kdyby náklady byly naopak nižší než odhad, je lepší původní plán (při $k = 0{,}90$ lítost 3,7 proti 9,6 mil. Kč). To je cena za ochranu proti zdražení. Odolný plán v tom případě nevydělá méně než při základních nákladech, jen nevyužije levnější brambory a cukrovou řepu.

**Odolný plán pro různé limity zeleniny** (`vystupy/doplneni/doporuceny_plan_podle_limitu_zeleniny.csv`). Protože limit zeleniny je odhad, počítáme odolný plán i pro jiné limity:

| Limit zeleniny (ha) | 100 | 150 | **200** | 250 | 300 |
|---|---|---|---|---|---|
| Ječmen | 250 | 250 | **250** | 250 | 250 |
| Kukuřice na zrno | 250 | 250 | **250** | 250 | 200 |
| Řepka | 250 | 250 | **250** | 250 | 250 |
| Cukrová řepa | 150 | 100 | **50** | 0 | 0 |
| Zelí | 18 | 35 | **54** | 71 | 90 |
| Zelený česnek | 15 | 22 | **31** | 39 | 47 |
| Salát a čekanka | 18 | 22 | **26** | 31 | 35 |
| Cibule a šalotka | 49 | 70 | **89** | 109 | 128 |
| **náklady plánu (mil. Kč)** | 76,7 | 93,2 | 109,8 | 126,4 | 143,8 |
| **náklady při růstu jako 2022 (mil. Kč)** | 86,2 | 104,8 | 123,4 | 142,1 | 161,6 |
| základ: E / CVaR / P(ztráta) | 24,6 / 2,5 / 2,2 % | 30,3 / 2,7 / 2,3 % | 35,9 / 2,9 / 2,3 % | 41,6 / 3,0 / 2,4 % | 47,0 / 3,3 / 2,4 % |
| růst jako 2022: E / CVaR / P(ztráta) | 15,1 / −7,1 / 14,9 % | 18,7 / −8,8 / 15,4 % | 22,3 / −10,7 / 15,7 % | 26,0 / −12,7 / 16,2 % | 29,1 / −14,5 / 16,7 % |
| největší lítost (mil. Kč) | 0,68 | 0,93 | 1,15 | 1,32 | 1,52 |

Řádek „náklady při růstu jako 2022“ je rozpočet, který plán potřebuje, aby se dal zaplatit i v nejdražším scénáři.

## 5. Stabilita plánu

Stabilitu měříme dvěma čísly. **Společné hektary** dvou plánů jsou $\sum_i \min(x_i, y_i)$: kolik hektarů mají oba plány oseto stejnou plodinou. Původní plán a plán pro růst jako 2022 mají společných 768 ha. **Jádro** je nejmenší plocha plodiny napříč všemi plány v dané skupině (`vystupy/doplneni/stabilita_jadro.csv`):

| Nejmenší plocha napříč plány (ha) | 4 scénáře růstu nákladů | náklady k = 0,80 až 1,40 | limit zeleniny 0 až 400 ha | rozpočet 25 až 180 mil. Kč |
|---|---|---|---|---|
| Brambory | 0 | 0 | 20 | 0 |
| Ječmen | 226 | 0 | 0 | 226 |
| Kukuřice na zrno | 250 | 0 | 186 | 29 |
| Salát a čekanka | 12 | 0 | 0 | 0 |
| Zelí | 30 | 0 | 0 | 0 |
| Řepka | 250 | 250 | 250 | 250 |

- **Řepka 250 ha** je ve všech spočítaných plánech bez výjimky.
- **Ječmen a kukuřice** po 226 až 250 ha drží ve scénářích růstu nákladů. Ustupují při nákladech o 5 % a víc pod odhadem, kukuřice také při nákladech o 20 % a víc nad odhadem a při rozpočtu pod 80 mil. Kč, ječmen při limitu zeleniny nad 200 ha.
- **Zelenina** je nestabilní část. Plochu určuje limit a rozpočet, skladbu náklady. Při dražších vstupech nebo menším rozpočtu roste cibule a klesá česnek a salát.
- **Brambory** (74 ha v původním plánu) vypadnou už při růstu nákladů jako 2008.

## 6. Předpoklady doplnění (projít se skupinou)

1. **Náklady rostou, ceny ne.** Ve scénářích růstu zůstávají ceny plodin podle modelu. V roce 2022 přitom vzrostla cena u 20 plodin z 20 (medián +28 %), ceny tedy tehdy rostly spolu s náklady. V roce 2023 už cena vzrostla jen u 8 plodin z 20 (medián −2 %) při inflaci 10,7 %. Scénář „náklady rostou, ceny ne“ tedy odpovídá spíš roku 2023 než 2022.
2. **Růst nákladů = inflace CPI.** Řadu nákladů farmy nemáme. Inflace vstupů v zemědělství se od CPI může lišit.
3. **Stejný násobek pro všechny polní plodiny a pro všechnu zeleninu.** Chybu odhadu u jednotlivé plodiny nemodelujeme.
4. **Limit zeleniny i rozpočet jsou tvrdé horní meze** a celá rozloha se musí oset. Úhor model nepřipouští.
5. **Rozpočet pokrývá náklady všech plodin najednou** a tržby přijdou až po sklizni. Kdy farmář rozpočet zjistí, zadání neříká, proto dáváme tabulku pro každou výši.
6. **Odolný plán** chrání proti čtyřem scénářům růstu nákladů při $\lambda = 0{,}5$. Jiná sada scénářů dá jiný plán.

## 7. Návrh závěrů

- Růst nákladů plán mění. Kdyby náklady rostly jako v roce 2022 (o 15,1 % místo 2,4 %) a ceny ne, původní plán by skončil ztrátou ve 25,9 % scénářů místo 6,5 %.
- Doporučujeme odolný plán: ječmen 250 ha, kukuřice na zrno 250 ha, řepka 250 ha, cukrová řepa 50 ha, zelí 54 ha, zelený česnek 31 ha, salát a čekanka 26 ha, cibule a šalotka 89 ha. Stojí 110 mil. Kč (při růstu nákladů jako 2022 123 mil. Kč), očekávaný zisk je 35,9 mil. Kč a ztráta nastane ve 2,3 % scénářů. Proti původnímu plánu obětuje 8,7 mil. Kč očekávaného zisku a potřebuje o 47 mil. Kč menší rozpočet.
- Nejdůležitější je zpřesnit náklady zeleniny. Zdražení zeleniny o 20 % sníží její plochu z 200 na 40 ha, stejné zdražení polních plodin plochu zeleniny nezmění.
- Limit zeleniny je vždy aktivní. Každý hektar limitu navíc má hodnotu kolem 59 tis. Kč, ale zvyšuje riziko i potřebný rozpočet. Pro jiný limit je plán v tabulce v oddílu 4.
- Plán s rozpočtem 100 mil. Kč je skoro stejně dobrý jako původní plán za 157 mil. Kč (cena opatrnosti 1,8 mil. Kč). Pod 80 mil. Kč je potřeba ubrat zeleninu a pod 18,7 mil. Kč nelze oset celou farmu.
- Stabilní jádro je řepka, ječmen a kukuřice po 250 ha. Na nákladech, limitu a rozpočtu závisí hlavně 200 až 250 ha zeleniny a okrajových polních plodin.
