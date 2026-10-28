# -*- coding: utf-8 -*-
# =============================================================================
# intermediaria_incart.py  —  versao intermediaria (anterior a consulta ao DS2)
#                             avaliada na base externa INCART
# -----------------------------------------------------------------------------
# A versao intermediaria foi selecionada so' no DS1 (conjunto H: as mesmas 11
# caracteristicas do modelo final, com a irregularidade rr_irreg medida sobre
# TODOS os intervalos no lugar de irr_np; depth 6, pesos SVEB 1,5 e VEB 1,5)
# e avaliada uma unica vez no DS2 (validacao/ds2_golden.txt). Nenhuma decisao
# dela usou o DS2 ou a INCART, entao a INCART e' um teste do pipeline inteiro
# sem influencia do DS2.
# Fidelidade: a reconstrucao deve reproduzir EXATAMENTE a matriz do DS2 de
# validacao/ds2_golden.txt antes de ser aplicada a' INCART.
# Saida: ../validacao/intermediaria_incart.txt
# Uso: python python/intermediaria_incart.py
# =============================================================================
import csv
import os
import sys
from multiprocessing import Pool

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import modelo_v2 as mv  # noqa: E402
import treinar_classificador as tc  # noqa: E402
from gerar_cache import CACHE, DS1, DS2  # noqa: E402
from gerar_treino import BEAT_SYMBOLS, TOLERANCIA, classe_de  # noqa: E402

FEAT_INT = ["rr_prev", "rr_next", "rr_ratio", "amp_r32", "sad_t", "dpol", "d_w",
            "rr_irreg", "rr_next_ratio", "rr_base", "rr_next_base"]
DEPTH, PESOS, MIN_FOLHA = 6, np.array([1.0, 1.5, 1.5, 1.0, 1.0]), 10
CACHE_INCART = os.path.join(AQUI, "cache_incart_ac")


def rr_irreg_registro(picos):
    """rr_irreg de cada batimento classificado (mesma ordem de atualizacao do
    golden): media dos ultimos 8 |RR_k - RR_k-1| * 256 / media local de RR."""
    picos = [int(p) for p in picos]
    rr_hist, irr_hist, out = [], [], {}
    rr_ant = None
    for i, p in enumerate(picos):
        if i >= 2:
            j = i - 1
            rpj = picos[j] - picos[j - 1]
            mj = max(rpj if not rr_hist else sum(rr_hist) // len(rr_hist), 1)
            out[picos[j]] = 0 if not irr_hist else (sum(irr_hist) // len(irr_hist)) * 256 // mj
            if rr_ant is not None:
                irr_hist.append(abs(rpj - rr_ant))
                if len(irr_hist) > mv.K_IRR:
                    irr_hist.pop(0)
            rr_ant = rpj
            rr_hist.append(rpj)
            if len(rr_hist) > mv.K_RR:
                rr_hist.pop(0)
    return out


def caracteristicas(z):
    """features do golden (modelo final) com irr_np trocada por rr_irreg."""
    irr = rr_irreg_registro(z["picos"])
    res = []
    for p, f in mv.features_registro(z["ds"].astype(np.int64), z["picos"], z["pval"]):
        g = dict(f)
        g["rr_irreg"] = irr[p]
        res.append((p, g))
    return res


def mitbih(rec):
    z = np.load(os.path.join(CACHE, f"{rec}.npz"))
    return rec, {p: g for p, g in caracteristicas(z)}


def incart(args):
    rec, raiz = args
    z = np.load(os.path.join(CACHE_INCART, f"{rec}.npz"))
    cl = [(p, tc.prever_um(raiz, np.array([g[k] for k in FEAT_INT]))) for p, g in caracteristicas(z)]
    anot = [(int(s), str(y)) for s, y in zip(z["ann_s"], z["ann_y"]) if str(y) in BEAT_SYMBOLS]
    a = [x[0] for x in anot]
    conf = np.zeros((5, 5), int)
    j = 0
    for amostra, pred in cl:
        while j + 1 < len(a) and abs(a[j + 1] - amostra) <= abs(a[j] - amostra):
            j += 1
        if j < len(a) and abs(a[j] - amostra) <= TOLERANCIA:
            v = classe_de(anot[j][1])
            if v >= 0:
                conf[v, pred] += 1
    return rec, conf


def metricas(m):
    out = []
    for c in range(3):
        vp = m[c, c]
        out.append((vp / max(m[c, :3].sum(), 1), vp / max(m[:3, c].sum(), 1)))
    return out


if __name__ == "__main__":
    lin = list(csv.DictReader(open(os.path.join(AQUI, "dados", "dataset_v2.csv"))))
    with Pool(2) as p:
        feats = dict(p.map(mitbih, DS1 + DS2))
    X = {"ds1": [], "ds2": []}; y = {"ds1": [], "ds2": []}
    for l in lin:
        conj = "ds1" if l["registro"] in DS1 else "ds2"
        g = feats[l["registro"]][int(l["amostra"])]
        X[conj].append([g[k] for k in FEAT_INT]); y[conj].append(int(l["classe"]))
    raiz = tc.podar(tc.construir(np.array(X["ds1"], np.int64), np.array(y["ds1"]), PESOS, DEPTH, MIN_FOLHA))
    pred = np.array([tc.prever_um(raiz, np.array(x)) for x in X["ds2"]])
    m2 = np.zeros((5, 5), int)
    for t, q in zip(y["ds2"], pred):
        m2[t, q] += 1
    ref = np.array([[42709, 490, 929, 13, 0], [1539, 138, 132, 15, 0], [263, 19, 2801, 0, 0]])
    fiel = np.array_equal(m2[:3], ref)
    L = ["  Versao intermediaria (selecionada so' no DS1; rr_irreg; depth 6, pesos 1.5/1.5)",
         f"  arvore: {tc.contar_comparadores(raiz)} comparadores",
         f"  DS2 reconstruido = validacao/ds2_golden.txt: {'SIM' if fiel else 'NAO'}"]
    L += ["   DS2  " + "  ".join(f"{n} {se:.3f}/{pp:.3f}" for n, (se, pp) in zip(["N", "SVEB", "VEB"], metricas(m2)))]
    if fiel:
        with Pool(2) as p:
            res = p.map(incart, [(r, raiz) for r in sorted(f[:-4] for f in os.listdir(CACHE_INCART))])
        mi = sum(r[1] for r in res)
        L += [f"   INCART ({len(res)} registros)  " + "  ".join(
            f"{n} {se:.3f}/{pp:.3f}" for n, (se, pp) in zip(["N", "SVEB", "VEB"], metricas(mi)))]
        # IC 95% por bootstrap de pacientes (registros do mesmo paciente juntos)
        import externo_incart as ei
        pac = {}
        for rec, m in res:
            pac.setdefault(ei.paciente(rec), []).append(m)
        mats = [sum(v) for v in pac.values()]
        rng = np.random.default_rng(2026)
        bs = [metricas(sum(mats[i] for i in rng.integers(0, len(mats), len(mats))))[2] for _ in range(5000)]
        se0, se1 = np.percentile([b[0] for b in bs], [2.5, 97.5])
        pp0, pp1 = np.percentile([b[1] for b in bs], [2.5, 97.5])
        L += [f"   INCART VEB IC95 por paciente ({len(mats)}): Se [{se0:.2f}-{se1:.2f}]  +P [{pp0:.2f}-{pp1:.2f}]"]
        L += ["   matriz INCART (N SVEB VEB F Q):"] + ["     " + " ".join(f"{v:>7}" for v in mi[i]) for i in range(5)]
    txt = "\n".join(L)
    print(txt)
    open(os.path.join(V2, "validacao", "intermediaria_incart.txt"), "w", encoding="utf-8").write(txt + "\n")
