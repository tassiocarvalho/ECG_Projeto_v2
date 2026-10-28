# -*- coding: utf-8 -*-
# =============================================================================
# estatisticas_v2.py  —  metricas completas, por paciente e com incerteza (DS2)
# -----------------------------------------------------------------------------
# Usa as classes do PROPRIO RTL (dumps do testbench, batimento a batimento):
#   v1: ../validacao/dumps_v1/NNN_rtl.txt
#   v2: ../validacao/dumps/NNN_rtl.txt
# Para cada versao: Se, +P, especificidade e F1 de N/SVEB/VEB (convencao
# focada), IC de 95% por bootstrap de PACIENTES (registros reamostrados com
# reposicao, 5000 vezes), resultados por registro e comparacao pareada v1 x v2.
# Deteccao: Se, +P e falsos positivos por hora.
# Saida: ../validacao/estatisticas_ds2.txt
# =============================================================================
import os
import sys

import numpy as np
import wfdb

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
RAIZ = V2
sys.path[:0] = [AQUI]
from gerar_cache import CACHE, DS2  # noqa: E402
from gerar_treino import BEAT_SYMBOLS, TOLERANCIA, classe_de  # noqa: E402

DUMPS = {"v1": os.path.join(V2, "validacao", "dumps_v1"),
         "v2": os.path.join(V2, "validacao", "dumps")}
NOMES = ["N", "SVEB", "VEB"]
B = 5000


def anotacoes(rec):
    ann = wfdb.rdann(os.path.join(RAIZ, "dados", "mitdb", rec), "atr")
    return [(int(s), y) for s, y in zip(ann.sample, ann.symbol) if y in BEAT_SYMBOLS]


def matriz(rec, dump, anot):
    cl = [tuple(map(int, l.split())) for l in open(os.path.join(dump, f"{rec}_rtl.txt")) if l.strip()]
    a = [x[0] for x in anot]
    m = np.zeros((5, 5), int)
    j = 0
    for amostra, pred in cl:
        while j + 1 < len(a) and abs(a[j + 1] - amostra) <= abs(a[j] - amostra):
            j += 1
        if j < len(a) and abs(a[j] - amostra) <= TOLERANCIA:
            v = classe_de(anot[j][1])
            if v >= 0:
                m[v, pred] += 1
    return m


def metricas(m):
    m3 = m[:3, :3]
    tot = m3.sum()
    out = {}
    for c in range(3):
        vp = m3[c, c]
        fn = m3[c].sum() - vp
        fp = m3[:, c].sum() - vp
        tn = tot - vp - fn - fp
        se = vp / max(vp + fn, 1)
        pp = vp / max(vp + fp, 1)
        sp = tn / max(tn + fp, 1)
        f1 = 2 * se * pp / max(se + pp, 1e-12)
        out[NOMES[c]] = (se, pp, sp, f1)
    return out


def ic(vals):
    return np.percentile(vals, 2.5), np.percentile(vals, 97.5)


if __name__ == "__main__":
    rng = np.random.default_rng(2026)
    mats = {v: {} for v in DUMPS}
    for rec in DS2:
        anot = anotacoes(rec)
        for v, d in DUMPS.items():
            mats[v][rec] = matriz(rec, d, anot)
    L = []
    idx = [rng.integers(0, len(DS2), len(DS2)) for _ in range(B)]
    boot = {}
    for v in DUMPS:
        tot = sum(mats[v].values())
        met = metricas(tot)
        L.append(f"\n=== {v}: DS2 agregado (RTL), IC 95% por bootstrap de pacientes ({B}x)")
        L.append("   classe   Se [IC95]              +P [IC95]              Esp     F1")
        amostras = {c: {"se": [], "pp": []} for c in NOMES}
        for ii in idx:
            mb = sum(mats[v][DS2[i]] for i in ii)
            mb_met = metricas(mb)
            for c in NOMES:
                amostras[c]["se"].append(mb_met[c][0]); amostras[c]["pp"].append(mb_met[c][1])
        boot[v] = amostras
        for c in NOMES:
            se, pp, sp, f1 = met[c]
            a, b = ic(amostras[c]["se"]); a2, b2 = ic(amostras[c]["pp"])
            L.append(f"   {c:<6} {se:.3f} [{a:.2f}-{b:.2f}]     {pp:.3f} [{a2:.2f}-{b2:.2f}]     {sp:.3f}   {f1:.3f}")
    # diferenca pareada VEB v2 - v1 (mesmos pacientes reamostrados)
    d_se = np.array(boot["v2"]["VEB"]["se"]) - np.array(boot["v1"]["VEB"]["se"])
    d_pp = np.array(boot["v2"]["VEB"]["pp"]) - np.array(boot["v1"]["VEB"]["pp"])
    L.append(f"\n=== Diferenca pareada v2 - v1 (VEB): Se {np.mean(d_se):+.3f} [IC95 {ic(d_se)[0]:+.2f}, {ic(d_se)[1]:+.2f}]"
             f"   +P {np.mean(d_pp):+.3f} [IC95 {ic(d_pp)[0]:+.2f}, {ic(d_pp)[1]:+.2f}]")
    # por registro (VEB)
    L.append("\n=== Por registro, VEB (registros com >= 10 VEB anotados)")
    L.append("   reg    n_VEB   v1 Se/+P       v2 Se/+P")
    melhor = pior = 0
    for rec in DS2:
        n = mats["v2"][rec][2, :3].sum()
        if n < 10:
            continue
        m1, m2 = metricas(mats["v1"][rec])["VEB"], metricas(mats["v2"][rec])["VEB"]
        melhor += m2[0] > m1[0] + 1e-9
        pior += m2[0] < m1[0] - 1e-9
        L.append(f"   {rec}  {n:6d}   {m1[0]:.2f}/{m1[1]:.2f}      {m2[0]:.2f}/{m2[1]:.2f}")
    L.append(f"   Se do VEB maior na v2 em {melhor} registros, menor em {pior}")
    # deteccao
    tp = fn = fp = 0
    horas = 0.0
    for rec in DS2:
        z = np.load(os.path.join(CACHE, f"{rec}.npz"))
        picos = np.array(z["picos"]) - 1
        a = np.array([s for s, _ in anotacoes(rec)])
        horas += len(z["ds"]) / 360 / 3600
        usados = np.zeros(len(a), bool)
        for p in picos:
            j = np.searchsorted(a, p)
            cand = [t for t in (j - 1, j) if 0 <= t < len(a) and not usados[t] and abs(a[t] - p) <= TOLERANCIA]
            if cand:
                t = min(cand, key=lambda t: abs(a[t] - p)); usados[t] = True; tp += 1
            else:
                fp += 1
        fn += (~usados).sum()
    L.append(f"\n=== Deteccao (DS2, {horas:.1f} h): Se={tp / (tp + fn):.4f}  +P={tp / (tp + fp):.4f}"
             f"  FN={fn}  FP={fp}  FP/hora={fp / horas:.1f}")
    txt = "\n".join(L)
    print(txt)
    open(os.path.join(V2, "validacao", "estatisticas_ds2.txt"), "w", encoding="utf-8").write(txt + "\n")
