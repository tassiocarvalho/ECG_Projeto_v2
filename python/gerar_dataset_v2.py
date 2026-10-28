# -*- coding: utf-8 -*-
# =============================================================================
# gerar_dataset_v2.py  —  caracteristicas EXATAS (golden model v2) + rotulos
# -----------------------------------------------------------------------------
# Para cada registro: features_registro (modelo_v2) sobre o cache do datapath,
# rotulo AAMI do batimento anotado mais proximo (tolerancia 36 amostras, mesma
# regra e mesmo ponteiro do gerar_treino.py da v1).
# Saida: dados/dataset_v2.csv (44 registros; a coluna registro separa DS1/DS2)
# =============================================================================
import csv
import os
import sys
from multiprocessing import Pool

import numpy as np
import wfdb

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path[:0] = [AQUI]
from gerar_cache import CACHE, DS1, DS2  # noqa: E402
from gerar_treino import BEAT_SYMBOLS, TOLERANCIA, classe_de  # noqa: E402
from modelo_v2 import FEATURES, features_registro  # noqa: E402


def linhas(rec):
    z = np.load(os.path.join(CACHE, f"{rec}.npz"))
    feats = features_registro(z["ds"].astype(np.int64), z["picos"], z["pval"])
    ann = wfdb.rdann(os.path.join(RAIZ, "dados", "mitdb", rec), "atr")
    anot = [(int(s), y) for s, y in zip(ann.sample, ann.symbol) if y in BEAT_SYMBOLS]
    a = [x[0] for x in anot]
    out, j = [], 0
    for amostra, f in feats:
        while j + 1 < len(a) and abs(a[j + 1] - amostra) <= abs(a[j] - amostra):
            j += 1
        if j < len(a) and abs(a[j] - amostra) <= TOLERANCIA:
            c = classe_de(anot[j][1])
            if c >= 0:
                out.append({"registro": rec, "amostra": amostra, **f, "classe": c})
    return out


if __name__ == "__main__":
    with Pool(os.cpu_count()) as p:
        res = p.map(linhas, DS1 + DS2)
    tudo = [l for r in res for l in r]
    os.makedirs(os.path.join(AQUI, "dados"), exist_ok=True)
    out = os.path.join(AQUI, "dados", "dataset_v2.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["registro", "amostra"] + FEATURES + ["classe"])
        w.writeheader()
        w.writerows(tudo)
    n1 = sum(1 for l in tudo if l["registro"] in DS1)
    print(f"  {out}: {len(tudo)} batimentos (DS1 {n1}, DS2 {len(tudo) - n1})")
    ds1 = [l for l in tudo if l["registro"] in DS1]
    for k in FEATURES:
        med = [np.median([l[k] for l in ds1 if l["classe"] == c]) for c in (0, 1, 2)]
        print(f"   DS1 mediana {k:<14} N {med[0]:7.0f}   SVEB {med[1]:7.0f}   VEB {med[2]:7.0f}")
