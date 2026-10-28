# -*- coding: utf-8 -*-
# =============================================================================
# externo_incart.py  —  VALIDACAO EXTERNA na St Petersburg INCART (PhysioNet)
# -----------------------------------------------------------------------------
# A INCART (75 registros de 30 min, 12 derivacoes, 257 Hz, 32 pacientes) nao
# participa de nenhuma decisao: serve so' de teste final do modelo congelado.
# Usa a derivacao II, a mais proxima da MLII de treino (a SVDB so' oferece um
# canal de derivacao nao especificada).
#
# preparar : reamostra a derivacao II de 257 para 360 Hz (polifasico 360/257),
#            converte para a escala da entrada MIT-BIH (6400 unidades/mV, base
#            32768, 16 bits), gera dados/incart_mem/NNN_ecg.mem, roda o
#            datapath bit a bit e grava cache_incart/NNN.npz (anotacoes em 360 Hz).
#            Antes da conversao, um passa-altas causal de 1a ordem a 0,05 Hz
#            emula o acoplamento AC do front-end analogico: a derivacao II da
#            INCART tem nivel DC de varios mV e, sem ele, ate' 87% das amostras
#            saturavam a faixa de 16 bits (+-5,12 mV). Decisao tomada apos ver
#            as falhas de deteccao; hardware e modelo nao mudam.
# avaliar  : caracteristicas (modelo_v2) + arvore congelada -> matriz e Se/+P,
#            com IC 95% por bootstrap de PACIENTES (registros do mesmo paciente
#            sao reamostrados juntos).
# Uso: python externo_incart.py preparar | avaliar [--saida arq]
# =============================================================================
import argparse
import os
import re
import sys
from multiprocessing import Pool

import numpy as np
import wfdb
from scipy.signal import lfilter, resample_poly

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
RAIZ = V2
sys.path[:0] = [AQUI]
from gerar_treino import BEAT_SYMBOLS, TOLERANCIA, classe_de  # noqa: E402
from pan_tompkins_hw import ECGProcessorHW, TB_INDEX_OFFSET, to_signed  # noqa: E402

INCART = os.path.join(V2, "dados", "incart")
MEM = os.path.join(V2, "dados", "incart_mem")
CACHE = os.path.join(AQUI, "cache_incart_ac")
UNID_POR_MV = 6400          # = 200 unidades/mV (ADC MIT-BIH) x 32
FS_IN, UP, DOWN = 257, 360, 257
FC_AC = 0.05                # Hz, corte do acoplamento AC (ECG diagnostico)


def acopla_ac(x, fs=360.0):
    # y[n] = a (y[n-1] + x[n] - x[n-1]), com x[-1] = x[0] e y[-1] = 0
    a = 1.0 / (1.0 + 2 * np.pi * FC_AC / fs)
    return lfilter([a, -a], [1.0, -a], x - x[0])
DERIVACAO = "II"
NOMES = ["N", "SVEB", "VEB"]


def registros():
    return sorted(f[:-4] for f in os.listdir(INCART) if f.endswith(".hea"))


def paciente(rec):
    # o cabecalho traz "<idade> <sexo> ... Patient <n>"? Se nao houver, cada
    # registro conta como um paciente (bootstrap mais otimista)
    h = wfdb.rdheader(os.path.join(INCART, rec))
    for c in h.comments or []:
        m = re.search(r"[Pp]atient\s*(\d+)", c)
        if m:
            return m.group(1)
    return rec


def prepara(rec):
    destino = os.path.join(CACHE, f"{rec}.npz")
    if os.path.exists(destino):
        return rec, "cache"
    h = wfdb.rdheader(os.path.join(INCART, rec))
    ch = h.sig_name.index(DERIVACAO)
    r = wfdb.rdrecord(os.path.join(INCART, rec), physical=False, channels=[ch])
    adc = r.d_signal[:, 0].astype(np.float64)
    mv = (adc - r.adc_zero[0]) / r.adc_gain[0]
    x = acopla_ac(resample_poly(mv, UP, DOWN))
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
    ann = wfdb.rdann(os.path.join(INCART, rec), "atr")
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
    # deteccao (casamento um a um, como em estatisticas_v2.py)
    picos = np.array(z["picos"]) - 1
    an = np.array(a)
    usados = np.zeros(len(an), bool)
    fp = 0
    for p in picos:
        k = np.searchsorted(an, p)
        cand = [t for t in (k - 1, k) if 0 <= t < len(an) and not usados[t] and abs(an[t] - p) <= TOLERANCIA]
        if cand:
            usados[min(cand, key=lambda t: abs(an[t] - p))] = True
        else:
            fp += 1
    return rec, conf, int(usados.sum()), len(an), fp, len(z["ds"]) / 360 / 3600


def metricas(m):
    out = {}
    for c in range(3):
        vp = m[c, c]
        fn = m[c, :3].sum() - vp
        fp = m[:3, c].sum() - vp
        out[NOMES[c]] = (vp / max(vp + fn, 1), vp / max(vp + fp, 1), vp + fn)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["preparar", "avaliar"])
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    if a.acao == "preparar":
        os.makedirs(MEM, exist_ok=True)
        os.makedirs(CACHE, exist_ok=True)
        with Pool(4) as p:
            for rec, info in p.imap_unordered(prepara, registros()):
                print(f"  {rec}: {info}", flush=True)
    else:
        with Pool(4) as p:
            res = p.map(avalia, registros())
        conf = sum(r[1] for r in res)
        tp = sum(r[2] for r in res); nan = sum(r[3] for r in res)
        fp = sum(r[4] for r in res); horas = sum(r[5] for r in res)
        # bootstrap por paciente
        pac = {}
        for r in res:
            pac.setdefault(paciente(r[0]), []).append(r[1])
        mats = [sum(v) for v in pac.values()]
        rng = np.random.default_rng(2026)
        boot = {c: ([], []) for c in NOMES}
        for _ in range(5000):
            mb = sum(mats[i] for i in rng.integers(0, len(mats), len(mats)))
            for c, (se, pp, _) in metricas(mb).items():
                boot[c][0].append(se); boot[c][1].append(pp)
        L = [f"  INCART (validacao externa, derivacao {DERIVACAO}): {len(res)} registros, "
             f"{len(pac)} pacientes, {horas:.1f} h",
             f"  Deteccao: Se={tp / nan:.4f}  +P={tp / max(tp + fp, 1):.4f}  FP/h={fp / horas:.1f}",
             "  MATRIZ (linha=real, coluna=predito: N SVEB VEB F Q)"]
        L += ["   " + f"{n:<5}" + "".join(f"{conf[v, k]:>8}" for k in range(5))
              for v, n in enumerate(["N", "SVEB", "VEB", "F", "Q"])]
        for c, (se, pp, n) in metricas(conf).items():
            s0, s1 = np.percentile(boot[c][0], [2.5, 97.5])
            p0, p1 = np.percentile(boot[c][1], [2.5, 97.5])
            L.append(f"   {c:<5} Se={se:.3f} [{s0:.2f}-{s1:.2f}]  +P={pp:.3f} [{p0:.2f}-{p1:.2f}]  (n={n})")
        L.append("\n  Por registro (VEB, >= 10 anotados): reg  n  Se  +P")
        for r in res:
            se, pp, n = metricas(r[1])["VEB"]
            if n >= 10:
                L.append(f"   {r[0]}  {n:5d}  {se:.2f}  {pp:.2f}")
        txt = "\n".join(L)
        print(txt)
        if a.saida:
            open(a.saida, "w", encoding="utf-8").write(txt + "\n")
