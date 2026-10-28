# -*- coding: utf-8 -*-
# =============================================================================
# ablacao_v2.py  —  contribuicao de cada caracteristica morfologica
# -----------------------------------------------------------------------------
# Treina a mesma arvore do modelo final (CART inteiro, profundidade 7, pesos
# N=1 SVEB=1 VEB=1.5, so' DS1) removendo caracteristicas, e avalia no DS2 com
# as caracteristicas do golden model (dados/dataset_v2.csv). Os
# hiperparametros NAO sao reselecionados por variante: mede-se o efeito da
# caracteristica com o resto do procedimento fixo.
# Saida: ../validacao/ablacao_ds2.txt
# Uso: python python/ablacao_v2.py
# =============================================================================
import csv
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
from gerar_cache import DS1, DS2  # noqa: E402
from modelo_v2 import FEATURES  # noqa: E402
import treinar_classificador as tc  # noqa: E402
from treinar_v2 import MIN_FOLHA  # noqa: E402

DEPTH, PESOS = 7, np.array([1.0, 1.0, 1.5, 1.0, 1.0])
MORF = ["sad_t", "dpol", "d_w"]
VARIANTES = [("todas (modelo final)", []),
             ("sem sad_t", ["sad_t"]),
             ("sem dpol", ["dpol"]),
             ("sem d_w", ["d_w"]),
             ("sem morfologia (sad_t, dpol, d_w)", MORF),
             ("sem irr_np", ["irr_np"]),
             ("sem base lenta (rr_base, rr_next_base)", ["rr_base", "rr_next_base"])]


def metricas(y, p):
    out = {}
    sel = y < 3
    for c, n in enumerate(["N", "SVEB", "VEB"]):
        vp = np.sum(sel & (y == c) & (p == c))
        fn = np.sum(sel & (y == c) & (p != c) & (p < 3))
        fp = np.sum(sel & (y != c) & (p == c))
        out[n] = (vp / max(vp + fn, 1), vp / max(vp + fp, 1))
    return out


if __name__ == "__main__":
    lin = list(csv.DictReader(open(os.path.join(AQUI, "dados", "dataset_v2.csv"))))
    tr = [l for l in lin if l["registro"] in DS1]
    te = [l for l in lin if l["registro"] in DS2]
    ytr = np.array([int(l["classe"]) for l in tr])
    yte = np.array([int(l["classe"]) for l in te])
    L = [f"  Ablacao (treino DS1, teste DS2, depth={DEPTH}, pesos SVEB=1 VEB=1.5, {len(te)} batimentos de teste)",
         f"   {'variante':<42} {'comparadores':>12}   {'VEB Se/+P':>11}   {'SVEB Se/+P':>11}   {'N Se/+P':>11}"]
    for nome, fora in VARIANTES:
        fs = [f for f in FEATURES if f not in fora]
        Xtr = np.array([[int(l[f]) for f in fs] for l in tr], np.int32)
        Xte = np.array([[int(l[f]) for f in fs] for l in te], np.int32)
        raiz = tc.podar(tc.construir(Xtr, ytr, PESOS, DEPTH, MIN_FOLHA))
        p = np.array([tc.prever_um(raiz, x) for x in Xte])
        m = metricas(yte, p)
        L.append(f"   {nome:<42} {tc.contar_comparadores(raiz):>12}   "
                 + "   ".join(f"{m[c][0]:.3f}/{m[c][1]:.3f}" for c in ["VEB", "SVEB", "N"]))
        print(L[-1], flush=True)
    txt = "\n".join(L)
    open(os.path.join(V2, "validacao", "ablacao_ds2.txt"), "w", encoding="utf-8").write(txt + "\n")
