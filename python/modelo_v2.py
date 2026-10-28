# -*- coding: utf-8 -*-
# =============================================================================
# modelo_v2.py  —  GOLDEN MODEL v2 (bit-exato com o RTL v2)
# -----------------------------------------------------------------------------
# Entrada: os sinais internos do datapath v1 (gerar_cache.py): derivada com
# sinal ds[j] de cada amostra j, picos (indice do testbench = j + 1) e o valor
# do MWI no pico. Saida: as 11 caracteristicas de cada batimento classificado,
# na ordem em que o hardware as produz.
#
# Semantica (o RTL v2 implementa exatamente isto):
#
# MEMORIA: a RAM de 256 palavras guarda ds[j] no endereco j mod 256. Amostras
#   de indice negativo valem 0 (RAM zerada pelo reset).
#
# MORFOLOGIA do pico de amostra k (= picos[i] - 1), calculada pelo motor de
#   morfologia quando a amostra max(k+40, r+40) ja' foi gravada:
#   1. r = 1o indice de max |ds[j]| em j in [k-80, k+39]; dmax = |ds[r]|
#   2. largura d_w: a partir de r, estende para os dois lados enquanto
#      |ds| > dmax>>3, sem sair de [k-80, k+39]; d_w = b - a + 1
#   3. S = ds[r-24 .. r+39] (64 amostras); smax = max(S), smin = -min(S)
#      pol = sinal(smax-smin) * (|smax-smin|*256 // max(smax+smin,1))  (trunca)
#   4. molde T (64 amostras, com sinal). 1o pico: T = S, sad_t = 0,
#      polt = pol. Depois: sad_t = sum|S-T|*256 // max(sum|T|,1);
#      polt = pol(T); dpol = |pol - polt|
#   5. atualizacao do molde (so' se o pico NAO e' prematuro, rr_ratio >= 230):
#      T += (S - T) >>> sh, sh = 1 (2o molde), 2 (3o e 4o), 3 (demais)
#      (>>> = deslocamento aritmetico = piso da divisao)
#
# RR (estado atualizado a cada batimento classificado, como na v1):
#   rr_prev = p0-p1, rr_next = p_novo-p0
#   m      = media dos ate' 8 RR anteriores (1o: o proprio rr_prev), min 1
#   rr_ratio      = rr_prev*256 // m        rr_next_ratio = rr_next*256 // m
#   amp_r32       = amp*256 // media das ate' 32 amplitudes anteriores (v1)
#   irr_np        = (soma|dRR| // n) * 256 // max(base,1), com |dRR| medido SO'
#                   entre batimentos NAO prematuros em relacao a' base
#                   (rr_prev*256 >= 230*base): irregularidade do ritmo de base
#                   (alta em fibrilacao atrial, baixa com extrassistoles);
#                   ultimos ate' 8 valores, 0 se nao ha' nenhum
#   base          = media exponencial lenta do RR (1/128), so' com batimentos
#                   nao prematuros (rr_prev*256 >= 230*m); 1o batimento: rr_prev
#   rr_base       = rr_prev*256 // max(base,1)   rr_next_base = rr_next*256 // ...
# =============================================================================
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

PRE, POS = 80, 40          # janela de busca do pico de |ds|: [k-PRE, k+POS-1]
SA, SB = 24, 40            # segmento S: [r-SA, r+SB-1]  (64 amostras)
K_RR, K_AMP, K_IRR = 8, 32, 8
LIM_PREM = 230             # rr_ratio abaixo disto = prematuro
SH_BASE = 7                # base: media exponencial 1/128
FEATURES = ["rr_prev", "rr_next", "rr_ratio", "amp_r32", "sad_t", "dpol", "d_w",
            "irr_np", "rr_next_ratio", "rr_base", "rr_next_base"]


def div_trunc(num, den):
    """Divisao inteira com truncamento em direcao a zero (como o hardware)."""
    q = abs(num) // den
    return q if num >= 0 else -q


def polaridade(seg):
    smax = int(seg.max())
    smin = int(-seg.min())
    return div_trunc((smax - smin) * 256, max(smax + smin, 1))


class Morfologia:
    """Motor de morfologia: estado = molde T e quantos moldes ja' entraram."""

    def __init__(self):
        self.T = None
        self.nT = 0

    def calcula(self, ds, k, prematuro):
        def le(j0, j1):                      # ds[j0..j1-1], indices < 0 valem 0
            out = np.zeros(j1 - j0, np.int64)   # (alem do fim: nunca usado, o
            a = max(j0, 0)                      #  batimento e' descartado)
            seg = ds[a:j1]
            out[a - j0: a - j0 + len(seg)] = seg
            return out
        lo, hi = k - PRE, k + POS
        w = le(lo, hi)
        aw = np.abs(w)
        r = lo + int(np.argmax(aw))          # 1a ocorrencia do maximo
        dmax = int(aw.max())
        lim = dmax >> 3
        a = r
        while a > lo and aw[a - 1 - lo] > lim:
            a -= 1
        b = r
        while b < hi - 1 and aw[b + 1 - lo] > lim:
            b += 1
        S = le(r - SA, r + SB)
        pol = polaridade(S)
        if self.T is None:
            sad_t, dpol = 0, 0
        else:
            sad_t = int(np.abs(S - self.T).sum()) * 256 // max(int(np.abs(self.T).sum()), 1)
            dpol = abs(pol - polaridade(self.T))
        # atualizacao do molde
        if self.T is None:
            self.T = S.copy()
            self.nT = 1
        elif not prematuro:
            sh = 1 if self.nT == 1 else (2 if self.nT <= 3 else 3)
            self.T = self.T + ((S - self.T) >> sh)
            self.nT = min(self.nT + 1, 4)
        return {"sad_t": sad_t, "dpol": dpol, "d_w": b - a + 1, "r": r}


def features_registro(ds, picos, pval, n_amostras=None):
    """Caracteristicas de cada batimento classificado (picos[1..n-2]).
    Devolve lista de (indice_do_pico_no_testbench, dict)."""
    n_amostras = len(ds) if n_amostras is None else n_amostras
    picos = [int(p) for p in picos]
    pval = [int(v) for v in pval]
    morf = Morfologia()
    rr_hist, amp_hist, np_hist = [], [], []
    np_ult = None
    base = None
    saida = []
    # rr_ratio de cada pico (o que o classificador calcula logo apos detecta-lo);
    # pico 0: rr_prev = p0 - 0, media = ele mesmo -> 256
    feats_morf = {}
    pendentes = []

    def media(h):
        return h[-1] if False else (sum(h) // len(h))

    # percorre os picos na ordem do hardware: na deteccao do pico i,
    # (1) classifica o pico i-1 e atualiza o estado; (2) calcula o rr_ratio do
    # pico i (pre-calculo do classificador); (3) 40 amostras depois, a
    # morfologia do pico i usa esse rr_ratio para decidir se e' prematuro.
    for i, p in enumerate(picos):
        # --- (1) classificacao do pico anterior (i-1), feita na deteccao deste
        if i >= 2:
            j = i - 1
            p0, p1 = picos[j], picos[j - 1]
            rpj = p0 - p1
            rn = p - p0
            mj = rpj if not rr_hist else media(rr_hist)
            mj = max(mj, 1)
            ma = pval[j] if not amp_hist else media(amp_hist)
            bref = rpj if base is None else base
            irr = 0 if not np_hist else (sum(np_hist) // len(np_hist)) * 256 // max(bref, 1)
            mfj = feats_morf.get(j)
            if mfj is not None:
                f = {"rr_prev": rpj, "rr_next": rn, "rr_ratio": rpj * 256 // mj,
                     "amp_r32": pval[j] * 256 // max(ma, 1),
                     "sad_t": mfj["sad_t"], "dpol": mfj["dpol"], "d_w": mfj["d_w"],
                     "irr_np": irr, "rr_next_ratio": rn * 256 // mj,
                     "rr_base": rpj * 256 // max(bref, 1), "rr_next_base": rn * 256 // max(bref, 1)}
                saida.append((p0, f))
            # atualiza o estado (com o batimento classificado j)
            if rpj * 256 >= LIM_PREM * max(bref, 1):      # nao prematuro vs base
                if np_ult is not None:
                    np_hist.append(abs(rpj - np_ult))
                    if len(np_hist) > K_IRR:
                        np_hist.pop(0)
                np_ult = rpj
            if base is None:
                base = rpj
            elif rpj * 256 >= LIM_PREM * mj:
                base = base + ((rpj - base) >> SH_BASE) if rpj >= base else base - ((base - rpj) >> SH_BASE)
            rr_hist.append(rpj)
            if len(rr_hist) > K_RR:
                rr_hist.pop(0)
            amp_hist.append(pval[j])
            if len(amp_hist) > K_AMP:
                amp_hist.pop(0)
        # --- (2) rr_ratio do pico i com o estado ja' atualizado
        rp = p - (picos[i - 1] if i > 0 else 0)
        m = max(rp if not rr_hist else media(rr_hist), 1)
        rr_ratio_i = rp * 256 // m
        # --- (3) morfologia do pico i (precisa de amostras ate' max(k+40, r+40))
        k = p - 1
        mf = None
        if k + POS <= n_amostras:
            mf = morf.calcula(ds, k, rr_ratio_i < LIM_PREM)
            if mf["r"] + SB > n_amostras:
                mf = None
        feats_morf[i] = mf
    return saida
