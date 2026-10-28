# -*- coding: utf-8 -*-
# =============================================================================
# analise_molde.py  —  estabilidade do molde adaptativo e metricas por paciente
# -----------------------------------------------------------------------------
# 1) Molde: instrumenta a classe Morfologia do golden model (semantica do RTL)
#    e registra, em cada registro do DS2, cada atualizacao do molde: classe
#    anotada do batimento que entrou no molde (contaminacao por VEB/SVEB nao
#    prematuros) e deriva do molde ao longo do tempo (variacao relativa
#    sum|T_t - T_t-1min| / sum|T_t-1min| a cada minuto).
# 2) Metricas por paciente (macro): media e mediana de Se e +P de VEB entre
#    registros, e falsos positivos de VEB por hora, a partir dos dumps do RTL.
# Saida: ../validacao/analise_molde.txt
# Uso: python python/analise_molde.py
# =============================================================================
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import modelo_v2 as mv  # noqa: E402
import estatisticas_v2 as est  # noqa: E402
from gerar_cache import CACHE, DS2  # noqa: E402
from gerar_treino import TOLERANCIA, classe_de  # noqa: E402

FS = 360
REGISTRO = []                                   # (k, prematuro, T apos a chamada, atualizou)


class MorfologiaInstr(mv.Morfologia):
    def calcula(self, ds, k, prematuro):
        n_antes = self.nT
        r = super().calcula(ds, k, prematuro)
        # o molde e' atualizado no 1o batimento e em todo batimento nao prematuro
        REGISTRO.append((k, prematuro, np.array(self.T, copy=True), n_antes == 0 or not prematuro))
        return r


def classe_anotada(anot, a, k):
    j = int(np.argmin(np.abs(a - k)))
    return classe_de(anot[j][1]) if abs(a[j] - k) <= TOLERANCIA else -1


if __name__ == "__main__":
    mv.Morfologia = MorfologiaInstr
    L = ["=== 1) Estabilidade do molde (golden model = RTL), DS2"]
    L.append("   reg   batimentos  atualiz.  %VEB_no_molde %SVEB_no_molde  deriva/min mediana  deriva 1o->ultimo min")
    tot_upd = tot_v = tot_s = 0
    derivas = []
    por_reg = {}
    for rec in DS2:
        REGISTRO.clear()
        z = np.load(os.path.join(CACHE, f"{rec}.npz"))
        mv.features_registro(z["ds"].astype(np.int64), z["picos"], z["pval"])
        anot = est.anotacoes(rec)
        a = np.array([s for s, _ in anot])
        upd = [(k, T) for k, _, T, u in REGISTRO if u]
        cls = [classe_anotada(anot, a, k) for k, _ in upd]
        nv, ns = cls.count(2), cls.count(1)
        tot_upd += len(upd); tot_v += nv; tot_s += ns
        # deriva: molde no fim de cada minuto
        por_min = {}
        for k, T in upd:
            por_min[k // (60 * FS)] = T
        mins = sorted(por_min)
        d = []
        for m0, m1 in zip(mins, mins[1:]):
            t0, t1 = por_min[m0].astype(np.int64), por_min[m1].astype(np.int64)
            d.append(np.abs(t1 - t0).sum() / max(np.abs(t0).sum(), 1))
        derivas += d
        ini, fim = por_min[mins[min(1, len(mins) - 1)]].astype(np.int64), por_min[mins[-1]].astype(np.int64)
        total = np.abs(fim - ini).sum() / max(np.abs(ini).sum(), 1)
        por_reg[rec] = (len(upd), nv)
        L.append(f"   {rec}   {len(REGISTRO):9d}  {len(upd):8d}  {100 * nv / max(len(upd), 1):12.2f}  "
                 f"{100 * ns / max(len(upd), 1):13.2f}  {np.median(d) if d else 0:17.3f}  {total:20.3f}")
    L.append(f"   total: {tot_upd} atualizacoes; {100 * tot_v / tot_upd:.2f}% de VEB e "
             f"{100 * tot_s / tot_upd:.2f}% de SVEB anotados entraram no molde; "
             f"deriva por minuto mediana {np.median(derivas):.3f}, p95 {np.percentile(derivas, 95):.3f}")

    L.append("\n=== 2) VEB por paciente (RTL, DS2): metricas macro")
    se, pp, fph = [], [], []
    for rec in DS2:
        m = est.matriz(rec, est.DUMPS["v2"], est.anotacoes(rec))
        n = m[2, :3].sum()
        fp = m[:3, 2].sum() - m[2, 2]
        horas = len(np.load(os.path.join(CACHE, f"{rec}.npz"))["ds"]) / FS / 3600
        fph.append(fp / horas)
        if n >= 10:
            se.append(m[2, 2] / n)
            pp.append(m[2, 2] / max(m[:3, 2].sum(), 1))
    L.append(f"   registros com >= 10 VEB: {len(se)}")
    L.append(f"   Se  media {np.mean(se):.3f}  mediana {np.median(se):.3f}  min {np.min(se):.2f}")
    L.append(f"   +P  media {np.mean(pp):.3f}  mediana {np.median(pp):.3f}  min {np.min(pp):.2f}")
    L.append(f"   falsos positivos de VEB por hora (22 registros): mediana {np.median(fph):.1f}, "
             f"media {np.mean(fph):.1f}, max {np.max(fph):.1f}")
    txt = "\n".join(L)
    print(txt)
    open(os.path.join(V2, "validacao", "analise_molde.txt"), "w", encoding="utf-8").write(txt + "\n")
