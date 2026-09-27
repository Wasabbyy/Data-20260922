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
