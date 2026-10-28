# -*- coding: utf-8 -*-
# =============================================================================
# banda_ds2.py  —  sensibilidade a' banda de aquisicao, MESMOS pacientes do DS2
# -----------------------------------------------------------------------------
# Separa o efeito da banda do efeito da populacao na validacao externa: o sinal
# de cada registro do DS2 (ADC MIT-BIH, 360 Hz) e' reamostrado para 128 Hz e de
# volta para 360 Hz (polifasico 16/45 e 45/16), como na SVDB, convertido para a
# mesma escala de entrada (ADC*32) e processado pelo datapath bit a bit; o
# modelo congelado classifica e as metricas sao comparadas com o DS2 original.
# Uso: python banda_ds2.py [--fs 128]
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
from gerar_cache import DS2  # noqa: E402
from pan_tompkins_hw import ECGProcessorHW, TB_INDEX_OFFSET, to_signed  # noqa: E402

FS = 128


def processa(rec):
    destino = os.path.join(AQUI, f"cache_banda{FS}", f"{rec}.npz")
    if os.path.exists(destino):
        return rec
    r = wfdb.rdrecord(os.path.join(RAIZ, "dados", "mitdb", rec), physical=False)
    ch = r.sig_name.index("MLII") if "MLII" in r.sig_name else 0
    adc = r.d_signal[:, ch].astype(np.float64)
    g = np.gcd(360, FS)
    x = resample_poly(resample_poly(adc, FS // g, 360 // g), 360 // g, FS // g)[:len(adc)]
    amostras = np.clip(np.round(x * 32), 0, 65535).astype(np.int64)
    hw = ECGProcessorHW()
    ds = np.empty(len(amostras), np.int32)
    picos, pval = [], []
    for k, s in enumerate(amostras):
        fo = hw._filter(int(s))
        d = (2 * to_signed(hw.d_x0, 32) + to_signed(hw.d_x1, 32)
             - to_signed(hw.d_x3, 32) - 2 * to_signed(hw.d_x4, 32))
        i = hw._integrator(hw._derivator(fo))
        if hw._peak_detector(i):
            picos.append(k + TB_INDEX_OFFSET)
            pval.append(hw.p_value)
        ds[k] = d
    np.savez_compressed(destino, ds=ds, picos=np.array(picos, np.int64), pval=np.array(pval, np.int64))
    return rec


def avalia(rec):
    from classificador_arvore_v2 import classificar
    from modelo_v2 import FEATURES, features_registro
    from validar_v2 import casar
    z = np.load(os.path.join(AQUI, f"cache_banda{FS}", f"{rec}.npz"))
    cl = [(p, classificar(*[f[k] for k in FEATURES]))
          for p, f in features_registro(z["ds"].astype(np.int64), z["picos"], z["pval"])]
    conf = [[0] * 5 for _ in range(5)]
    casar(cl, rec, conf)
    return np.array(conf)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fs", type=int, default=128)
    FS = ap.parse_args().fs
    os.makedirs(os.path.join(AQUI, f"cache_banda{FS}"), exist_ok=True)
    assert FS == 128, "os processos de trabalho usam FS do modulo (128 Hz)"
    with Pool(4) as p:
        list(p.imap_unordered(processa, DS2))
        m = sum(p.map(avalia, DS2))
    L = [f"  DS2 com banda limitada a {FS} Hz (mesmos pacientes, modelo congelado)",
         "  MATRIZ (linha=real, coluna=predito: N SVEB VEB F Q)"]
    L += ["   " + f"{n:<5}" + "".join(f"{m[v, k]:>8}" for k in range(5)) for v, n in enumerate(["N", "SVEB", "VEB", "F", "Q"])]
    for c, n in zip((0, 1, 2), ("N", "SVEB", "VEB")):
        vp = m[c, c]
        fn = sum(m[c, k] for k in (0, 1, 2)) - vp
        fp = sum(m[v, c] for v in (0, 1, 2)) - vp
        L.append(f"   {n:<5} Se={vp / max(vp + fn, 1):.3f}  +P={vp / max(vp + fp, 1):.3f}")
    txt = "\n".join(L)
    print(txt)
    open(os.path.join(V2, "validacao", f"ds2_banda{FS}.txt"), "w", encoding="utf-8").write(txt + "\n")
