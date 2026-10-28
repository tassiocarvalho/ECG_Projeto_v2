# -*- coding: utf-8 -*-
# =============================================================================
# externo_svdb.py  —  VALIDACAO EXTERNA na MIT-BIH Supraventricular (SVDB)
# -----------------------------------------------------------------------------
# A SVDB (78 registros de 30 min, 128 Hz) nao participa de nenhuma decisao:
# serve so' de teste final do modelo congelado.
#
# preparar : reamostra o canal ECG1 de 128 para 360 Hz (polifasico 45/16) e
#            converte para a mesma escala da entrada MIT-BIH (6400 unidades/mV,
#            linha de base em 32768, 16 bits), gerando dados/svdb_mem/
#            NNN_ecg.mem; roda o datapath bit a bit e grava cache_svdb/NNN.npz
#            (com as anotacoes ja' convertidas para 360 Hz).
# avaliar  : caracteristicas (modelo_v2) + arvore congelada -> matriz e Se/+P.
# Uso: python externo_svdb.py preparar | avaliar [--saida arq]
# =============================================================================
import argparse
import os
import sys
from multiprocessing import Pool

import numpy as np
import wfdb
from scipy.signal import resample_poly

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
RAIZ = V2
sys.path[:0] = [AQUI]
from gerar_treino import BEAT_SYMBOLS, TOLERANCIA, classe_de  # noqa: E402
from pan_tompkins_hw import ECGProcessorHW, TB_INDEX_OFFSET, to_signed  # noqa: E402

SVDB = os.path.join(V2, "dados", "svdb")
MEM = os.path.join(V2, "dados", "svdb_mem")
CACHE = os.path.join(AQUI, "cache_svdb")
UNID_POR_MV = 6400          # = 200 unidades/mV (ADC MIT-BIH) x 32
FS_IN, UP, DOWN = 128, 45, 16


def registros():
    return sorted(f[:-4] for f in os.listdir(SVDB) if f.endswith(".hea"))


def prepara(rec):
    destino = os.path.join(CACHE, f"{rec}.npz")
    if os.path.exists(destino):
        return rec, "cache"
    r = wfdb.rdrecord(os.path.join(SVDB, rec), physical=False, channels=[0])
    adc = r.d_signal[:, 0].astype(np.float64)
    mv = (adc - r.adc_zero[0]) / r.adc_gain[0]
    x = resample_poly(mv, UP, DOWN)
    amostras = np.clip(np.round(32768 + x * UNID_POR_MV), 0, 65535).astype(np.int64)
    with open(os.path.join(MEM, f"{rec}_ecg.mem"), "w") as f:
        f.write("\n".join(f"{v:04x}" for v in amostras) + "\n")
    hw = ECGProcessorHW()
    n = len(amostras)
    ds = np.empty(n, np.int32)
    picos, pval = [], []
    for k in range(n):
        fo = hw._filter(int(amostras[k]))
        d = (2 * to_signed(hw.d_x0, 32) + to_signed(hw.d_x1, 32)
             - to_signed(hw.d_x3, 32) - 2 * to_signed(hw.d_x4, 32))
        i = hw._integrator(hw._derivator(fo))
        if hw._peak_detector(i):
            picos.append(k + TB_INDEX_OFFSET)
            pval.append(hw.p_value)
        ds[k] = d
    ann = wfdb.rdann(os.path.join(SVDB, rec), "atr")
    a_s = np.round(np.array(ann.sample) * UP / DOWN).astype(np.int64)
    np.savez_compressed(destino, ds=ds, picos=np.array(picos, np.int64), pval=np.array(pval, np.int64),
                        ann_s=a_s, ann_y=np.array(ann.symbol))
    return rec, len(picos)


def avalia(rec):
    from classificador_arvore_v2 import classificar
    from modelo_v2 import FEATURES, features_registro
    z = np.load(os.path.join(CACHE, f"{rec}.npz"))
    cl = [(p, classificar(*[f[k] for k in FEATURES]))
          for p, f in features_registro(z["ds"].astype(np.int64), z["picos"], z["pval"])]
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
    # deteccao
    picos = np.array(z["picos"]) - 1
    tp = sum(1 for s in a if len(picos) and np.min(np.abs(picos - s)) <= TOLERANCIA)
    return rec, conf, tp, len(a), len(picos)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["preparar", "avaliar"])
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    if a.acao == "preparar":
        os.makedirs(MEM, exist_ok=True)
        os.makedirs(CACHE, exist_ok=True)
        with Pool(os.cpu_count()) as p:
            for rec, info in p.imap_unordered(prepara, registros()):
                print(f"  {rec}: {info}", flush=True)
    else:
        with Pool(os.cpu_count()) as p:
            res = p.map(avalia, registros())
        conf = sum(r[1] for r in res)
        tp = sum(r[2] for r in res); nan = sum(r[3] for r in res); npk = sum(r[4] for r in res)
        L = [f"  SVDB (validacao externa): {len(res)} registros",
             f"  Deteccao: Se={tp / nan:.4f}  +P~={tp / max(npk, 1):.4f}",
             "  MATRIZ (linha=real, coluna=predito: N SVEB VEB F Q)"]
        L += ["   " + f"{n:<5}" + "".join(f"{conf[v, k]:>8}" for k in range(5))
              for v, n in enumerate(["N", "SVEB", "VEB", "F", "Q"])]
        for c, n in zip((0, 1, 2), ("N", "SVEB", "VEB")):
            vp = conf[c, c]
            fn = sum(conf[c, k] for k in (0, 1, 2)) - vp
            fp = sum(conf[v, c] for v in (0, 1, 2)) - vp
            L.append(f"   {n:<5} Se={vp / max(vp + fn, 1):.3f}  +P={vp / max(vp + fp, 1):.3f}  (n={vp + fn})")
        txt = "\n".join(L)
        print(txt)
        if a.saida:
            open(a.saida, "w", encoding="utf-8").write(txt + "\n")
