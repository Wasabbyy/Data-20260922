"""Testy: python3 -m pytest osevni_plan/test_reseni.py -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt  # noqa: E402
import data as dt  # noqa: E402
import modely as md  # noqa: E402
import naklady_rozpocet as nr  # noqa: E402
import optimalizace as op  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return dt.nacti()


def test_zadna_data_po_2024(data):
    for tab in (data.ceny, data.vynosy, data.plochy, data.pocasi, data.makro):
        assert tab.index.max() == 2024


def test_marze_2024_psenice(data):
    # 4772 Kč/t * 5956.7 kg/ha / 1000 - 25000 Kč/ha = 3425.4 Kč/ha
    m = dt.marze_2024(data).loc["0111", "marze_kc_ha"]
    assert m == pytest.approx(4772 * 5956.7 / 1000 - 25000)


@pytest.mark.parametrize("modely", [md.MODELY_CEN, md.MODELY_VYNOSU])
def test_modely_nevidi_budoucnost(data, modely):
    """Když přepíšeme všechno po roce T nesmyslem, predikce z T se nesmí změnit."""
    K = md.Kontext.z_dat(data)
    T = 2015
    pokazeny = md.Kontext(K.lp.copy(), K.ly.copy(), K.pocasi.copy(), K.makro.copy())
    for tab in (pokazeny.lp, pokazeny.ly, pokazeny.pocasi, pokazeny.makro):
        tab.loc[T + 1:] = 999.0
    for nazev, f in modely.items():
        a, b = f(K.do(T), T), f(pokazeny.do(T), T)
        pd.testing.assert_series_equal(a, b, check_names=False, obj=nazev)


def test_arima_vynos_finite(data):
    K = md.Kontext.z_dat(data)
    pred = md.vynos_arima(K.do(2015), 2015)
    assert pred.index.tolist() == dt.KODY
    assert np.isfinite(pred.to_numpy()).all()
    naive = md.vynos_naivni(K.do(2015), 2015)
    assert not np.allclose(pred.to_numpy(), naive.to_numpy())


def test_crps_bodove_predikce():
    # Pro "vzorek" s jedinou hodnotou je CRPS rovno absolutní chybě
    assert bt.crps_vzorek(np.full(100, 2.0), 3.5) == pytest.approx(1.5)


def test_optimalizace_splni_omezeni(data):
    rng = np.random.default_rng(0)
    M = rng.normal(10_000, 5_000, size=(500, 20))
    om = op.omezeni(data.zelenina)
    for lam in (0.0, 0.5, 1.0):
        x = op.optimalizuj(M, om, lam=lam)
        assert x.sum() == pytest.approx(op.ROZLOHA)
        assert x[om.zelenina].sum() <= op.MAX_ZELENINA + 1e-6
        assert np.all(x <= om.horni + 1e-6) and np.all(x >= 0)


def test_lambda0_je_maximum_ocekavani(data):
    """Při lambda = 0 je úloha lineární v průměrech: optimum = hladové plnění podle průměrné marže."""
    rng = np.random.default_rng(1)
    M = rng.normal(0, 1, size=(300, 20)) + np.linspace(0, 19, 20)
    om = op.omezeni(data.zelenina)
    x = op.optimalizuj(M, om, lam=0.0)
    mu = M.mean(axis=0)
    zbyva, zel_zbyva, hlad = op.ROZLOHA, op.MAX_ZELENINA, np.zeros(20)
    for i in np.argsort(-mu):
        h = min(om.horni[i], zbyva, zel_zbyva if om.zelenina[i] else np.inf)
        hlad[i] = h
        zbyva -= h
        zel_zbyva -= h if om.zelenina[i] else 0
    assert mu @ x == pytest.approx(mu @ hlad, rel=1e-6)


def test_bootstrap_zachova_prumer_a_korelace():
    rng = np.random.default_rng(3)
    E = rng.multivariate_normal([0.1, -0.2], [[1, 0.9], [0.9, 1]], size=22)
    S, _ = bt.vyhlazeny_bootstrap(E, 400_000, rng)
    b2 = bt.faktor_jadra(len(E)) ** 2
    # rozptyl = (výběrový rozptyl s dělitelem n + b^2 * výběrový rozptyl s dělitelem n-1) / (1 + b^2)
    ocekavana = (np.cov(E.T, bias=True) + b2 * np.cov(E.T)) / (1 + b2)
    assert S.mean(axis=0) == pytest.approx(E.mean(axis=0), abs=0.01)
    assert np.cov(S.T) == pytest.approx(ocekavana, abs=0.01)
    assert np.corrcoef(S.T)[0, 1] == pytest.approx(np.corrcoef(E.T)[0, 1], abs=0.005)


def test_pocasi_je_spolecna_ols(data):
    """Efekt počasí musí odpovídat přímé OLS s konstantou a trendem pro každou plodinu."""
    K = md.Kontext.z_dat(data).do(2024)
    gamma, _ = md.odhad_pocasi(K, 2024)
    clenove = [k for k in dt.KODY if dt.PODSKUPINY[k] == "obiloviny"]
    ly = K.ly.loc[2024 - md.OKNO_TREND + 1:2024]
    w = md._pocasi_std(K).loc[ly.index].to_numpy()
    t = ly.index.to_numpy(float)
    bloky, Y = [], []
    for j, kod in enumerate(clenove):
        D = np.zeros((len(t), 2 * len(clenove)))
        D[:, 2 * j], D[:, 2 * j + 1] = 1, t
        bloky.append(np.hstack([D, w]))
        Y.append(ly[kod].to_numpy())
    beta = np.linalg.lstsq(np.vstack(bloky), np.concatenate(Y), rcond=None)[0]
    assert gamma.loc["0111"].to_numpy() == pytest.approx(beta[-2:], abs=1e-8)


# --- doplnění zadání: náklady, limit zeleniny, rozpočet ---------------------
@pytest.fixture(scope="module")
def uloha(data):
    """Malá umělá úloha: tržby rostou s náklady, dražší plodiny jsou výnosnější i rizikovější."""
    rng = np.random.default_rng(7)
    C = data.naklady_2024.to_numpy(float)
    T = C * (1.15 + 0.25 * rng.standard_normal((400, 20)))
    return T, C, op.omezeni(data.zelenina)


def test_nasobek_rustu_nakladu(data):
    # náklady rostou jako v roce 2022 (15,1 %) místo základních 2,4 %: 1,151 / 1,024 = 1,124
    assert nr.nasobek_rustu(data.makro, 2022) == pytest.approx(1.151 / 1.024)
    assert nr.nasobek_rustu(data.makro, 2024) == pytest.approx(1.0)
    sc = nr.scenare_rustu(data.makro)
    assert [round(s.k_pole, 3) for s in sc] == [1.0, 1.038, 1.081, 1.124]


def test_naklady_scenare_deli_pole_a_zeleninu(data):
    zel = data.zelenina.reindex(dt.KODY).to_numpy(bool)
    C = nr.naklady_scenare(np.full(20, 100.0), zel, nr.ScenarNakladu("x", 1.1, 1.3))
    assert C[0] == pytest.approx(110) and C[-1] == pytest.approx(130)


def test_vychozi_omezeni_se_nezmenila(uloha):
    T, C, om = uloha
    x = op.optimalizuj(T - C, om)
    assert x == pytest.approx(op.optimalizuj(T - C, om, max_zelenina=200.0))
    assert x == pytest.approx(op.vyres(T - C, om, naklady=C, rozpocet=1e12).x, abs=1e-4)


def test_rozpocet_se_dodrzi_a_je_aktivni(uloha):
    T, C, om = uloha
    bez = op.vyres(T - C, om)
    B = 0.6 * C @ bez.x
    r = op.vyres(T - C, om, naklady=C, rozpocet=B)
    assert C @ r.x == pytest.approx(B, rel=1e-6)          # rozpočet se vyčerpá
    assert r.x.sum() == pytest.approx(op.ROZLOHA)
    assert r.stin_rozpocet > 0 and r.hodnota < bez.hodnota


def test_rozpocet_pod_minimem_hlasi_chybu(uloha, data):
    T, C, om = uloha
    minimum = op.min_rozpocet(C, om)
    # nejlevnější osetí = 250 ha čtyř nejlevnějších plodin
    assert minimum == pytest.approx(250 * np.sort(C)[:4].sum())
    with pytest.raises(ValueError, match="nestačí"):
        op.vyres(T - C, om, naklady=C, rozpocet=0.99 * minimum)
    op.vyres(T - C, om, naklady=C, rozpocet=1.01 * minimum)


def test_hodnota_optima_je_monotonni(uloha):
    T, C, om = uloha
    podle_B = [op.vyres(T - C, om, naklady=C, rozpocet=B * 1e6).hodnota for B in (30, 60, 120, 240)]
    podle_limitu = [op.vyres(T - C, om, max_zelenina=z).hodnota for z in (0, 100, 200, 400)]
    podle_k = [op.vyres(T - k * C, om).hodnota for k in (0.8, 1.0, 1.2)]
    assert np.all(np.diff(podle_B) >= -1e-3) and np.all(np.diff(podle_limitu) >= -1e-3)
    assert np.all(np.diff(podle_k) <= 1e-3)


def test_stinova_cena_odpovida_zmene_hodnoty(uloha):
    T, C, om = uloha
    r = op.vyres(T - C, om, max_zelenina=100)
    o_ha_vic = op.vyres(T - C, om, max_zelenina=101).hodnota - r.hodnota
    assert r.stin_zelenina == pytest.approx(o_ha_vic, rel=0.05)


def test_hodnota_je_ucel_lp(uloha):
    T, C, om = uloha
    r = op.vyres(T - C, om)
    assert op.hodnota((T - C) @ r.x) == pytest.approx(r.hodnota, rel=1e-3)


def test_minimax_litost_neni_horsi_nez_plan_pro_jeden_scenar(uloha):
    T, C, om = uloha
    marze = [T - k * C for k in (1.0, 1.1, 1.2)]
    x, nejvetsi = op.minimax_litost(marze, om)
    assert x.sum() == pytest.approx(op.ROZLOHA) and x[om.zelenina].sum() <= op.MAX_ZELENINA + 1e-6

    def nejvetsi_litost(y):
        return max(op.vyres(M, om).hodnota - op.hodnota(M @ y) for M in marze)

    assert nejvetsi == pytest.approx(nejvetsi_litost(x), abs=2e3)
    for M in marze:
        assert nejvetsi <= nejvetsi_litost(op.optimalizuj(M, om)) + 2e3


def test_odolny_plan_podle_lambda(uloha):
    T, C, om = uloha
    scenare = [nr.ScenarNakladu("základ", 1.0, 1.0), nr.ScenarNakladu("růst", 1.1, 1.1)]
    marze = [T - nr.naklady_scenare(C, om.zelenina, s) for s in scenare]
    nazvy = [dt.NAZVY[k] for k in dt.KODY]

    tab = nr.krok_odolny_podle_lambda(T, C, om, scenare, nazvy)

    assert tab.columns.tolist() == [f"lambda_{lam}" for lam in nr.LAMBDY_ODOLNEHO_PLANU]
    assert tab.sum(axis=0).to_numpy() == pytest.approx(np.full(5, op.ROZLOHA), abs=0.5)
    assert tab.loc[tab.index.isin(np.array(nazvy)[om.zelenina])].sum(axis=0).max() <= op.MAX_ZELENINA + 0.5
    plan_05, _ = op.minimax_litost(marze, om, lam=0.5)
    assert tab["lambda_0.5"].reindex(nazvy, fill_value=0).to_numpy() == pytest.approx(plan_05, abs=0.05)


def test_cisla_v_textu_odpovidaji_vystupum():
    """DOPLNENI_ZADANI.md musí obsahovat čísla z posledního běhu spust.py."""
    koren = Path(__file__).resolve().parent
    vysledky = koren / "vystupy" / "detaily" / "vysledky.json"
    if not vysledky.exists():
        pytest.skip("nejdřív spusť python3 osevni_plan/spust.py")
    import json
    S = json.loads(vysledky.read_text())["doplneni_zadani"]
    text = (koren / "DOPLNENI_ZADANI.md").read_text()

    def cz(x, mista=1):
        return nr.cz(x, mista).replace("-", "−")

    ocekavane = [
        f"1{{,}}151 / 1{{,}}024 = {cz(S['nasobky_rustu']['růst jako 2022 (15,1 %)'], 3)}",
        f"= {cz(S['min_rozpocet'] / 1e6)}$ mil. Kč",
        f"Původní plán stojí {cz(S['naklady_planu'] / 1e6)} mil. Kč",
        f"Stojí {cz(S['naklady_robustniho_planu'] / 1e6)} mil. Kč",
        f"= {cz(S['k_nulovy_ocekavany_zisk_planu'], 2)}$",
    ]
    for nazev, r in S["scenare"].items():
        for plan in ("puvodni", "prepocitany", "robustni"):
            ocekavane.append(f"{cz(r[plan + '_E'] / 1e6)} / {cz(r[plan + '_CVaR'] / 1e6)} / {cz(100 * r[plan + '_p_ztraty'])} %")
    for plodina, ha in S["doporuceny_plan"].items():
        ocekavane.append(f"{plodina.lower()} {cz(ha, 0)} ha")
    chybi = [o for o in ocekavane if o not in text]
    assert not chybi, chybi
