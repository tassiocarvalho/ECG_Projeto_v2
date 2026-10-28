# -*- coding: utf-8 -*-
# =============================================================================
# validar_v2.py  —  RTL v2 x golden model, batimento a batimento + metricas
# -----------------------------------------------------------------------------
# Para cada registro: classes do golden model (modelo_v2 + arvore v2) contra o
# dump do classificar_v2_tb.v ("amostra classe"). Se o dump existir, compara;
# monta a matriz de confusao (contra o .atr) do golden e, se houver dumps de
# todos, do RTL.
# Uso:
#   python python/validar_v2.py --records 100 --n 50000   (teste curto)
#   python python/validar_v2.py --conjunto ds2 --saida validacao/resultado_ds2_rtl.txt
# =============================================================================
import argparse
import os
import sys

import numpy as np
import wfdb

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
RAIZ = V2
sys.path[:0] = [AQUI]
from classificador_arvore_v2 import FEATURES as FT, classificar  # noqa: E402
from gerar_cache import CACHE, DS1, DS2  # noqa: E402
from gerar_treino import BEAT_SYMBOLS, TOLERANCIA, classe_de  # noqa: E402
from modelo_v2 import FEATURES, features_registro  # noqa: E402

assert FT == FEATURES
NOMES = {0: "N", 1: "SVEB", 2: "VEB", 3: "F", 4: "Q"}


def golden(rec, n=None):
    z = np.load(os.path.join(CACHE, f"{rec}.npz"))
    ds = z["ds"].astype(np.int64)
    picos, pval = list(z["picos"]), list(z["pval"])
    if n is not None:
        ds = ds[:n]
        keep = [i for i, p in enumerate(picos) if p - 1 < n]
        picos = [picos[i] for i in keep]
        pval = [pval[i] for i in keep]
    return [(p, classificar(*[f[k] for k in FEATURES])) for p, f in features_registro(ds, picos, pval)]


def casar(cl, rec, conf):
    ann = wfdb.rdann(os.path.join(RAIZ, "dados", "mitdb", rec), "atr")
    anot = [(int(s), y) for s, y in zip(ann.sample, ann.symbol) if y in BEAT_SYMBOLS]
    a = [x[0] for x in anot]
    j = 0
    for amostra, pred in cl:
        while j + 1 < len(a) and abs(a[j + 1] - amostra) <= abs(a[j] - amostra):
            j += 1
        if j < len(a) and abs(a[j] - amostra) <= TOLERANCIA:
            v = classe_de(anot[j][1])
            if v >= 0:
                conf[v][pred] += 1


def metricas(conf):
    m = np.array(conf)
    linhas = []
    for c in (0, 1, 2):
        vp = m[c, c]
        fn = sum(m[c, k] for k in (0, 1, 2)) - vp
        fp = sum(m[v, c] for v in (0, 1, 2)) - vp
        linhas.append(f"   {NOMES[c]:<5} Se={vp / max(vp + fn, 1):.3f}  +P={vp / max(vp + fp, 1):.3f}  (n={vp + fn})")
    tot3 = sum(m[v, p] for v in (0, 1, 2) for p in (0, 1, 2))
    linhas.append(f"   Acuracia N/SVEB/VEB: {sum(m[c, c] for c in (0, 1, 2)) / max(tot3, 1):.4f}")
    return linhas


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", nargs="*")
    ap.add_argument("--conjunto", choices=["ds1", "ds2"])
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--dumps", default=os.path.join(V2, "validacao", "dumps"))
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    recs = a.records or (DS1 if a.conjunto == "ds1" else DS2)
    rel = [f"   {'Reg':<6}{'RTL':>7}{'golden':>8}{'iguais':>8}  situacao"]
    conf_g = [[0] * 5 for _ in range(5)]
    conf_r = [[0] * 5 for _ in range(5)]
    todos_rtl, ok = True, 0
    for rec in recs:
        g = golden(rec, a.n)
        casar(g, rec, conf_g)
        dump = os.path.join(a.dumps, f"{rec}_rtl.txt")
        if not os.path.isfile(dump):
            todos_rtl = False
            rel.append(f"   {rec:<6}{'-':>7}{len(g):>8}{'-':>8}  sem dump")
            continue
        r = [tuple(map(int, l.split())) for l in open(dump) if l.strip()]
        iguais = sum(1 for x, y in zip(r, g) if x == y)
        idem = len(r) == len(g) == iguais
        ok += idem
        rel.append(f"   {rec:<6}{len(r):>7}{len(g):>8}{iguais:>8}  {'IDENTICO' if idem else 'DIVERGE'}")
        if not idem:
            dif = next((k for k, (x, y) in enumerate(zip(r, g)) if x != y), min(len(r), len(g)))
            rel.append(f"          1a diferenca no batimento {dif}: RTL {r[dif] if dif < len(r) else '-'}"
                       f"  golden {g[dif] if dif < len(g) else '-'}")
        casar(r, rec, conf_r)
    rel.append(f"\n   Registros identicos: {ok}/{len(recs)}")
    rel.append("\n   MATRIZ DO GOLDEN MODEL (linha=real, coluna=predito: N SVEB VEB F Q)")
    rel += ["   " + f"{NOMES[v]:<5}" + "".join(f"{conf_g[v][p]:>8}" for p in range(5)) for v in range(5)]
    rel.append("   Metricas (convencao focada N/SVEB/VEB):")
    rel += metricas(conf_g)
    if todos_rtl:
        rel.append(f"\n   Matriz do RTL identica a do golden: {'SIM' if conf_r == conf_g else 'NAO'}")
    texto = "\n".join(rel)
    print(texto)
    if a.saida:
        os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
        open(a.saida, "w", encoding="utf-8").write(texto + "\n")
