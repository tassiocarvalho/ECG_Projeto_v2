# -*- coding: utf-8 -*-
# =============================================================================
# gerar_figuras_v2.py  —  diagramas e graficos do projeto
#   (primitivas de desenho em figuras/estilo.py)
# Saida: figuras/img/*.png
# Uso:  python figuras/gerar_figuras_v2.py [nome ...]
#   nomes: arquitetura morfologia temporizacao matriz matriz_incart comparacao
#          porpaciente caso232 protocolo area
# =============================================================================
import csv
import importlib.util
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
RAIZ = V2
SAIDA = os.path.join(AQUI, "img")
sys.path[:0] = [os.path.join(V2, "python")]

_spec = importlib.util.spec_from_file_location(
    "gf", os.path.join(AQUI, "estilo.py"))
gf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gf)
gf.AQUI = SAIDA                       # salvar() grava em figuras/img
bloco, registrador, ula, cilindro = gf.bloco, gf.registrador, gf.ula, gf.cilindro
moldura, linha, rot, no, salvar, novo = gf.moldura, gf.linha, gf.rot, gf.no, gf.salvar, gf.novo
PROC, REG, MEM, CTRL, CLS, INTERF = gf.PROC, gf.REG, gf.MEM, gf.CTRL, gf.CLS, gf.INTERF
TINTA, CINZA, COR_CTRL, TRACO = gf.TINTA, gf.CINZA, gf.COR_CTRL, gf.TRACO
MORF = ("#E3F4F4", "#1F6F73")         # motor de morfologia (cor nova)
plt.rcParams.update({"font.family": "DejaVu Sans"})


# -----------------------------------------------------------------------------
# 1) arquitetura v2
# -----------------------------------------------------------------------------
def arquitetura():
    fig, ax = novo(19.6, 16.6, -0.2, -6.05)
    moldura(ax, 1.2, -4.95, 14.25, 15.4, "ecg_processor_top_spi (v2)  ·  escopo sintetizado (Genus)",
            cor="#4D4D4D", lw=1.6, tam=10.5)
    moldura(ax, 4.4, 0.9, 9.3, 9.0, "ecg_processor_top", cor="#8A8A8A")
    moldura(ax, 4.7, 4.2, 8.75, 5.25, "Datapath  (32 bits, aritmética inteira)", cor=PROC[1], fc="#F7FAFD")

    # SPI
    for i, s in enumerate(["sclk", "cs_n", "mosi"]):
        yy = 8.45 - i * 0.45
        ax.text(0.0, yy, s, ha="left", va="center", fontsize=9, family="DejaVu Sans Mono")
        linha(ax, [(0.75, yy), (1.6, yy)])
    bloco(ax, 1.6, 7.2, 2.3, 1.75, "Escravo SPI", "modo 0, MSB primeiro\nsincronização 2 FF\nshift register 16 b",
          cores=INTERF, ts=8)
    registrador(ax, 1.6, 4.75, 2.3, 1.35, "Reg. de fronteira", "amostra_reg · valida")
    linha(ax, [(2.75, 7.2), (2.75, 6.1)])
    rot(ax, 2.85, 6.65, "spi_data[31:0]\nspi_valid", va="center")

    # datapath
    registrador(ax, 5.0, 7.95, 1.35, 1.0, "sample_reg", tn=8.2)
    bloco(ax, 6.75, 7.9, 1.55, 1.1, "Filtro", "média de 3")
    bloco(ax, 8.7, 7.9, 1.85, 1.1, "Derivador", "d e |d|", ts=8.4)
    bloco(ax, 10.95, 7.9, 2.25, 1.1, "Integrador MWI", "janela 30, ≫ 5", tt=10)
    bloco(ax, 10.95, 6.0, 2.25, 1.3, "Detector de picos", "limiar adaptativo\nrefratário · SETTLE", tt=9.6, ts=8)
    a_in, b_in, u_out = ula(ax, 8.6, 5.0, 1.7, 1.2)
    cilindro(ax, 5.15, 4.5, 2.2, 1.95, "RAM 256×32", "derivada com sinal")
    linha(ax, [(3.9, 5.4), (4.15, 5.4), (4.15, 8.45), (5.0, 8.45)])
    linha(ax, [(6.35, 8.45), (6.75, 8.45)])
    linha(ax, [(8.3, 8.45), (8.7, 8.45)])
    linha(ax, [(10.55, 8.45), (10.95, 8.45)])
    linha(ax, [(12.1, 7.9), (12.1, 7.3)])
    no(ax, 12.1, 7.6)
    linha(ax, [(12.1, 7.6), (a_in[0], 7.6), a_in])
    linha(ax, [(10.95, 6.55), (b_in[0], 6.55), b_in])
    rot(ax, 10.9, 6.62, "peak_value", ha="right")
    # derivada com sinal -> RAM (porta de escrita)
    linha(ax, [(9.35, 7.9), (9.35, 7.25), (6.25, 7.25), (6.25, 6.45)], cor=MORF[1])
    rot(ax, 7.55, 7.32, "d (com sinal)", ha="center", cor=MORF[1], tam=7.4)
    linha(ax, [u_out, (u_out[0], 4.4), (15.45, 4.4)], z=2.4)
    rot(ax, 15.3, 4.45, "final_output[31:0]", ha="right", mono=True, tam=7.2)
    linha(ax, [(13.2, 6.95), (15.45, 6.95)])
    rot(ax, 15.3, 7.0, "peak_value_out", ha="right", mono=True, tam=7.2)

    # FSM
    bloco(ax, 5.9, 1.3, 5.0, 1.75, "Unidade de controle (FSM)",
          "12 estados, Moore · 11 ciclos por amostra\nendereço da RAM = amostra mod 256", cores=CTRL, ts=8.2)
    linha(ax, [(7.9, 3.05), (7.9, 4.2)], cor=COR_CTRL, ls=TRACO)
    rot(ax, 7.8, 3.62, "enables · ula_op\nram_we · ram_addr", ha="right", va="center", cor=COR_CTRL, tam=7.0)
    linha(ax, [(10.4, 4.2), (10.4, 3.05)])
    rot(ax, 10.5, 3.62, "peak_detected", va="center")
    linha(ax, [(2.3, 4.75), (2.3, 2.55), (5.9, 2.55)])
    rot(ax, 3.1, 2.6, "data_valid")
    linha(ax, [(5.9, 1.75), (3.2, 1.75), (3.2, 4.75)], cor=COR_CTRL, ls=TRACO)
    rot(ax, 3.3, 1.68, "data_ready", va="top", cor=COR_CTRL)
    linha(ax, [(10.9, 2.55), (15.45, 2.55)])
    rot(ax, 15.3, 2.6, "alert_out", ha="right", mono=True, tam=7.2)

    # ---- faixa de classificacao (v2)
    registrador(ax, 1.6, -2.75, 2.15, 1.55, "Contadores", "aceitas · gravadas", tn=8.6)
    no(ax, 2.3, 2.55)
    linha(ax, [(2.3, 2.55), (2.3, -1.2)])
    no(ax, 3.2, 1.75, cor=COR_CTRL)
    linha(ax, [(3.2, 1.75), (3.2, -1.2)], cor=COR_CTRL, ls=TRACO)
    registrador(ax, 1.6, -4.55, 2.15, 1.25, "Captura do pico", "índice · amplitude", tn=8.2)
    linha(ax, [(2.675, -2.75), (2.675, -3.3)])
    no(ax, 14.1, 2.55, cor=CLS[1])
    linha(ax, [(14.1, 2.55), (14.1, 0.45), (4.05, 0.45), (4.05, -3.9), (3.75, -3.9)], cor=CLS[1])
    rot(ax, 13.9, 0.52, "alert_out → new_peak", ha="right", cor=CLS[1], mono=True, tam=7.0)
    no(ax, 14.7, 6.95)
    linha(ax, [(14.7, 6.95), (14.7, 0.15), (4.3, 0.15), (4.3, -4.25), (3.75, -4.25)])
    rot(ax, 13.9, 0.2, "peak_value_out", ha="right", mono=True, tam=7.0)

    # RAM -> morfologia (2a porta de leitura)
    linha(ax, [(5.4, 4.55), (5.4, 4.0), (4.6, 4.0), (4.6, -0.2), (6.6, -0.2), (6.6, -1.2)], cor=MORF[1])
    rot(ax, 4.68, -0.12, "rd_addr / rd_data (2ª porta)", va="top", cor=MORF[1], tam=6.8)

    bloco(ax, 4.9, -4.55, 3.4, 3.35, "Motor de morfologia",
          "busca max|d| em [k−80, k+39]\nlargura do QRS (d_w)\nmolde 64 × 20 b do paciente\nSAD e polaridade\n(sad_t, dpol)\ndivisor serial", cores=MORF, ts=7.4, tt=9.4)
    bloco(ax, 8.75, -4.55, 3.5, 3.35, "Classificador v2",
          "históricos: RR · amplitude\n|ΔRR| não prematuros (irr_np)\nbase lenta de RR (1/128)\n9 razões inteiras\ndivisor serial", cores=CLS, ts=7.4, tt=9.4)
    bloco(ax, 12.7, -4.55, 2.35, 3.35, "Árvore", "\nprofundidade 7\n62 comparadores\n11 entradas", cores=CLS, ts=7.4, tt=9.4)
    linha(ax, [(3.75, -1.95), (4.9, -1.95)])
    rot(ax, 3.83, -1.88, "n_grav", tam=6.6, mono=True)
    linha(ax, [(3.75, -3.6), (4.45, -3.6), (4.45, -4.75), (10.5, -4.75), (10.5, -4.55)], cor=CLS[1])
    linha(ax, [(8.3, -2.3), (8.75, -2.3)], cor=MORF[1])
    rot(ax, 8.52, -2.05, "sad_t · dpol · d_w", ha="center", tam=6.6, cor=MORF[1])
    linha(ax, [(8.75, -3.4), (8.3, -3.4)], cor=COR_CTRL, ls=TRACO)
    rot(ax, 8.52, -3.65, "rr_ratio (molde?)", ha="center", tam=6.4, cor=COR_CTRL)
    linha(ax, [(12.25, -2.85), (12.7, -2.85)])
    for i, s in enumerate(["classe_out[2:0]", "classe_valid", "peak_classificado"]):
        yy = -2.2 - i * 0.42
        linha(ax, [(15.05, yy), (15.85, yy)])
        ax.text(15.9, yy, s, ha="left", va="center", fontsize=7.8, family="DejaVu Sans Mono")
    gf.legenda(ax, 4.6, -5.6)
    salvar(fig, "arquitetura_v2.png")


# -----------------------------------------------------------------------------
# 2) exemplo da morfologia (registro 119, DS1): molde x batimento N x VEB
# -----------------------------------------------------------------------------
def morfologia():
    import wfdb
    import modelo_v2 as mv
    from gerar_cache import CACHE
    rec = "119"
    z = np.load(os.path.join(CACHE, f"{rec}.npz"))
    captura = {}
    orig = mv.Morfologia.calcula

    def espia(self, ds, k, prem):
        T = None if self.T is None else self.T.copy()
        out = orig(self, ds, k, prem)
        r = out["r"]
        S = np.array([ds[j] if 0 <= j < len(ds) else 0 for j in range(r - mv.SA, r + mv.SB)])
        captura[k + 1] = (S, T, out)
        return out
    mv.Morfologia.calcula = espia
    mv.features_registro(z["ds"].astype(np.int64), z["picos"], z["pval"])
    mv.Morfologia.calcula = orig
    ann = wfdb.rdann(os.path.join(RAIZ, "dados", "mitdb", rec), "atr")
    rot_ = {int(s): y for s, y in zip(ann.sample, ann.symbol)}
    asamp = np.array(sorted(rot_))

    def classe(p):
        j = asamp[np.argmin(np.abs(asamp - p))]
        return rot_[j] if abs(j - p) <= 36 else "?"
    pk = sorted(captura)
    alvo_v = next(p for p in pk if p > 360 * 120 and classe(p) == "V")
    alvo_n = max(p for p in pk if p < alvo_v and classe(p) == "N")
    Sv, T, ov = captura[alvo_v]
    Sn, _, on = captura[alvo_n]
    t = (np.arange(-mv.SA, mv.SB)) / 360 * 1000
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    ax.plot(t, T, color="#222222", lw=2.0, ls="--", label="molde do paciente (T)")
    ax.plot(t, Sn, color="#2F5D8A", lw=1.4, label=f"batimento N   (sad_t = {on['sad_t']}, d_w = {on['d_w']})")
    ax.plot(t, Sv, color="#A23B4D", lw=1.4, label=f"batimento VEB (sad_t = {ov['sad_t']}, d_w = {ov['d_w']})")
    ax.fill_between(t, T, Sv, color="#A23B4D", alpha=0.10)
    ax.axvline(0, color="#999999", lw=0.8, ls=":")
    ax.set_xlabel("tempo em relação ao máximo de |d| (ms)", fontsize=8.5)
    ax.set_ylabel("derivada com sinal (unid.)", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.legend(fontsize=7.4, frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "morfologia_exemplo.png"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [gerado] morfologia_exemplo.png", alvo_n, alvo_v)


# -----------------------------------------------------------------------------
# 3) temporizacao de um batimento
# -----------------------------------------------------------------------------
def temporizacao():
    fig, ax = plt.subplots(figsize=(7.2, 2.7))
    ax.set_xlim(-78, 135)
    ax.set_ylim(-0.85, 3.75)
    ax.axis("off")
    faixas = [(3, "Datapath / detector"), (2, "Motor de morfologia"), (1, "Classificador v2"), (0, "Saída")]
    for y, n in faixas:
        ax.text(-77, y, n, va="center", fontsize=8.2, color=TINTA, fontweight="bold")
        ax.plot([-30, 132], [y, y], color="#E2E2E2", lw=0.8, zorder=0)
    for x, nome in ((0, "pico i (amostra k)"), (115, "pico i+1")):
        ax.plot([x, x], [-0.3, 3.35], color="#A23B4D", lw=1.0, ls=(0, (3, 2)), zorder=1)
        ax.text(x, 3.45, nome, ha="center", va="bottom", fontsize=7.4, color="#A23B4D")
    # R -> deteccao
    ax.plot([-20], [3], marker="v", color=TINTA, ms=5)
    ax.text(-20, 3.18, "R", ha="center", fontsize=7.4)
    ax.annotate("", xy=(0, 2.78), xytext=(-20, 2.78), arrowprops=dict(arrowstyle="->", color=CINZA, lw=0.8))
    ax.text(-12, 2.5, "~20 amostras", ha="center", fontsize=6.2, color=CINZA)
    # morfologia
    ax.annotate("", xy=(40, 2.32), xytext=(0, 2.32), arrowprops=dict(arrowstyle="->", color=CINZA, lw=0.8))
    ax.text(20, 2.4, "espera +40 amostras", ha="center", va="bottom", fontsize=6.4, color=CINZA)
    ax.add_patch(plt.Rectangle((40, 1.78), 36, 0.44, fc=MORF[0], ec=MORF[1], lw=1.0))
    ax.text(58, 2.0, "varredura · molde\n3 divisões", ha="center", va="center", fontsize=6.3, linespacing=1.1)
    # classificador
    ax.add_patch(plt.Rectangle((0, 0.8), 11, 0.4, fc=CLS[0], ec=CLS[1], lw=1.0))
    ax.text(5.5, 1.0, "pré", ha="center", va="center", fontsize=6.4)
    ax.text(13, 1.0, "7 razões", ha="left", va="center", fontsize=6.0, color=CINZA)
    ax.add_patch(plt.Rectangle((115, 0.8), 11, 0.4, fc=CLS[0], ec=CLS[1], lw=1.0))
    ax.text(120.5, 1.28, "classifica i", ha="center", va="bottom", fontsize=6.2)
    ax.annotate("", xy=(115, 1.2), xytext=(76, 1.8), arrowprops=dict(arrowstyle="->", color=MORF[1], lw=0.9))
    ax.text(93, 1.78, "sad_t · dpol · d_w", ha="center", fontsize=6.4, color=MORF[1])
    # saida
    ax.add_patch(plt.Rectangle((126, -0.16), 2.4, 0.32, fc="#9FD39F", ec="#2E6B46", lw=1.0))
    ax.text(127.2, -0.24, "classe_valid", ha="center", va="top", fontsize=6.0, family="DejaVu Sans Mono")
    ax.text(52, -0.68, "entre picos: >= 72 amostras (refratário), ou seja, >= 790 ciclos a 11 ciclos/amostra",
            ha="center", va="center", fontsize=6.4, color=CINZA)
    fig.savefig(os.path.join(SAIDA, "temporizacao_v2.png"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [gerado] temporizacao_v2.png")


# -----------------------------------------------------------------------------
# 4) matriz de confusao (DS2, RTL = golden)
# -----------------------------------------------------------------------------
def ler_matriz(arq):
    txt = open(arq, encoding="utf-8").read()
    m = []
    for n in ("N", "SVEB", "VEB"):
        lin = re.search(rf"^\s+{n}\s+([\d\s]+)$", txt, re.M).group(1).split()
        m.append([int(v) for v in lin[:3]])
    return np.array(m)


def matriz(arq="resultado_ds2_rtl.txt", saida="matriz_ds2_v2.png"):
    m = ler_matriz(os.path.join(V2, "validacao", arq))
    frac = m / m.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    ax.imshow(frac, cmap="Blues", vmin=0, vmax=1)
    nomes = ["N", "SVEB", "VEB"]
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{m[i, j]}\n({100 * frac[i, j]:.1f}%)", ha="center", va="center", fontsize=8,
                    color="white" if frac[i, j] > 0.6 else "#222222")
    ax.set_xticks(range(3)); ax.set_xticklabels(nomes, fontsize=8.5)
    ax.set_yticks(range(3)); ax.set_yticklabels(nomes, fontsize=8.5)
    ax.set_xlabel("classe prevista", fontsize=8.5); ax.set_ylabel("classe real", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, saida), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def matriz_incart():
    matriz("incart_v3.txt", "matriz_incart.png")
    print("  [gerado] matriz_ds2_v2.png")


# -----------------------------------------------------------------------------
# 5) comparacao v1 x v2 (DS2)
# -----------------------------------------------------------------------------
def comparacao():
    v1 = {"N": (0.930, 0.983), "SVEB": (0.521, 0.237), "VEB": (0.540, 0.514)}
    v2 = {"N": (0.973, 0.961), "SVEB": (0.149, 0.308), "VEB": (0.892, 0.792)}
    fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.4), sharey=True)
    for ax, (idx, nome) in zip(axs, ((0, "Sensibilidade (Se)"), (1, "Precisão (+P)"))):
        x = np.arange(3)
        ax.bar(x - 0.18, [v1[c][idx] for c in v1], 0.34, color="#B8C4D6", label="v1 (RR + amplitude)")
        ax.bar(x + 0.18, [v2[c][idx] for c in v2], 0.34, color="#2F5D8A", label="v2 (+ morfologia)")
        for xi, c in zip(x, v2):
            ax.text(xi + 0.18, v2[c][idx] + 0.02, f"{v2[c][idx]:.2f}", ha="center", fontsize=7)
            ax.text(xi - 0.18, v1[c][idx] + 0.02, f"{v1[c][idx]:.2f}", ha="center", fontsize=7, color="#555555")
        ax.set_xticks(x); ax.set_xticklabels(list(v1), fontsize=8.5)
        ax.set_title(nome, fontsize=8.8)
        ax.set_ylim(0, 1.12)
        ax.tick_params(labelsize=7.5)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
    axs[0].legend(fontsize=7, frameon=False, loc="upper center", ncol=1)
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "comparacao_v1_v2.png"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [gerado] comparacao_v1_v2.png")


# -----------------------------------------------------------------------------
# 5b) VEB por paciente (DS2 e INCART): Se x +P, tamanho ~ numero de VEB
# -----------------------------------------------------------------------------
def porpaciente():
    def ler(arq, padrao):
        txt = open(os.path.join(V2, "validacao", arq), encoding="utf-8").read()
        return [(int(n), float(se), float(pp)) for n, se, pp in re.findall(padrao, txt, re.M)]
    ds2 = ler("estatisticas_ds2.txt", r"^\s+\d{3}\s+(\d+)\s+[\d.]+/[\d.]+\s+([\d.]+)/([\d.]+)\s*$")
    inc = ler("incart_v3.txt", r"^\s+I\d{2}\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s*$")
    fig, ax = plt.subplots(figsize=(3.5, 3.1))
    for dados, cor, rot in ((inc, "#D08C3A", f"INCART ({len(inc)} reg. com ≥10 VEB)"),
                            (ds2, "#2F5D8A", f"DS2 ({len(ds2)} reg. com ≥10 VEB)")):
        n = np.array([d[0] for d in dados])
        ax.scatter([d[1] for d in dados], [d[2] for d in dados], s=8 + 70 * np.sqrt(n / n.max()),
                   color=cor, alpha=0.7, edgecolor="white", linewidth=0.5, label=rot)
    ax.scatter([0.892], [0.792], marker="*", s=140, color="#2F5D8A", edgecolor="black", linewidth=0.6, zorder=5)
    ax.scatter([0.819], [0.755], marker="*", s=140, color="#D08C3A", edgecolor="black", linewidth=0.6, zorder=5)
    ax.set_xlim(0, 1.03); ax.set_ylim(0, 1.03)
    ax.set_xlabel("Se (VEB)", fontsize=8.5); ax.set_ylabel("+P (VEB)", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    ax.grid(True, color="#E5E5E5", linewidth=0.6)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    ax.text(0.03, 0.17, "★ agregado", fontsize=7, transform=ax.transAxes)
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "porpaciente_veb.png"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [gerado] porpaciente_veb.png")


# -----------------------------------------------------------------------------
# 6) limitacao do SVEB: registro 232
# -----------------------------------------------------------------------------
def caso232():
    lin = [l for l in csv.DictReader(open(os.path.join(V2, "python", "dados", "dataset_v2.csv")))
           if l["registro"] == "232"]
    t = np.array([int(l["amostra"]) for l in lin]) / 360 / 60
    rr = np.array([int(l["rr_prev"]) for l in lin]) / 360 * 1000
    c = np.array([int(l["classe"]) for l in lin])
    irr = np.array([int(l["irr_np"]) for l in lin])
    sel = t < 10
    fig, ax = plt.subplots(2, 1, figsize=(6.8, 3.4), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for cl, cor, nome in ((0, "#2F5D8A", "N"), (1, "#B07A14", "SVEB")):
        k = sel & (c == cl)
        ax[0].scatter(t[k], rr[k], s=5, color=cor, label=nome, zorder=3)
    ax[0].set_ylabel("RR anterior (ms)", fontsize=8)
    ax[0].legend(fontsize=7.5, frameon=False, markerscale=2.5, loc="upper right")
    ax[1].plot(t[sel], irr[sel], color="#555555", lw=0.9)
    ax[1].axhline(np.median([int(l["irr_np"]) for l in csv.DictReader(open(os.path.join(V2, "python", "dados", "dataset_v2.csv")))
                             if l["registro"] in ("101", "112", "115", "122") and l["classe"] == "0"]),
                  color="#2E6B46", lw=0.8, ls="--")
    ax[1].text(9.9, ax[1].get_ylim()[1] * 0.85, "irr_np típico de ritmo sinusal (DS1)", ha="right", fontsize=6.6, color="#2E6B46")
    ax[1].set_ylabel("irr_np", fontsize=8)
    ax[1].set_xlabel("tempo (min)", fontsize=8)
    for a in ax:
        a.tick_params(labelsize=7)
        for lado in ("top", "right"):
            a.spines[lado].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "caso_232.png"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [gerado] caso_232.png")


# -----------------------------------------------------------------------------
# 7) protocolo de avaliacao
# -----------------------------------------------------------------------------
def protocolo():
    fig, ax = novo(15.4, 4.6, -0.2, -0.2)
    gf.bloco(ax, 0.0, 1.6, 3.4, 2.2, "DS1 (22 pacientes)", "LOPO: 22 rodadas\ncaracterísticas, modelo\ne hiperparâmetros", cores=PROC, ts=8)
    gf.bloco(ax, 4.3, 1.6, 3.0, 2.2, "Treino final", "DS1 inteiro\nárvore de 62\ncomparadores", cores=CLS, ts=8)
    gf.bloco(ax, 8.3, 2.55, 3.3, 1.55, "DS2 (22 pacientes)", "teste inter-paciente\nRTL = golden", cores=MEM, ts=8)
    gf.bloco(ax, 8.3, 0.4, 3.3, 1.55, "SVDB (78 pacientes)", "validação externa\n128 Hz → 360 Hz", cores=MEM, ts=8)
    gf.bloco(ax, 12.4, 1.6, 2.8, 2.2, "Métricas", "Se e +P por classe\n(AAMI EC57)\nmatriz de confusão", cores=REG, ts=8)
    linha(ax, [(3.4, 2.7), (4.3, 2.7)])
    linha(ax, [(7.3, 2.7), (7.8, 2.7), (7.8, 3.3), (8.3, 3.3)])
    linha(ax, [(7.8, 2.7), (7.8, 1.15), (8.3, 1.15)])
    linha(ax, [(11.6, 3.3), (12.0, 3.3), (12.0, 2.7), (12.4, 2.7)])
    linha(ax, [(11.6, 1.15), (12.0, 1.15), (12.0, 2.7)], seta=False)
    ax.text(5.8, 0.9, "seleção e treino: só DS1 (LOPO)\nDS2 e SVDB apenas avaliam", ha="center", fontsize=7.6,
            color=CINZA, style="italic")
    salvar(fig, "protocolo_v2.png")


# -----------------------------------------------------------------------------
# 8) area e potencia (relatorios do Genus)
# -----------------------------------------------------------------------------
def area():
    rep = os.path.join(V2, "sintese", "reports_nangate45_ram19")
    r = {}
    for l in open(os.path.join(rep, "area_resumo.txt"), encoding="utf-8"):
        k, v = l.split(":")
        r[k.strip()] = float(v.split()[0])
    tot = r["area total"]
    # potencia por bloco: NanGate a 1 MHz (fluxo de referencia, mW) e SkyWater
    # 130 nm com clock gating a 100 kHz (uW), dos relatorios hierarquicos
    pot = {"RAM (derivada)": (0.785, 0.77), "Morfologia": (0.380, 1.87), "Classificador v2": (0.369, 1.08)}
    itens = [("RAM (derivada)", r["area da RAM"]), ("Classificador v2", r["area do classificador"]),
             ("Morfologia", r["area da morfologia"]),
             ("Pan-Tompkins, SPI,\nFSM e topo", tot - r["area da RAM"] - r["area do classificador"] - r["area da morfologia"])]
    cores = {"RAM (derivada)": "#2E6B46", "Classificador v2": "#8E3B4A", "Morfologia": "#1F6F73"}
    fig, ax = plt.subplots(figsize=(5.6, 2.2))
    y = np.arange(len(itens))
    ax.barh(y, [v / 1000 for _, v in itens], color=[cores.get(n, "#2F5D8A") for n, _ in itens], height=0.6)
    ax.set_yticks(y); ax.set_yticklabels([n for n, _ in itens], fontsize=7.6)
    ax.invert_yaxis()
    for yi, (n, v) in zip(y, itens):
        txt = f"{v / 1000:.1f} ({100 * v / tot:.0f}%)"
        if n in pot:
            txt += f"   ·   {pot[n][0]:.2f} mW (45 nm, 1 MHz)  ·  {pot[n][1]:.2f} µW (130 nm, 100 kHz)"
        ax.text(v / 1000 + 0.5, yi, txt, va="center", fontsize=6.8)
    ax.set_xlim(0, 95)
    ax.set_xlabel("área (10³ µm², NanGate 45 nm)", fontsize=8)
    ax.tick_params(labelsize=7.5)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "area_v2.png"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [gerado] area_v2.png", r)


TODAS = {"arquitetura": arquitetura, "morfologia": morfologia, "temporizacao": temporizacao,
         "matriz": matriz, "matriz_incart": matriz_incart, "comparacao": comparacao, "porpaciente": porpaciente, "caso232": caso232, "protocolo": protocolo, "area": area}

if __name__ == "__main__":
    os.makedirs(SAIDA, exist_ok=True)
    for n in (sys.argv[1:] or [k for k in TODAS if k != "area"]):
        TODAS[n]()
