#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# gerar_treino.py
# -----------------------------------------------------------------------------
# Gera o dataset de treino para o classificador de arritmia, casando os picos
# DETECTADOS PELO SEU PIPELINE (pan_tompkins_hw) com os rotulos reais do .atr
# do MIT-BIH. Para cada pico detectado:
#   - encontra o batimento anotado mais proximo (dentro de TOLERANCIA amostras)
#   - herda o rotulo desse batimento (N, V, A, ...)
#   - calcula features inteiras baseadas em RR (as MESMAS que o Verilog usara')
#
# Saida: treino.csv  com colunas:
#   registro, amostra, rr_prev, rr_next, rr_ratio_x256, amp_mwi,
#   amp_ratio_x256, label_raw, classe
#
# Onde:
#   rr_prev     = RR anterior  (amostras)            [inteiro]
#   rr_next     = RR posterior (amostras)            [inteiro]
#   rr_ratio_x256 = (rr_prev * 256) / rr_media_local [inteiro, ponto fixo /256]
#   amp_mwi     = valor do MWI no pico (informativo; depende do ganho)
#   amp_ratio_x256 = (amp_mwi * 256) / media das 32 amplitudes anteriores
#   classe      = 0:N  1:SVEB  2:VEB  3:F  4:Q   (superclasses AAMI EC57)
#
# IMPORTANTE: as features sao TODAS inteiras e calculadas exatamente como o
# Verilog ira' calcular, para preservar a equivalencia bit-a-bit.
#
# Uso (no SEU PC, com os .atr disponiveis):
#   python python/gerar_treino.py --mem ./verilog_mem --atr ./mitdb --out python/dados/treino.csv
#   (--atr = pasta com 100.atr, 100.hea, 100.dat, ... do PhysioNet)
#
# Para baixar os .atr (uma vez):
#   python -c "import wfdb; wfdb.dl_database('mitdb','./mitdb')"
# =============================================================================
import argparse
import os
import sys
import csv

# caminhos fixos a partir da pasta deste script (roda de qualquer lugar)
AQUI    = os.path.dirname(os.path.abspath(__file__))   # python/
PROJETO = os.path.dirname(AQUI)                        # raiz do repositorio
DADOS   = os.path.join(AQUI, "dados")                  # CSVs de treino

try:
    import wfdb
except ImportError:
    sys.exit("ERRO: pip install wfdb")

try:
    from pan_tompkins_hw import ECGProcessorHW, ler_mem, TB_INDEX_OFFSET
except ImportError:
    sys.exit("ERRO: pan_tompkins_hw.py precisa estar na mesma pasta.")

RECORDS = [
    "100", "101", "102", "103", "104", "105", "106", "107", "108", "109",
    "111", "112", "113", "114", "115", "116", "117", "118", "119", "121",
    "122", "123", "124", "200", "201", "202", "203", "205", "207", "208",
    "209", "210", "212", "213", "214", "215", "217", "219", "220", "221",
    "222", "223", "228", "230", "231", "232", "233", "234",
]

# Tolerancia (amostras) para casar pico detectado <-> batimento anotado.
# 36 amostras = 100 ms @ 360 Hz: se o pico esta' a <100ms de um batimento
# anotado, consideramos que sao o mesmo batimento.
TOLERANCIA = 36

# ============================================================================
# MAPEAMENTO AAMI EC57 (padrao da area p/ publicacao) — 5 superclasses.
# ----------------------------------------------------------------------------
#   0 = N    (Normal)        : N, L, R, e, j   (normal + bloqueios de ramo +
#                              escapes atrial/nodal — todos "nao-ectopicos")
#   1 = SVEB (Supraventric.) : A, a, J, S       (ectopicos supraventriculares)
#   2 = VEB  (Ventricular)   : V, E             (ectopicos ventriculares)
#   3 = F    (Fusion)        : F                (fusao ventricular+normal)
#   4 = Q    (Unknown)       : /, f, Q          (marcapasso + nao classificavel)
#
# Conforme ANSI/AAMI EC57 e De Chazal et al. (2004). Note que L e R (bloqueios)
# entram em Normal pelo padrao AAMI — diferente do agrupamento clinico-por-RR
# anterior. As metricas de interesse clinico/AAMI sao SVEB e VEB.
#
# Registros com marcapasso (102,104,107,217) sao EXCLUIDOS por recomendacao
# AAMI -> restam 44 registros, divididos em DS1 (treino) e DS2 (teste).
# ============================================================================
AAMI_N    = set(['N', 'L', 'R', 'e', 'j'])
AAMI_SVEB = set(['A', 'a', 'J', 'S'])
AAMI_VEB  = set(['V', 'E'])
AAMI_F    = set(['F'])
AAMI_Q    = set(['/', 'f', 'Q'])

BEAT_SYMBOLS = set(['N','L','R','B','A','a','J','S','V','r','F','e','j','n',
                    'E','/','f','Q','?'])

# Divisao inter-patient de De Chazal et al. (2004) — padrao da literatura.
DS1 = ["101","106","108","109","112","114","115","116","118","119","122",
       "124","201","203","205","207","208","209","215","220","223","230"]
DS2 = ["100","103","105","111","113","117","121","123","200","202","210",
       "212","213","214","219","221","222","228","231","232","233","234"]
# Excluidos (marcapasso): 102, 104, 107, 217


def classe_de(sym):
    """Mapeia simbolo MIT-BIH -> classe AAMI (0..4), ou -1 se nao for batimento."""
    if sym in AAMI_N:    return 0
    if sym in AAMI_SVEB: return 1
    if sym in AAMI_VEB:  return 2
    if sym in AAMI_F:    return 3
    if sym in AAMI_Q:    return 4
    return -1


def detectar_picos(mem_path, n=None):
    """Roda o pipeline HW e retorna (indices de pico, peak_value de cada pico).
    peak_value e' o valor do MWI no pico (= self.p_value do peak_detector,
    exatamente o que o hardware expoe em peak_value_out). Usado como feature
    de amplitude (amp_mwi)."""
    samples = ler_mem(mem_path, n)
    hw = ECGProcessorHW()
    picos = []
    pvals = []
    for idx, s in enumerate(samples):
        if hw.step(int(s)):
            picos.append(idx + TB_INDEX_OFFSET)
            pvals.append(int(hw.p_value))
    return picos, pvals


def features_rr(picos):
    """
    Calcula as features inteiras replicando EXATAMENTE a ordem de registradores
    do arritmia_classifier.v (mesma logica de classificar_python.py), para que
    o treino use features identicas as que o hardware vera'.
    Retorna lista de tuplas (idx_pico, rr_prev, rr_next, rr_ratio_x256).
    """
    K = 8
    out = []
    p0 = p1 = p2 = 0
    n_peaks = 0
    rr_hist = [0] * K
    rr_sum = 0
    rr_cnt = 0
    rr_ptr = 0

    for pk in picos:
        c_rr_prev = p0 - p1
        c_rr_next = pk - p0
        c_media = c_rr_prev if rr_cnt == 0 else rr_sum // rr_cnt
        c_media_s = 1 if c_media == 0 else c_media
        c_ratio = (c_rr_prev * 256) // c_media_s
        if n_peaks >= 2:
            out.append((p0, c_rr_prev, c_rr_next, c_ratio))
            rr_sum = rr_sum - rr_hist[rr_ptr] + c_rr_prev
            rr_hist[rr_ptr] = c_rr_prev
            rr_ptr = 0 if rr_ptr == K - 1 else rr_ptr + 1
            if rr_cnt < K:
                rr_cnt += 1
        p2, p1, p0 = p1, p0, pk
        if n_peaks < 3:
            n_peaks += 1
    return out


def amp_ratio(amps, K=32):
    """amp_ratio_x256 = amp_mwi*256 / media das K amplitudes ANTERIORES
    (causal; 1o batimento: ele mesmo). Mesma ordem de registradores do
    buffer de amplitude do arritmia_classifier.v. `amps` segue a ordem dos
    batimentos classificados (saida de features_rr)."""
    out, hist, soma, cnt, ptr = [], [0] * K, 0, 0, 0
    for v in amps:
        m = v if cnt == 0 else soma // cnt
        m = 1 if m == 0 else m
        out.append((v * 256) // m)
        soma = soma - hist[ptr] + v
        hist[ptr] = v
        ptr = 0 if ptr == K - 1 else ptr + 1
        cnt = min(cnt + 1, K)
    return out


def main():
    ap = argparse.ArgumentParser(description="Gera dataset de treino (picos+.atr)")
    ap.add_argument("--mem", default=os.path.join(PROJETO, "dados", "verilog_mem"),
                    help="pasta com NNN_ecg.mem")
    ap.add_argument("--atr", default=os.path.join(PROJETO, "dados", "mitdb"),
                    help="pasta com os arquivos WFDB (NNN.atr/.hea/.dat)")
    ap.add_argument("--out", default=os.path.join(DADOS, "treino.csv"), help="CSV de saida")
    ap.add_argument("--n", type=int, default=None,
                    help="limite de amostras por registro (default: todas)")
    ap.add_argument("--records", nargs="*", default=None,
                    help="subconjunto de registros (sobrepoe --conjunto)")
    ap.add_argument("--conjunto", choices=["ds1", "ds2", "todos"], default="todos",
                    help="ds1=treino, ds2=teste (inter-patient De Chazal); "
                         "todos=44 registros AAMI")
    args = ap.parse_args()

    if args.records:
        recs = args.records
    elif args.conjunto == "ds1":
        recs = DS1
    elif args.conjunto == "ds2":
        recs = DS2
    else:
        recs = DS1 + DS2   # 44 registros AAMI (exclui marcapasso 102,104,107,217)
    linhas = []
    cont_classe = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    casados = 0
    sem_par = 0
    descartados_morf = 0

    for rec in recs:
        mem_path = os.path.join(args.mem, f"{rec}_ecg.mem")
        atr_base = os.path.join(args.atr, rec)
        if not os.path.isfile(mem_path):
            print(f"[skip] {rec}: {rec}_ecg.mem nao encontrado")
            continue
        try:
            ann = wfdb.rdann(atr_base, 'atr')
        except Exception as e:
            print(f"[skip] {rec}: nao li .atr ({e})")
            continue

        # batimentos anotados: (amostra, simbolo) apenas para simbolos de batimento
        anot = [(int(s), sym) for s, sym in zip(ann.sample, ann.symbol)
                if sym in BEAT_SYMBOLS]
        anot_samp = [a[0] for a in anot]

        picos, pvals = detectar_picos(mem_path, args.n)
        feats = features_rr(picos)
        # mapa amostra->peak_value (amp_mwi), alinhado por indice de pico
        amp_por_amostra = {}
        for _i in range(1, len(picos) - 1):
            amp_por_amostra[picos[_i]] = pvals[_i]

        ratios_amp = amp_ratio([amp_por_amostra.get(a[0], 0) for a in feats])

        # casa cada pico com o batimento anotado mais proximo (busca linear
        # com ponteiro, pois ambos estao ordenados)
        j = 0
        for (amostra, rr_prev, rr_next, ratio), amp_r in zip(feats, ratios_amp):
            # avanca o ponteiro ate o anotado mais proximo
            while j + 1 < len(anot_samp) and \
                  abs(anot_samp[j+1] - amostra) <= abs(anot_samp[j] - amostra):
                j += 1
            if j < len(anot_samp) and abs(anot_samp[j] - amostra) <= TOLERANCIA:
                sym = anot[j][1]
                cls = classe_de(sym)
                if cls < 0:
                    # simbolo que nao e' batimento valido AAMI: ignorado.
                    descartados_morf += 1
                    continue
                amp_mwi = amp_por_amostra.get(amostra, 0)
                linhas.append([rec, amostra, rr_prev, rr_next, ratio, amp_mwi,
                               amp_r, sym, cls])
                cont_classe[cls] += 1
                casados += 1
            else:
                sem_par += 1

        print(f"[ok] {rec}: {len(picos)} picos, {len(anot)} anotados, "
              f"{casados} casados acumulado")

    # escreve CSV
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["registro", "amostra", "rr_prev", "rr_next",
                    "rr_ratio_x256", "amp_mwi", "amp_ratio_x256", "label_raw", "classe"])
        w.writerows(linhas)

    print("=" * 56)
    print(f"  Dataset salvo em: {args.out}")
    print(f"  Conjunto: {args.conjunto}  ({len(recs)} registros)")
    print(f"  Linhas (batimentos AAMI)      : {len(linhas)}")
    print(f"  Sem par no .atr (descartados) : {sem_par}")
    print(f"  Simbolos nao-batimento        : {descartados_morf}")
    print("  ----  classes AAMI EC57  ----")
    print(f"  0 N    (Normal)         : {cont_classe[0]}")
    print(f"  1 SVEB (Supraventric.)  : {cont_classe[1]}")
    print(f"  2 VEB  (Ventricular)    : {cont_classe[2]}")
    print(f"  3 F    (Fusion)         : {cont_classe[3]}")
    print(f"  4 Q    (Unknown)        : {cont_classe[4]}")
    print("=" * 56)


if __name__ == "__main__":
    main()
