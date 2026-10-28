# -*- coding: utf-8 -*-
# =============================================================================
# gerar_cache.py  —  v2: grava, por registro, os sinais internos do datapath
# -----------------------------------------------------------------------------
# Roda o modelo bit-a-bit (pan_tompkins_hw) sobre a entrada causal (ganho fixo,
# dados/verilog_mem) e grava em cache/NNN.npz:
#   f    : saida do filtro (media de 3)            por amostra
#   ds   : derivada COM SINAL (2x0+x1-x3-2x4)       por amostra
#   mwi  : saida do integrador                      por amostra
#   picos: indice de cada pico (convencao do testbench, idx + TB_INDEX_OFFSET)
#   pval : valor do MWI no pico (amp_mwi)
# Os sinais sao exatamente os que o hardware v2 tera disponiveis.
#
# Uso: python python/gerar_cache.py
# =============================================================================
import os
import sys
from multiprocessing import Pool

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
MEM = os.path.join(RAIZ, "dados", "verilog_mem")
CACHE = os.path.join(AQUI, "cache")
sys.path.insert(0, AQUI)

from pan_tompkins_hw import ECGProcessorHW, ler_mem, TB_INDEX_OFFSET, to_signed  # noqa: E402

DS1 = ["101", "106", "108", "109", "112", "114", "115", "116", "118", "119", "122",
       "124", "201", "203", "205", "207", "208", "209", "215", "220", "223", "230"]
DS2 = ["100", "103", "105", "111", "113", "117", "121", "123", "200", "202", "210",
       "212", "213", "214", "219", "221", "222", "228", "231", "232", "233", "234"]


def processa(rec):
    destino = os.path.join(CACHE, f"{rec}.npz")
    if os.path.exists(destino):
        return rec, "cache"
    x = ler_mem(os.path.join(MEM, f"{rec}_ecg.mem"))
    n = len(x)
    hw = ECGProcessorHW()
    f = np.empty(n, np.int32)
    ds = np.empty(n, np.int32)
    mwi = np.empty(n, np.int32)
    picos, pval = [], []
    for k in range(n):
        # derivada com sinal calculada com os registradores ANTES do passo,
        # como o derivator.v (mesma expressao que gera o |d|)
        fo = hw._filter(int(x[k]))
        d = (2 * to_signed(hw.d_x0, 32) + to_signed(hw.d_x1, 32)
             - to_signed(hw.d_x3, 32) - 2 * to_signed(hw.d_x4, 32))
        dd = hw._derivator(fo)
        i = hw._integrator(dd)
        if hw._peak_detector(i):
            picos.append(k + TB_INDEX_OFFSET)
            pval.append(hw.p_value)
        f[k] = fo
        ds[k] = d
        mwi[k] = i
    np.savez_compressed(destino, f=f, ds=ds, mwi=mwi,
                        picos=np.array(picos, np.int64), pval=np.array(pval, np.int64))
    return rec, len(picos)


if __name__ == "__main__":
    os.makedirs(CACHE, exist_ok=True)
    with Pool(os.cpu_count()) as p:
        for rec, info in p.imap_unordered(processa, DS1 + DS2):
            print(f"  {rec}: {info}", flush=True)
