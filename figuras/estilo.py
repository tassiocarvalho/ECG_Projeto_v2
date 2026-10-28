# -*- coding: utf-8 -*-
# =============================================================================
# estilo.py  —  primitivas de desenho (blocos, registradores, setas, cores)
#   usadas por figuras/gerar_figuras_v2.py
# =============================================================================
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon,
                                Rectangle)

AQUI = os.path.dirname(os.path.abspath(__file__))
DPI = 300
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

# paleta por funcao: (preenchimento, borda)
INTERF = ("#ECE6F6", "#5B4A8B")    # SPI / interface
PROC = ("#E4EEF8", "#2F5D8A")      # estagios de processamento
REG = ("#F2F2F2", "#555555")       # registradores
ULA_C = ("#FFF3D4", "#9A7414")     # ULA
MEM = ("#E2F1E6", "#2E6B46")       # memoria
CTRL = ("#FDE9D2", "#B0601F")      # controle / FSM
CLS = ("#F8E2E5", "#8E3B4A")       # classificador
TINTA = "#262626"
CINZA = "#6B6B6B"
COR_CTRL = "#C0651B"
TRACO = (0, (4, 2.5))


# -----------------------------------------------------------------------------
# primitivas
# -----------------------------------------------------------------------------
def bloco(ax, x, y, w, h, titulo, sub=None, cores=PROC, tt=10.5, ts=8.4, raio=0.12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={raio}",
                                fc=cores[0], ec=cores[1], lw=1.6, zorder=3))
    if sub:
        ax.text(x + w / 2, y + h - 0.15, titulo, ha="center", va="top", fontsize=tt,
                fontweight="bold", color=TINTA, zorder=4)
        ax.text(x + w / 2, y + h - 0.48, sub, ha="center", va="top", fontsize=ts,
                color="#3F3F3F", linespacing=1.35, zorder=4)
    else:
        ax.text(x + w / 2, y + h / 2, titulo, ha="center", va="center", fontsize=tt,
                fontweight="bold", color=TINTA, zorder=4)


def registrador(ax, x, y, w, h, nome, sub=None, tn=8.6):
    ax.add_patch(Rectangle((x, y), w, h, fc=REG[0], ec=REG[1], lw=1.4, zorder=3))
    ax.add_patch(Polygon([(x + w / 2 - 0.09, y), (x + w / 2 + 0.09, y), (x + w / 2, y + 0.13)],
                         closed=True, fc="none", ec=REG[1], lw=1.0, zorder=4))
    ax.text(x + w / 2, y + h / 2 + (0.12 if sub else 0.03), nome, ha="center", va="center",
            fontsize=tn, fontweight="bold", color=TINTA, zorder=4)
    if sub:
        ax.text(x + w / 2, y + h / 2 - 0.2, sub, ha="center", va="center", fontsize=7.4,
                color="#3F3F3F", zorder=4)


def ula(ax, x, y, w, h, sub="7 operações"):
    """Simbolo classico de ULA: entradas A/B no topo (com entalhe), saida embaixo."""
    e = w * 0.18
    pts = [(x, y + h), (x + w / 2 - 0.12, y + h), (x + w / 2, y + h - 0.22),
           (x + w / 2 + 0.12, y + h), (x + w, y + h), (x + w - e, y), (x + e, y)]
    ax.add_patch(Polygon(pts, closed=True, fc=ULA_C[0], ec=ULA_C[1], lw=1.6, zorder=3))
    ax.text(x + w / 2, y + h * 0.47, "ULA", ha="center", va="center", fontsize=11,
            fontweight="bold", color=TINTA, zorder=4)
    duas = "\n" in sub
    ax.text(x + w / 2, y + h * (0.24 if duas else 0.2), sub, ha="center", va="center",
            fontsize=6.6 if duas else 7.4, color="#3F3F3F", linespacing=1.2, zorder=4)
    ax.text(x + w * 0.22, y + h - 0.12, "A", ha="center", va="top", fontsize=8, color=CINZA, zorder=4)
    ax.text(x + w * 0.78, y + h - 0.12, "B", ha="center", va="top", fontsize=8, color=CINZA, zorder=4)
    return (x + w * 0.22, y + h), (x + w * 0.78, y + h), (x + w / 2, y)


def cilindro(ax, x, y, w, h, titulo, sub):
    t = 0.32
    ax.add_patch(Rectangle((x, y + t / 2), w, h - t, fc=MEM[0], ec="none", zorder=3))
    ax.add_patch(Ellipse((x + w / 2, y + t / 2), w, t, fc=MEM[0], ec=MEM[1], lw=1.6, zorder=3))
    ax.add_patch(Rectangle((x, y + t / 2), w, h - t, fc=MEM[0], ec="none", zorder=3.1))
    ax.plot([x, x], [y + t / 2, y + h - t / 2], color=MEM[1], lw=1.6, zorder=3.2)
    ax.plot([x + w, x + w], [y + t / 2, y + h - t / 2], color=MEM[1], lw=1.6, zorder=3.2)
    ax.add_patch(Ellipse((x + w / 2, y + h - t / 2), w, t, fc="#CDE6D4", ec=MEM[1], lw=1.6, zorder=3.3))
    ax.text(x + w / 2, y + h / 2 - 0.02, titulo, ha="center", va="center", fontsize=10.5,
            fontweight="bold", color=TINTA, zorder=4)
    ax.text(x + w / 2, y + h / 2 - 0.34, sub, ha="center", va="center", fontsize=8,
            color="#3F3F3F", zorder=4)


def moldura(ax, x, y, w, h, rotulo, cor="#9A9A9A", ls="-", fc="none", lw=1.3, tam=9.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.18",
                                fc=fc, ec=cor, lw=lw, linestyle=ls, zorder=1))
    ax.text(x + 0.15, y + h - 0.12, rotulo, ha="left", va="top", fontsize=tam,
            fontweight="bold", color=cor, zorder=2)


def linha(ax, pts, cor=TINTA, ls="-", lw=1.4, seta=True, z=2.5):
    """Polilinha ortogonal; ponta de seta no ultimo segmento."""
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=cor, lw=lw, ls=ls, solid_capstyle="butt", zorder=z)
    if seta:
        ax.annotate("", xy=pts[-1], xytext=pts[-2],
                    arrowprops=dict(arrowstyle="-|>", color=cor, lw=0.01, mutation_scale=11,
                                    shrinkA=0, shrinkB=0), zorder=z)


def rot(ax, x, y, txt, ha="left", va="bottom", cor=CINZA, tam=7.6, mono=False, **kw):
    ax.text(x, y, txt, ha=ha, va=va, fontsize=tam, color=cor, zorder=5,
            family="DejaVu Sans Mono" if mono else "DejaVu Sans",
            bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.92), **kw)


def no(ax, x, y, cor=TINTA):
    ax.plot([x], [y], "o", ms=3.6, color=cor, zorder=6)


def salvar(fig, nome):
    p = os.path.join(AQUI, nome)
    fig.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.08)
    plt.close(fig)
    print("  [gerado]", p)


def legenda(ax, x, y, evento=True):
    linha(ax, [(x, y), (x + 0.7, y)])
    ax.text(x + 0.85, y, "dados", va="center", fontsize=8.2, color=TINTA)
    linha(ax, [(x + 1.75, y), (x + 2.45, y)], cor=COR_CTRL, ls=TRACO)
    ax.text(x + 2.6, y, "controle", va="center", fontsize=8.2, color=TINTA)
    if evento:
        linha(ax, [(x + 3.65, y), (x + 4.35, y)], cor=CLS[1])
        ax.text(x + 4.5, y, "evento de pico / índice", va="center", fontsize=8.2, color=TINTA)


def novo(w, h, xmin=0, ymin=0):
    fig, ax = plt.subplots(figsize=(w * 0.82, h * 0.82))
    ax.set_xlim(xmin, xmin + w)
    ax.set_ylim(ymin, ymin + h)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


# -----------------------------------------------------------------------------
# 1) arquitetura completa (alto nivel)
# -----------------------------------------------------------------------------
def arquitetura():
    fig, ax = novo(19.4, 16.4, -0.2, -5.85)

    moldura(ax, 1.2, -4.75, 14.25, 15.2, "ecg_processor_top_spi  ·  escopo sintetizado (Genus)",
            cor="#4D4D4D", lw=1.6, tam=10.5)
    moldura(ax, 4.4, 0.9, 9.3, 9.0, "ecg_processor_top", cor="#8A8A8A")
    moldura(ax, 4.7, 4.2, 8.75, 5.25, "Datapath  (32 bits, aritmética inteira)",
            cor=PROC[1], fc="#F7FAFD")
    moldura(ax, 7.0, -4.45, 8.2, 3.8, "arritmia_classifier", cor=CLS[1], fc="#FFFBFC", tam=10)

    # ---- interface SPI
    for i, s in enumerate(["sclk", "cs_n", "mosi"]):
        yy = 8.45 - i * 0.45
        ax.text(0.0, yy, s, ha="left", va="center", fontsize=9, family="DejaVu Sans Mono")
        linha(ax, [(0.75, yy), (1.6, yy)])
    bloco(ax, 1.6, 7.2, 2.3, 1.75, "Escravo SPI",
          "modo 0, MSB primeiro\nsincronização 2 FF\nshift register 16 b", cores=INTERF, ts=8)
    registrador(ax, 1.6, 4.75, 2.3, 1.35, "Reg. de fronteira", "amostra_reg · valida")
    linha(ax, [(2.75, 7.2), (2.75, 6.1)])
    rot(ax, 2.85, 6.65, "spi_data[31:0]\nspi_valid", va="center")

    # ---- datapath
    registrador(ax, 5.0, 7.95, 1.35, 1.0, "sample_reg", tn=8.2)
    bloco(ax, 6.75, 7.9, 1.55, 1.1, "Filtro", "média de 3")
    bloco(ax, 8.7, 7.9, 1.85, 1.1, "Derivador", "|2x₀+x₁−x₃−2x₄|", ts=8)
    bloco(ax, 10.95, 7.9, 2.25, 1.1, "Integrador MWI", "janela 30, ≫ 5", tt=10)
    bloco(ax, 10.95, 6.0, 2.25, 1.3, "Detector de picos", "limiar adaptativo\nrefratário 200 ms",
          tt=9.6, ts=8)
    a_in, b_in, u_out = ula(ax, 8.4, 5.0, 1.9, 1.3)
    cilindro(ax, 5.2, 4.55, 1.85, 1.85, "Memória", "256 × 32 bits")

    linha(ax, [(3.9, 5.4), (4.15, 5.4), (4.15, 8.45), (5.0, 8.45)])
    rot(ax, 4.24, 6.95, "spi_data_in[31:0]", va="center", rotation=90)
    linha(ax, [(6.35, 8.45), (6.75, 8.45)])
    linha(ax, [(8.3, 8.45), (8.7, 8.45)])
    linha(ax, [(10.55, 8.45), (10.95, 8.45)])
    linha(ax, [(12.1, 7.9), (12.1, 7.3)])
    no(ax, 12.1, 7.6)
    linha(ax, [(12.1, 7.6), (a_in[0], 7.6), a_in])
    rot(ax, 9.35, 7.66, "integrated_data[31:0]")
    linha(ax, [(10.95, 6.55), (b_in[0], 6.55), b_in])
    rot(ax, 10.9, 6.62, "peak_value", ha="right")
    linha(ax, [u_out, (u_out[0], 4.8), (7.05, 4.8)])
    no(ax, u_out[0], 4.8)
    linha(ax, [(u_out[0], 4.8), (u_out[0], 4.55), (15.45, 4.55)], z=2.4)
    linha(ax, [(6.12, 4.55), (6.12, 4.36), (15.45, 4.36)], z=2.4)
    linha(ax, [(13.2, 6.95), (15.45, 6.95)])

    # ---- FSM
    bloco(ax, 5.9, 1.3, 5.0, 1.75, "Unidade de controle (FSM)",
          "12 estados, Moore · 11 ciclos por amostra\ncontador de endereço da memória", cores=CTRL, ts=8.2)
    linha(ax, [(7.3, 3.05), (7.3, 4.2)], cor=COR_CTRL, ls=TRACO)
    rot(ax, 7.18, 3.62, "read_en · filter_en · derivator_en\nintegrator_en · peak_detector_en\n"
                        "ula_op[2:0] · ram_we · ram_addr[7:0]", ha="right", va="center", cor=COR_CTRL, tam=7.3)
    linha(ax, [(9.6, 4.2), (9.6, 3.05)])
    rot(ax, 9.7, 3.62, "peak_detected", va="center")
    linha(ax, [(2.3, 4.75), (2.3, 2.55), (5.9, 2.55)])
    rot(ax, 3.1, 2.6, "data_valid")
    linha(ax, [(5.9, 1.75), (3.2, 1.75), (3.2, 4.75)], cor=COR_CTRL, ls=TRACO)
    rot(ax, 3.3, 1.68, "data_ready", va="top", cor=COR_CTRL)
    linha(ax, [(10.9, 2.55), (15.45, 2.55)])
    linha(ax, [(10.9, 1.75), (15.45, 1.75)])

    for yy, s in [(6.95, "peak_value_out[31:0]"), (4.55, "final_output[31:0]"),
                  (4.36, "ram_data_out[31:0]"), (2.55, "alert_out"), (1.75, "done_out")]:
        va = "top" if s.startswith("ram") else "bottom"
        ax.text(15.3, yy + (-0.05 if va == "top" else 0.05), s, ha="right", va=va, fontsize=7.4,
                color=CINZA, family="DejaVu Sans Mono", zorder=5)

    # ---- classificador (dentro do top sintetizado)
    registrador(ax, 1.6, -2.55, 2.3, 1.45, "Contador de\namostras", "aceitas (valid·ready)", tn=8.4)
    no(ax, 2.3, 2.55)
    linha(ax, [(2.3, 2.55), (2.3, -1.1)])
    no(ax, 3.2, 1.75, cor=COR_CTRL)
    linha(ax, [(3.2, 1.75), (3.2, -1.1)], cor=COR_CTRL, ls=TRACO)
    registrador(ax, 4.35, -2.55, 2.3, 1.45, "Captura do pico", "índice · amplitude", tn=8.4)
    linha(ax, [(3.9, -1.85), (4.35, -1.85)])

    # alert_out e peak_value_out descem do ecg_processor_top para a captura
    no(ax, 14.1, 2.55, cor=CLS[1])
    linha(ax, [(14.1, 2.55), (14.1, 0.35), (6.0, 0.35), (6.0, -1.1)], cor=CLS[1])
    rot(ax, 13.95, 0.42, "alert_out", ha="right", cor=CLS[1], mono=True)
    no(ax, 14.7, 6.95)
    linha(ax, [(14.7, 6.95), (14.7, 0.05), (5.0, 0.05), (5.0, -1.1)])
    rot(ax, 13.95, 0.12, "peak_value_out", ha="right", mono=True)

    registrador(ax, 7.3, -3.85, 2.45, 2.55, "", tn=9.2)
    ax.text(8.525, -1.75, "Histórico", ha="center", va="center", fontsize=9.6,
            fontweight="bold", color=TINTA, zorder=4)
    ax.text(8.525, -2.75, "p0 · p1 · amplitude v0\n\nbuffer RR: 8 × 32 b\nbuffer amp: 32 × 18 b",
            ha="center", va="center",
            fontsize=7.4, color="#3F3F3F", linespacing=1.35, zorder=4)
    linha(ax, [(6.65, -1.85), (7.3, -1.85)], cor=CLS[1])
    rot(ax, 6.7, -1.5, "new_peak", cor=CLS[1], mono=True, tam=6.8)
    bloco(ax, 10.15, -3.85, 2.3, 2.55, "Divisor serial",
          "1 bit por ciclo\ncompartilhado\nmédias e razões\n≈ 170 ciclos\napós cada pico", cores=CLS, ts=7.6, tt=9.6)
    linha(ax, [(9.75, -2.6), (10.15, -2.6)])
    bloco(ax, 12.85, -3.85, 2.1, 2.55, "Árvore de\ndecisão",
          "\n\nprofundidade 4\n12 comparadores\n\nrr_ratio · amp_ratio\n(do divisor)", cores=CLS, ts=7.0, tt=9.6)
    linha(ax, [(12.45, -2.6), (12.85, -2.6)])
    linha(ax, [(8.525, -1.3), (8.525, -1.05), (13.9, -1.05), (13.9, -1.3)])
    rot(ax, 11.2, -1.0, "rr_prev · rr_next", ha="center", tam=7.0, mono=True)

    for i, s in enumerate(["classe_out[2:0]", "classe_valid", "peak_classificado"]):
        yy = -2.15 - i * 0.42
        linha(ax, [(14.95, yy), (15.75, yy)])
        ax.text(15.8, yy, s, ha="left", va="center", fontsize=7.8, family="DejaVu Sans Mono")
    ax.text(11.1, -4.25, "classes AAMI: N · SVEB · VEB · F · Q", ha="center", va="center",
            fontsize=7.6, color=CINZA, style="italic")

    legenda(ax, 4.6, -5.4)
    salvar(fig, "arquitetura_completa.png")


# -----------------------------------------------------------------------------
# 2) datapath detalhado
# -----------------------------------------------------------------------------
def datapath():
    fig, ax = novo(17.8, 8.4, -0.2, -0.4)
    moldura(ax, 1.6, 0.55, 12.85, 6.75, "datapath", cor=PROC[1], fc="#F7FAFD", tam=10)

    registrador(ax, 2.0, 4.5, 1.4, 1.0, "sample_reg", tn=8.2)
    bloco(ax, 3.8, 4.45, 1.9, 1.1, "Filtro", "(a+b+c) / 3")
    bloco(ax, 6.1, 4.45, 2.05, 1.1, "Derivador", "|2x₀+x₁−x₃−2x₄|", ts=8)
    bloco(ax, 8.55, 4.45, 2.3, 1.1, "Integrador MWI", "Σ 30 amostras ≫ 5", tt=10)
    bloco(ax, 10.95, 2.25, 3.05, 1.5, "Detector de picos",
          "limiar = ruído + (sinal − ruído) / 4\nrefratário 72 · aprendizado 720", tt=10, ts=7.6)
    a_in, b_in, u_out = ula(ax, 6.9, 1.75, 2.45, 1.5, sub="ADD SUB AND OR\nXOR PASS_A PASS_B")
    cilindro(ax, 3.3, 0.85, 2.0, 2.05, "Memória", "256 × 32 bits")

    # entrada
    ax.text(0.0, 5.07, "spi_data_in[31:0]", ha="left", va="bottom", fontsize=8, family="DejaVu Sans Mono")
    linha(ax, [(0.0, 5.0), (2.0, 5.0)])
    linha(ax, [(3.4, 5.0), (3.8, 5.0)])
    linha(ax, [(5.7, 5.0), (6.1, 5.0)])
    linha(ax, [(8.15, 5.0), (8.55, 5.0)])
    # integrador -> detector e ULA.A
    linha(ax, [(10.85, 5.0), (12.15, 5.0), (12.15, 3.75)])
    no(ax, 11.15, 5.0)
    linha(ax, [(11.15, 5.0), (11.15, 3.95), (a_in[0], 3.95), a_in])
    rot(ax, 9.0, 4.02, "integrated_data[31:0]")
    # detector -> ULA.B e saidas
    linha(ax, [(10.95, 3.4), (b_in[0], 3.4), b_in])
    rot(ax, 10.9, 3.46, "peak_value[31:0]", ha="right")
    linha(ax, [(14.0, 3.35), (15.25, 3.35)])
    linha(ax, [(14.0, 2.75), (15.25, 2.75)])
    ax.text(15.3, 3.35, "peak_detected_out", va="center", fontsize=8, family="DejaVu Sans Mono")
    ax.text(15.3, 2.75, "peak_value_out[31:0]", va="center", fontsize=8, family="DejaVu Sans Mono")
    # ULA -> memoria e datapath_output
    linha(ax, [u_out, (u_out[0], 1.3), (5.3, 1.3)])
    no(ax, u_out[0], 1.3)
    linha(ax, [(u_out[0], 1.3), (u_out[0], -0.1)])
    ax.text(u_out[0] + 0.1, 0.05, "datapath_output[31:0]  (ula_result)", va="bottom", fontsize=8,
            family="DejaVu Sans Mono")
    rot(ax, 6.1, 1.36, "ula_result")
    # memoria -> ram_data_out
    linha(ax, [(3.3, 1.5), (0.0, 1.5)])
    ax.text(0.0, 1.56, "ram_data_out[31:0]", va="bottom", fontsize=8, family="DejaVu Sans Mono")

    # controle (da FSM)
    ax.text(0.0, 6.65, "da FSM", ha="left", va="center", fontsize=8.4, color=COR_CTRL, fontweight="bold")
    ax.plot([0.75, 12.6], [6.65, 6.65], color=COR_CTRL, lw=1.4, ls=TRACO, zorder=2)
    for xx, s, alvo in [(2.7, "read_en", 5.5), (4.75, "filter_en", 5.55), (7.12, "derivator_en", 5.55),
                        (9.7, "integrator_en", 5.55)]:
        linha(ax, [(xx, 6.65), (xx, alvo)], cor=COR_CTRL, ls=TRACO)
        rot(ax, xx + 0.08, 6.0, s, cor=COR_CTRL, tam=7.4, mono=True, va="center")
    ax.plot([12.6, 13.5], [6.65, 6.65], color=COR_CTRL, lw=1.4, ls=TRACO, zorder=2)
    linha(ax, [(13.5, 6.65), (13.5, 3.75)], cor=COR_CTRL, ls=TRACO)
    rot(ax, 13.6, 5.2, "peak_detector_en", cor=COR_CTRL, tam=7.4, mono=True, va="center", rotation=90)
    for yy, s, alvo in [(3.55, "ula_op[2:0]", (7.15, 2.45))]:
        linha(ax, [(0.75, yy), (6.5, yy), (6.5, alvo[1]), (alvo[0], alvo[1])], cor=COR_CTRL, ls=TRACO)
        rot(ax, 0.8, yy + 0.05, s, cor=COR_CTRL, tam=7.4, mono=True)
    for yy, s in [(2.5, "ram_we"), (2.05, "ram_addr[7:0]")]:
        linha(ax, [(0.75, yy), (3.3, yy)], cor=COR_CTRL, ls=TRACO)
        rot(ax, 0.8, yy + 0.04, s, cor=COR_CTRL, tam=7.4, mono=True)

    legenda(ax, 6.0, -0.32, evento=False)
    salvar(fig, "datapath.png")


# -----------------------------------------------------------------------------
# 3) FSM (12 estados, Moore)
# -----------------------------------------------------------------------------
def estado(ax, x, y, nome, w=2.2, h=0.8, cor=CTRL):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.38",
                                fc=cor[0], ec=cor[1], lw=1.6, zorder=3))
    ax.text(x + w / 2, y + h / 2, nome, ha="center", va="center", fontsize=8.8,
            fontweight="bold", color=TINTA, family="DejaVu Sans Mono", zorder=4)


def fsm():
    fig, ax = novo(17.6, 6.9, -0.6, -0.9)
    W, H = 2.2, 0.8
    topo = ["IDLE", "READ_DATA", "FILTERING", "WAIT_FILTER", "DERIVATING", "WAIT_DERIV"]
    base = ["FINISHED", "CHECK_ALERT", "STORE_RESULT", "PEAK_DETECTING", "WAIT_INTEG", "INTEGRATING"]
    xs = [0.6 + i * 2.75 for i in range(6)]
    yt, yb = 3.7, 0.9
    saida = {
        "READ_DATA": "read_en\ndata_ready", "FILTERING": "filter_en", "DERIVATING": "derivator_en",
        "INTEGRATING": "integrator_en", "PEAK_DETECTING": "peak_detector_en",
        "STORE_RESULT": "ram_we\nula_op = PASS_A", "CHECK_ALERT": "alert_out =\npeak_detected",
        "FINISHED": "done_out",
    }
    espera = {"WAIT_FILTER", "WAIT_DERIV", "WAIT_INTEG"}
    for x, n in zip(xs, topo):
        estado(ax, x, yt, n, cor=REG if n in espera or n == "IDLE" else CTRL)
        if n in saida:
            ax.text(x + W / 2, yt + H + 0.12, saida[n], ha="center", va="bottom", fontsize=7.6,
                    color=COR_CTRL, family="DejaVu Sans Mono", linespacing=1.25)
    for x, n in zip(xs, base):
        estado(ax, x, yb, n, cor=REG if n in espera else CTRL)
        if n in saida:
            ax.text(x + W / 2, yb - 0.12, saida[n], ha="center", va="top", fontsize=7.6,
                    color=COR_CTRL, family="DejaVu Sans Mono", linespacing=1.25)
    # cadeia
    for i in range(5):
        linha(ax, [(xs[i] + W, yt + H / 2), (xs[i + 1], yt + H / 2)])
        linha(ax, [(xs[i + 1], yb + H / 2), (xs[i] + W, yb + H / 2)])
    xr = xs[5] + W
    linha(ax, [(xr, yt + H / 2), (xr + 0.45, yt + H / 2), (xr + 0.45, yb + H / 2), (xr, yb + H / 2)])
    # reset e IDLE
    linha(ax, [(-0.45, yt + H / 2), (xs[0], yt + H / 2)])
    ax.text(-0.45, yt + H / 2 + 0.08, "rst", va="bottom", fontsize=8.6, family="DejaVu Sans Mono")
    ax.add_patch(FancyArrowPatch((xs[0] + 0.55, yt + H), (xs[0] + 1.25, yt + H),
                                 connectionstyle="arc3,rad=-1.6", arrowstyle="-|>",
                                 mutation_scale=11, color=TINTA, lw=1.3, zorder=2))
    ax.text(xs[0] + 0.9, yt + H + 0.62, "!data_valid", ha="center", va="bottom", fontsize=7.8,
            family="DejaVu Sans Mono", color=TINTA)
    ax.text(xs[0] + W + 0.28, yt + H + 0.08, "data_valid", ha="center", va="bottom", fontsize=7.6,
            family="DejaVu Sans Mono", color=TINTA)
    # FINISHED -> IDLE (!data_valid)  e  FINISHED -> READ_DATA (data_valid)
    linha(ax, [(xs[0] + 0.7, yb + H), (xs[0] + 0.7, yt)])
    rot(ax, xs[0] + 0.62, (yb + H + yt) / 2, "!data_valid", ha="right", va="center", mono=True,
        cor=TINTA, tam=7.6)
    linha(ax, [(xs[0] + 1.6, yb + H), (xs[0] + 1.6, (yb + H + yt) / 2), (xs[1] + 0.8, (yb + H + yt) / 2),
               (xs[1] + 0.8, yt)])
    rot(ax, xs[0] + 1.7, (yb + H + yt) / 2 + 0.06, "data_valid", mono=True, cor=TINTA, tam=7.6)
    ax.text(xs[2] + 0.2, (yb + H + yt) / 2, "WAIT_*: ciclo de espera para o registrador do estágio anterior estabilizar",
            ha="left", va="center", fontsize=7.6, color=CINZA, style="italic")
    ax.text(xs[2] + 0.2, (yb + H + yt) / 2 - 0.36, "STORE_RESULT: o endereço da memória avança no ciclo seguinte",
            ha="left", va="center", fontsize=7.6, color=CINZA, style="italic")
    ax.text(xs[0], -0.75, "saídas (Moore) em laranja; sinais não indicados permanecem em 0",
            fontsize=7.6, color=CINZA, va="bottom")
    salvar(fig, "fsm.png")


# -----------------------------------------------------------------------------
# 4) trabalhos relacionados (posicionamento conceitual)
# -----------------------------------------------------------------------------
def trabalhos():
    fig, ax = novo(12.4, 8.4, -1.0, -0.9)
    faixas = [(0.0, 1.9, "nenhuma — apenas detecção", "#FAFAFA"),
              (1.9, 4.2, "características temporais", "#F4F4F4"),
              (4.2, 7.2, "características morfológicas + RR", "#ECECEC")]
    for y0, y1, txt, cor in faixas:
        ax.add_patch(Rectangle((0, y0), 11, y1 - y0, fc=cor, ec="none", zorder=0))
        ax.text(0.15, y1 - 0.12, txt, fontsize=8.2, style="italic", color="#8A8A8A", va="top")
    linha(ax, [(0, 0), (11.2, 0)], cor="#555555", lw=1.2)
    linha(ax, [(0, 0), (0, 7.4)], cor="#555555", lw=1.2)
    ax.text(5.6, -0.5, "Complexidade computacional da inferência", ha="center", fontsize=10)
    ax.text(-0.55, 3.6, "Informação utilizada na classificação", ha="center", va="center",
            rotation=90, fontsize=10)

    def caixa(x, y, w, h, t, s, cores, ls="-"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12",
                                    fc=cores[0], ec=cores[1], lw=1.6, ls=ls, zorder=3))
        ax.text(x + w / 2, y + h - 0.16, t, ha="center", va="top", fontsize=10.5, fontweight="bold", zorder=4)
        ax.text(x + w / 2, y + h - 0.55, s, ha="center", va="top", fontsize=8.4, color="#3F3F3F",
                linespacing=1.35, zorder=4)

    caixa(0.5, 0.2, 3.4, 1.25, "Pan e Tompkins [1]", "detecção de QRS\nnão realiza classificação",
          REG, ls=(0, (4, 2.5)))
    caixa(1.8, 2.25, 4.0, 1.65, "Este trabalho",
          "4 características causais\nRR + amplitude relativa\nárvore com 12 comparadores",
          ("#FBE6C2", "#A0611B"))
    caixa(5.4, 5.55, 3.6, 1.3, "de Chazal et al. [2]", "26 características\nmorfologia + RR", PROC)
    caixa(7.2, 4.35, 3.6, 1.1, "Farag [5]", "CNN sobre a forma de onda", PROC)
    salvar(fig, "trabalhos_relacionados.png")


if __name__ == "__main__":
    arquitetura()
    datapath()
    fsm()
    trabalhos()
