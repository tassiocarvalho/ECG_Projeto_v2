# -*- coding: utf-8 -*-
# =============================================================================
# selecionar_v2.py  —  SELECAO OFICIAL da v2 (so' DS1, LOPO)
# -----------------------------------------------------------------------------
# Arvore CART (a mesma da v1) sobre as 11 caracteristicas do golden model.
# Grade: profundidade x peso de SVEB x peso de VEB (N, F, Q com peso 1).
# Criterio: F1 macro ESTRITO de N/SVEB/VEB, predicoes agrupadas das 22 rodadas
# (um paciente de DS1 fora por vez). O DS2 nao e' lido.
# Saida: tabela completa em dados/selecao_v2.txt e a escolha na ultima linha.
# =============================================================================
import csv
import os
import sys
from multiprocessing import Pool

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path[:0] = [AQUI]
import treinar_classificador as tc  # noqa: E402
from gerar_cache import DS1  # noqa: E402
from modelo_v2 import FEATURES  # noqa: E402

GRADE = [(d, ws, wv) for d in (5, 6, 7, 8, 9) for ws in (1.0, 1.25, 1.5, 2.0) for wv in (1.0, 1.25, 1.5, 2.0)]
MIN_FOLHA = 10


def metricas(m):
    """F1 estrito + Se/+P na convencao focada (N/SVEB/VEB)."""
    f1, foc = [], []
    for c in (0, 1, 2):
        vp = m[c, c]
        se = vp / max(m[c].sum(), 1)
        pp = vp / max(m[:, c].sum(), 1)
        f1.append(2 * se * pp / (se + pp) if se + pp else 0)
        fn = sum(m[c, k] for k in (0, 1, 2)) - vp
        fp = sum(m[v, c] for v in (0, 1, 2)) - vp
        foc.append((vp / max(vp + fn, 1), vp / max(vp + fp, 1)))
    return float(np.mean(f1)), foc


def carrega():
    lin = [l for l in csv.DictReader(open(os.path.join(AQUI, "dados", "dataset_v2.csv"))) if l["registro"] in DS1]
    X = np.array([[int(l[f]) for f in FEATURES] for l in lin], np.int32)
    y = np.array([int(l["classe"]) for l in lin], np.int32)
    g = np.array([l["registro"] for l in lin])
    return X, y, g


def rodada(a):
    d, ws, wv = a
    X, y, g = carrega()
    w = np.array([1.0, ws, wv, 1.0, 1.0])
    pred = np.empty_like(y)
    for r in np.unique(g):
        tr, te = g != r, g == r
        raiz = tc.construir(X[tr], y[tr], w, d, MIN_FOLHA)
        pred[te] = [tc.prever_um(raiz, x) for x in X[te]]
    m = np.zeros((5, 5), int)
    np.add.at(m, (y, pred), 1)
    s, foc = metricas(m)
    return d, ws, wv, s, foc


if __name__ == "__main__":
    with Pool(max(1, (os.cpu_count() or 2) - 2)) as p:
        res = p.map(rodada, GRADE)
    linhas = ["  depth  wS    wV   | F1 LOPO | N Se/+P     SVEB Se/+P   VEB Se/+P"]
    for d, ws, wv, s, foc in sorted(res, key=lambda r: -r[3]):
        linhas.append(f"   {d:>3} {ws:5.2f} {wv:5.2f} |  {s:.3f}  | " + "  ".join(f"{a:.2f}/{b:.2f}" for a, b in foc))
    d, ws, wv, s, _ = max(res, key=lambda r: r[3])
    linhas.append(f"\n  ESCOLHIDO (so' DS1): depth={d} wS={ws} wV={wv}  F1 LOPO={s:.3f}")
    txt = "\n".join(linhas)
    open(os.path.join(AQUI, "dados", "selecao_v2.txt"), "w", encoding="utf-8").write(txt + "\n")
    print("\n".join(linhas[:16] + linhas[-1:]))
