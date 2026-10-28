# -*- coding: utf-8 -*-
# =============================================================================
# treinar_v2.py  —  treina a arvore FINAL da v2 (DS1 inteiro) e gera o codigo
# -----------------------------------------------------------------------------
# Usa a configuracao escolhida por selecionar_v2.py (so' DS1). Funde nos cujos
# dois filhos sao folhas da mesma classe e emite:
#   python/classificador_arvore_v2.py   (golden model da arvore)
#   rtl/classificador_arvore_v2.v       (combinacional, 11 entradas)
# Uso: python treinar_v2.py --depth D --ws WS --wv WV
# =============================================================================
import argparse
import csv
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
RAIZ = V2
sys.path[:0] = [AQUI]
import treinar_classificador as tc  # noqa: E402
from gerar_cache import DS1  # noqa: E402
from modelo_v2 import FEATURES  # noqa: E402

MIN_FOLHA = 10


def emitir_python(raiz, path, cabecalho):
    L = ["# -*- coding: utf-8 -*-",
         "# classificador_arvore_v2.py  (GERADO por treinar_v2.py)",
         f"# {cabecalho}",
         "# Arvore de decisao inteira — identica a rtl/classificador_arvore_v2.v",
         "# Saida: 0=N 1=SVEB 2=VEB 3=F 4=Q (superclasses AAMI EC57)", "",
         f"FEATURES = {FEATURES!r}", "",
         f"def classificar({', '.join(FEATURES)}):"]

    def rec(no, dep):
        ind = "    " * (dep + 1)
        if no.classe >= 0:
            L.append(f"{ind}return {no.classe}")
        else:
            L.append(f"{ind}if {FEATURES[no.feat]} <= {no.thr}:")
            rec(no.esq, dep + 1)
            L.append(f"{ind}else:")
            rec(no.dir, dep + 1)
    rec(raiz, 0)
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


def emitir_verilog(raiz, path, cabecalho):
    L = ["// classificador_arvore_v2.v  (GERADO por python/treinar_v2.py)",
         f"// {cabecalho}",
         "// Arvore de decisao inteira — identica a python/classificador_arvore_v2.py",
         "// Combinacional: comparadores com constantes + multiplexadores.",
         "module classificador_arvore_v2 ("]
    L += [f"    input  wire [31:0] {f}," for f in FEATURES]
    L += ["    output reg  [2:0]  classe", ");", "", "    always @(*) begin"]

    def rec(no, dep):
        ind = "    " * (dep + 2)
        if no.classe >= 0:
            L.append(f"{ind}classe = 3'd{no.classe};")
        else:
            L.append(f"{ind}if ({FEATURES[no.feat]} <= {no.thr}) begin")
            rec(no.esq, dep + 1)
            L.append(f"{ind}end else begin")
            rec(no.dir, dep + 1)
            L.append(f"{ind}end")
    rec(raiz, 0)
    L += ["    end", "", "endmodule", ""]
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, required=True)
    ap.add_argument("--ws", type=float, required=True)
    ap.add_argument("--wv", type=float, required=True)
    a = ap.parse_args()
    lin = [l for l in csv.DictReader(open(os.path.join(AQUI, "dados", "dataset_v2.csv"))) if l["registro"] in DS1]
    X = np.array([[int(l[f]) for f in FEATURES] for l in lin], np.int32)
    y = np.array([int(l["classe"]) for l in lin], np.int32)
    w = np.array([1.0, a.ws, a.wv, 1.0, 1.0])
    raiz = tc.construir(X, y, w, a.depth, MIN_FOLHA)
    antes = tc.contar_comparadores(raiz)
    raiz = tc.podar(raiz)
    n = tc.contar_comparadores(raiz)
    cab = f"DS1 inteiro, depth={a.depth}, pesos N=1 SVEB={a.ws} VEB={a.wv}, {n} comparadores"
    emitir_python(raiz, os.path.join(AQUI, "classificador_arvore_v2.py"), cab)
    emitir_verilog(raiz, os.path.join(V2, "rtl", "classificador_arvore_v2.v"), cab)
    print(f"  arvore: {antes} -> {n} comparadores (nos redundantes fundidos)")

    def feats_usadas(no, s):
        if no.classe < 0:
            s.add(FEATURES[no.feat]); feats_usadas(no.esq, s); feats_usadas(no.dir, s)
        return s
    print(f"  caracteristicas usadas: {sorted(feats_usadas(raiz, set()))}")
    print("  gerados: python/classificador_arvore_v2.py e rtl/classificador_arvore_v2.v")
