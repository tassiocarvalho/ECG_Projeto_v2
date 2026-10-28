#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# treinar_classificador.py   (VERSAO SEM scikit-learn — usa SO' numpy)
# -----------------------------------------------------------------------------
# Treina uma arvore de decisao CART (Gini) com numpy puro e EMITE:
#   - classificador_arvore.py  : modelo Python (inteiro, = Verilog)
#   - classificador_arvore.v   : modulo Verilog combinacional (comparadores)
#
# Nao requer scipy nem scikit-learn (que nao compilam em Python 32 bits).
# So' precisa de numpy, que voce ja' tem.
#
# A arvore usa SO' features inteiras (rr_prev, rr_next, rr_ratio_x256), entao
# os limiares sao inteiros e viram comparacoes '<=' identicas nos dois lados.
#
# Uso:
#   python python/treinar_classificador.py --csv python/dados/treino.csv --depth 4
#
# Parametros uteis:
#   --depth N        profundidade maxima da arvore (default 4)
#   --min_leaf N     minimo de amostras por folha (default 10)
#   --balance        compensa classes desbalanceadas (recomendado p/ PVC raro)
# =============================================================================
import argparse
import csv
import os
import sys
import numpy as np

# caminhos fixos a partir da pasta deste script (roda de qualquer lugar)
AQUI    = os.path.dirname(os.path.abspath(__file__))   # python/
PROJETO = os.path.dirname(AQUI)                        # raiz do repositorio
DADOS   = os.path.join(AQUI, "dados")                  # CSVs de treino

FEATURES = ["rr_prev", "rr_next", "rr_ratio_x256", "amp_ratio_x256"]
CLASSES = {0:"N", 1:"SVEB", 2:"VEB", 3:"F", 4:"Q"}
N_CLASSES = 5


def carregar(csv_path, duas_classes=False):
    X, y = [], []
    for row in csv.DictReader(open(csv_path)):
        cls = int(row["classe"])
        # modo 2 classes: descarta "Outro" (classe 2), foca em Normal vs PVC.
        # E' a abordagem mais precisa, pois "Outro" mistura arritmias sem
        # assinatura de RR comum e sabota a separacao.
        if duas_classes and cls == 2:
            continue
        X.append([int(row["rr_prev"]), int(row["rr_next"]),
                  int(row["rr_ratio_x256"]), int(row["amp_ratio_x256"])])
        y.append(cls)
    return np.array(X, dtype=np.int32), np.array(y, dtype=np.int32)


# ---------------------------------------------------------------------------
# Arvore CART (Gini) em numpy puro
# ---------------------------------------------------------------------------
class No:
    __slots__ = ("feat", "thr", "esq", "dir", "classe")
    def __init__(self):
        self.feat = -1; self.thr = 0
        self.esq = None; self.dir = None
        self.classe = -1   # >=0 se folha


def gini_ponderado(y, pesos):
    """Impureza de Gini ponderada por classe."""
    total = pesos[y].sum()
    if total == 0:
        return 0.0
    imp = 1.0
    for c in range(N_CLASSES):
        w_c = pesos[y][y == c].sum()
        p = w_c / total
        imp -= p * p
    return imp


def _gini_linhas(W, tot):
    """Gini de cada linha de W (peso acumulado por classe), mesma ordem de
    operacoes de gini_ponderado (imp = 1 - p0^2 - p1^2 - ...)."""
    imp = np.ones(W.shape[0])
    with np.errstate(divide="ignore", invalid="ignore"):
        for c in range(N_CLASSES):
            p = W[:, c] / tot
            imp = imp - p * p
    return np.where(tot == 0, 0.0, imp)


def melhor_split(X, y, pesos):
    """Acha (feature, limiar) que minimiza o Gini ponderado das duas metades.
    Limiares sao inteiros (pontos medios arredondados p/ baixo).

    Vetorizado: ordena cada feature uma vez e avalia todos os limiares
    candidatos por somas acumuladas, em vez de um laco por limiar. Os
    candidatos empatados com o minimo (diferenca < 1e-9, so' ruido de ponto
    flutuante) sao reavaliados com _g_exato, que repete a aritmetica da busca
    exaustiva original na mesma ordem -> a arvore gerada e' identica."""
    n, d = X.shape
    melhor = (None, None, float("inf"))
    pw = pesos[y]
    tot_c = np.array([pw[y == c].sum() for c in range(N_CLASSES)])
    total_w = tot_c.sum()
    gini_pai = 1.0
    for c in range(N_CLASSES):
        p = tot_c[c] / total_w
        gini_pai -= p * p
    if gini_pai == 0:
        return melhor
    Y1 = np.zeros((n, N_CLASSES))
    Y1[np.arange(n), y] = pw
    cand = []   # (f, limiares, g) por feature, em ordem
    for f in range(d):
        col = X[:, f]
        ordem = np.argsort(col, kind="stable")
        cs = col[ordem]
        fim = np.nonzero(np.diff(cs))[0]       # ultima posicao de cada valor
        if len(fim) == 0:
            continue
        Wl = np.cumsum(Y1[ordem], axis=0)[fim]  # peso por classe a esquerda
        Wr = tot_c[None, :] - Wl
        wl = Wl.sum(axis=1)
        wr = Wr.sum(axis=1)
        g = (wl * _gini_linhas(Wl, wl) + wr * _gini_linhas(Wr, wr)) / total_w
        thr = (cs[fim] + cs[fim + 1]) // 2
        cand.append((f, thr, g))
    if not cand:
        return melhor
    g_min = min(float(g.min()) for _, _, g in cand)
    for f, thr, g in cand:
        for k in np.nonzero(g <= g_min + 1e-9)[0]:
            g_ex = _g_exato(X[:, f], y, pesos, int(thr[k]))
            if g_ex < melhor[2]:
                melhor = (f, int(thr[k]), g_ex)
    return melhor


def _g_exato(col, y, pesos, thr):
    """Gini ponderado de um limiar com a aritmetica da busca original."""
    mask = col <= thr
    yl, yr = y[mask], y[~mask]
    wl = pesos[yl].sum(); wr = pesos[yr].sum()
    return (wl * gini_ponderado(yl, pesos)
            + wr * gini_ponderado(yr, pesos)) / pesos[y].sum()


def classe_majoritaria(y, pesos):
    w = np.array([pesos[y][y == c].sum() for c in range(N_CLASSES)])
    return int(np.argmax(w))


def construir(X, y, pesos, depth, min_leaf):
    no = No()
    if depth == 0 or len(y) < 2 * min_leaf or len(np.unique(y)) == 1:
        no.classe = classe_majoritaria(y, pesos)
        return no
    f, thr, g = melhor_split(X, y, pesos)
    if f is None:
        no.classe = classe_majoritaria(y, pesos)
        return no
    mask = X[:, f] <= thr
    if mask.sum() < min_leaf or (~mask).sum() < min_leaf:
        no.classe = classe_majoritaria(y, pesos)
        return no
    no.feat = f; no.thr = thr
    no.esq = construir(X[mask], y[mask], pesos, depth - 1, min_leaf)
    no.dir = construir(X[~mask], y[~mask], pesos, depth - 1, min_leaf)
    return no


def prever_um(no, x):
    while no.classe < 0:
        no = no.esq if x[no.feat] <= no.thr else no.dir
    return no.classe


def podar(no):
    """Funde nos cujos dois filhos sao folhas da MESMA classe (comparador
    inutil). A funcao da arvore nao muda; so' some hardware redundante."""
    if no.classe >= 0:
        return no
    no.esq = podar(no.esq)
    no.dir = podar(no.dir)
    if no.esq.classe >= 0 and no.esq.classe == no.dir.classe:
        folha = No()
        folha.classe = no.esq.classe
        return folha
    return no


def contar_comparadores(no):
    return 0 if no.classe >= 0 else 1 + contar_comparadores(no.esq) + contar_comparadores(no.dir)


# ---------------------------------------------------------------------------
# Emissao de codigo
# ---------------------------------------------------------------------------
def emitir_python(raiz, path):
    L = ["# -*- coding: utf-8 -*-",
         "# classificador_arvore.py  (GERADO por treinar_classificador.py)",
         "# Arvore de decisao inteira — identica ao classificador_arvore.v",
         "# Entrada: rr_prev, rr_next, rr_ratio_x256, amp_ratio_x256 (inteiros)",
         "# Saida  : 0=N  1=SVEB  2=VEB  3=F  4=Q  (superclasses AAMI EC57)", "",
         "def classificar(rr_prev, rr_next, rr_ratio_x256, amp_ratio_x256):"]
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
    print(f"  [gerado] {path}")


def emitir_verilog(raiz, path):
    L = ["// classificador_arvore.v  (GERADO por treinar_classificador.py)",
         "// Arvore de decisao inteira — identica ao classificador_arvore.py",
         "// Combinacional puro: comparadores + muxes, sem multiplicador.",
         "module classificador_arvore (",
         "    input  wire [31:0] rr_prev,",
         "    input  wire [31:0] rr_next,",
         "    input  wire [31:0] rr_ratio_x256,",
         "    input  wire [31:0] amp_ratio_x256,",
         "    output reg  [2:0]  classe",
         ");", "", "    always @(*) begin"]
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
    print(f"  [gerado] {path}")


def main():
    ap = argparse.ArgumentParser(description="Treina arvore (numpy puro) e gera Python+Verilog")
    ap.add_argument("--csv", default=os.path.join(DADOS, "treino.csv"))
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--min_leaf", type=int, default=10)
    ap.add_argument("--balance", action="store_true",
                    help="balanceamento total (= --balance-forca 1.0)")
    ap.add_argument("--balance-forca", dest="balance_forca", type=float,
                    default=None,
                    help="intensidade do balanceamento 0.0-1.0 "
                         "(0=precisao alta, 1=sensibilidade alta, 0.5=equilibrio)")
    ap.add_argument("--duas-classes", dest="duas_classes", action="store_true",
                    help="treina so' Normal vs Ventricular (descarta 'Outro'); "
                         "mais preciso e clinicamente util")
    ap.add_argument("--out_py", default=os.path.join(AQUI, "classificador_arvore.py"))
    ap.add_argument("--out_v",  default=os.path.join(PROJETO, "classificador_arvore.v"))
    args = ap.parse_args()

    X, y = carregar(args.csv, duas_classes=args.duas_classes)
    dist = np.bincount(np.asarray(y, dtype=np.int32), minlength=N_CLASSES)
    print(f"  Amostras: {len(y)}  | distribuicao: {dist.tolist()}")

    # pesos por classe (balanceamento ajustavel via --balance-forca).
    #   forca=0.0  -> sem balanceamento (favorece Normal, alta precisao)
    #   forca=1.0  -> balanceamento total (favorece arritmias, alta sensibilidade)
    #   valores intermediarios (ex.: 0.5) equilibram sensibilidade vs precisao.
    # --balance liga forca=1.0 (compatibilidade); --balance-forca sobrepoe.
    forca = args.balance_forca
    if args.balance and args.balance_forca is None:
        forca = 1.0
    if forca is None:
        forca = 0.0
    pesos = np.ones(N_CLASSES)
    for c in range(N_CLASSES):
        if dist[c] > 0:
            peso_total = len(y) / (N_CLASSES * dist[c])
            pesos[c] = peso_total ** forca   # interpola entre 1 (forca0) e total (forca1)
    print(f"  Balanceamento (forca={forca}): pesos={[round(float(p),2) for p in pesos]}")

    raiz = construir(X, y, pesos, args.depth, args.min_leaf)
    antes = contar_comparadores(raiz)
    raiz = podar(raiz)
    print(f"  Comparadores: {antes} -> {contar_comparadores(raiz)} (folhas irmas iguais fundidas)")

    # acuracia no treino
    pred = np.array([prever_um(raiz, x) for x in X])
    acc = (pred == y).mean()
    print(f"  Acuracia (treino completo): {acc:.4f}")
    # acuracia por classe (sensibilidade) — importante p/ PVC
    for c in range(N_CLASSES):
        if dist[c] > 0:
            sens = ((pred == c) & (y == c)).sum() / dist[c]
            print(f"    Classe {c} ({CLASSES[c]:<11}): sensibilidade {sens:.3f}  (n={dist[c]})")

    emitir_python(raiz, args.out_py)
    emitir_verilog(raiz, args.out_v)
    print("  Pronto. Os dois arquivos sao equivalentes por construcao.")


if __name__ == "__main__":
    main()
