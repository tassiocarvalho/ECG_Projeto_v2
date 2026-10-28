# -*- coding: utf-8 -*-
# =============================================================================
# incart_filtro.py  —  o passa-altas de entrada da INCART altera a classificacao?
# -----------------------------------------------------------------------------
# O acoplamento AC (0,05 Hz) foi introduzido porque o nivel DC da derivacao II
# saturava a entrada de 16 bits. Este teste separa os dois efeitos: nos
# registros que NAO saturam sem o filtro, processa o mesmo sinal com e sem o
# passa-altas e compara deteccao e classificacao. Se forem equivalentes, o
# filtro apenas evita a saturacao e nao "ajusta" o resultado.
# Saida: ../validacao/incart_filtro.txt
# Uso: python python/incart_filtro.py
# =============================================================================
import os
import sys
from multiprocessing import Pool

import numpy as np
import wfdb
from scipy.signal import resample_poly

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import externo_incart as e  # noqa: E402

CACHE_SEM = os.path.join(AQUI, "cache_incart_semac")


def saturacao(rec):
    h = wfdb.rdheader(os.path.join(e.INCART, rec))
    r = wfdb.rdrecord(os.path.join(e.INCART, rec), physical=False, channels=[h.sig_name.index(e.DERIVACAO)])
    mv = (r.d_signal[:, 0].astype(np.float64) - r.adc_zero[0]) / r.adc_gain[0]
    x = np.round(32768 + resample_poly(mv, e.UP, e.DOWN) * e.UNID_POR_MV)
    return rec, float(np.mean((x < 0) | (x > 65535)))


def prepara_sem(rec):
    e.CACHE = CACHE_SEM
    e.MEM = os.path.join(os.path.dirname(e.MEM), "incart_mem_semac")
    e.acopla_ac = lambda x, fs=360.0: x          # sem passa-altas
    return e.prepara(rec)


def avalia(args):
    rec, cache = args
    e.CACHE = cache
    return e.avalia(rec)


if __name__ == "__main__":
    with Pool(2) as p:
        sat = dict(p.map(saturacao, e.registros()))
    limpos = sorted(r for r, s in sat.items() if s == 0.0)
    os.makedirs(CACHE_SEM, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(e.MEM), "incart_mem_semac"), exist_ok=True)
    with Pool(2) as p:
        list(p.imap_unordered(prepara_sem, limpos))
        com = p.map(avalia, [(r, e.CACHE) for r in limpos])
        sem = p.map(avalia, [(r, CACHE_SEM) for r in limpos])
    L = [f"  INCART: {len(limpos)} de {len(sat)} registros sem nenhuma amostra saturada sem o filtro",
         f"  registros: {' '.join(limpos)}",
         "   pipeline            deteccao Se/+P        VEB Se/+P       N Se/+P        SVEB Se/+P"]
    for nome, res in (("com passa-altas", com), ("sem passa-altas", sem)):
        m = sum(x[1] for x in res)
        tp = sum(x[2] for x in res); na = sum(x[3] for x in res); fp = sum(x[4] for x in res)
        met = e.metricas(m)
        L.append(f"   {nome:<18}  {tp / na:.4f}/{tp / (tp + fp):.4f}     "
                 + "     ".join(f"{met[c][0]:.3f}/{met[c][1]:.3f}" for c in ("VEB", "N", "SVEB")))
    iguais = sum(np.array_equal(a[1], b[1]) for a, b in zip(com, sem))
    L.append(f"  matrizes de confusao identicas em {iguais} de {len(limpos)} registros")
    txt = "\n".join(L)
    print(txt)
    open(os.path.join(os.path.dirname(AQUI), "validacao", "incart_filtro.txt"), "w", encoding="utf-8").write(txt + "\n")
