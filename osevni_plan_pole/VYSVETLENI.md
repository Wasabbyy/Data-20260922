# Paralelní analýza dělení polí

Tato analýza je oddělená od hlavního agregovaného řešení ve složce `osevni_plan/`.

Spuštění z kořene repozitáře:

```text
python osevni_plan_pole/spust_pole.py
```

Výstupy vznikají pouze ve `osevni_plan_pole/vystupy_pole/`, takže hlavní výstupy ve `osevni_plan/vystupy/` se nepřepisují.

## Předpoklady

`osevni_plan_1.pdf` uvádí farmu o 1 000 ha a maximální kapacitu zeleniny 20 %, ale neurčuje velikost jednotlivých polí. Tato varianta proto používá samostatný realistický scénář:

- nejvýše 30 ha produkce na jednom poli,
- 2 ha mezí kolem každého použitého pole,
- stejná plodina může být na více polích,
- celková fyzická plocha včetně mezí nesmí překročit 1 000 ha.

Pro každou plodinu se optimalizuje produkční plocha `x_i` a celočíselný počet polí `n_i`:

$$x_i \le 30 n_i, \qquad \sum_i (x_i + 2 n_i) \le 1\,000.$$

Zachována zůstávají ostatní omezení hlavního modelu: maximálně 200 ha zeleniny a maximálně 250 ha jedné plodiny. Účelová funkce mean-CVaR i scénáře jsou stejné jako v hlavní analýze.

## Výstupy

- `vystupy_pole/plan_pole_2025.csv`: agregované hektary podle plodiny a lambda,
- `vystupy_pole/detaily/plan_pole_2025_detail.csv`: konkrétní pole, plodina, produkční plocha a mez,
- `vystupy_pole/detaily/riziko_pole_2025.csv`: rizikové ukazatele.
