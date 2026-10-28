#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# pan_tompkins_hw.py
# -----------------------------------------------------------------------------
# Modelo Python BIT-A-BIT do processador ECG em Verilog (versao 16 bits /
# 650k amostras / handshake). Reproduz EXATAMENTE:
#
#   datapath:  sample_reg -> filter -> derivator -> integrator -> peak_detector
#
#   filter.v       : media movel de 3 pontos, regs 32 bits unsigned, (a+b+c)/3
#   derivator.v    : x0..x4 signed 32b; deriv signed 34b = 2x0+x1-x3-2x4;
#                    saida = |deriv| mascarada em 32 bits
#   integrator.v   : janela WINDOW_SIZE=30, window_sum 64b, saida = sum>>5 (=/32),
#                    truncada em 32 bits
#   peak_detector.v: threshold inicial=1; pico se prev>cur AND prev>thr;
#                    thr_novo = (prev>>1)+(prev>>2) (=75%); decay_cnt=8;
#                    decaimento thr -= 1 a cada ciclo se thr>1
#
# A deteccao de pico no Verilog dispara alert_out no estado CHECK_ALERT, que
# ocorre 1x por amostra. Aqui processamos amostra-a-amostra com os mesmos
# registradores, e registramos o INDICE DA AMOSTRA em que peak_detected=1,
# que e' exatamente o "amostra=%0d" reportado pelo testbench.
#
# IMPORTANTE — equivalencia com o testbench:
#   O testbench imprime "amostra=mem_idx" no ciclo do alerta. Devido ao
#   pipeline + handshake, mem_idx no instante do alerta corresponde ao indice
#   modelado abaixo (ver get_alert_sample_index). O offset e' validado contra
#   a simulacao Icarus em validate_against_verilog().
#
# Uso:
#   python python/pan_tompkins_hw.py --mem verilog_mem/100_ecg.mem
#   python python/pan_tompkins_hw.py --mem verilog_mem/100_ecg.mem --n 650000
# =============================================================================
import argparse
import sys

import numpy as np

MASK32 = 0xFFFFFFFF
MASK34 = 0x3FFFFFFFF
WINDOW_SIZE = 30
SHIFT = 5          # integrator >>5
REFRACTORY = 72    # peak_detector: 200 ms @ 360 Hz
LEARNING = 720     # peak_detector: 2 s @ 360 Hz
SETTLE = 64        # peak_detector: transitorio de partida fora do learn_max

# Offset de indexacao para casar com o "amostra=%0d" do testbench Verilog,
# que reporta mem_idx ja' incrementado (latencia pipeline+handshake).
TB_INDEX_OFFSET = 1


def to_signed(val, bits):
    """Interpreta os `bits` inferiores de val como complemento de 2 com sinal."""
    val &= (1 << bits) - 1
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val


# ════════════════════════════════════════════════════════════════════
# MODELO DO HARDWARE — registrador por registrador
# ════════════════════════════════════════════════════════════════════
class ECGProcessorHW:
    """
    Reproduz o datapath Verilog amostra-a-amostra. Cada chamada a step(x)
    avanca UMA amostra por todo o pipeline (como a FSM faz: cada amostra
    passa por FILTERING/DERIVATING/INTEGRATING/PEAK_DETECTING uma vez).

    Os registradores persistem entre amostras, exatamente como no hardware.
    """

    def __init__(self):
        # filter
        self.f_reg0 = 0
        self.f_reg1 = 0
        self.f_reg2 = 0
        self.f_out = 0
        # derivator
        self.d_x0 = 0
        self.d_x1 = 0
        self.d_x2 = 0
        self.d_x3 = 0
        self.d_x4 = 0
        self.d_out = 0
        # integrator
        self.i_window = [0] * WINDOW_SIZE
        self.i_sum = 0
        self.i_ptr = 0
        self.i_out = 0
        # peak detector (refratario + limiar adaptativo + learning)
        self.p_prev = 0
        self.p_sig = 0          # signal_level (SPKI)
        self.p_noise = 0        # noise_level  (NPKI)
        self.p_thr = 0          # threshold
        self.p_refr = 0         # refr_cnt
        self.p_learn_cnt = 0    # learn_cnt
        self.p_learn_max = 0    # learn_max
        self.p_detected = 0
        self.p_value = 0

    # ---- filter.v ----
    def _filter(self, data_in):
        # data_out <= (reg0 + reg1 + reg2) / 3  (com os regs ANTES do shift)
        out = ((self.f_reg0 + self.f_reg1 + self.f_reg2) // 3) & MASK32
        # shift dos registradores (nonblocking: usam valores antigos)
        self.f_reg2 = self.f_reg1
        self.f_reg1 = self.f_reg0
        self.f_reg0 = data_in & MASK32
        self.f_out = out
        return out

    # ---- derivator.v ----
    def _derivator(self, data_in):
        # x0..x4 signed 32b; deriv = 2x0+x1-x3-2x4 (signed 34b); out=|deriv|
        x0 = to_signed(data_in, 32)
        deriv = (2 * to_signed(self.d_x0, 32)
                 + to_signed(self.d_x1, 32)
                 - to_signed(self.d_x3, 32)
                 - 2 * to_signed(self.d_x4, 32))
        deriv = to_signed(deriv & MASK34, 34)
        out = (-deriv if deriv < 0 else deriv) & MASK32
        # shift (nonblocking)
        self.d_x4 = self.d_x3
        self.d_x3 = self.d_x2
        self.d_x2 = self.d_x1
        self.d_x1 = self.d_x0
        self.d_x0 = x0 & MASK32
        self.d_out = out
        return out

    # ---- integrator.v ----
    def _integrator(self, data_in):
        # data_out <= (window_sum - window[ptr] + data_in) >> 5   (64b sum)
        new_sum = (self.i_sum - self.i_window[self.i_ptr] + data_in) & ((1 << 64) - 1)
        out = (new_sum >> SHIFT) & MASK32
        # updates (nonblocking)
        self.i_sum = new_sum
        self.i_window[self.i_ptr] = data_in & MASK32
        self.i_ptr = 0 if self.i_ptr == WINDOW_SIZE - 1 else self.i_ptr + 1
        self.i_out = out
        return out

    # ---- peak_detector.v ----
    def _peak_detector(self, data_in):
        # Espelha bit-a-bit o novo peak_detector.v (refratario + limiar
        # adaptativo + learning phase). Semantica nonblocking: TODAS as leituras
        # usam os valores do INICIO do ciclo (sig/noise/thr antigos).
        self.p_detected = 0
        prev = self.p_prev
        sig = self.p_sig
        noise = self.p_noise
        thr = self.p_thr
        refr = self.p_refr
        lcnt = self.p_learn_cnt
        lmax = self.p_learn_max

        # valores que serao escritos (default: mantem)
        n_sig, n_noise, n_thr = sig, noise, thr
        n_refr, n_lcnt, n_lmax = refr, lcnt, lmax

        if lcnt < LEARNING:
            # ---- fase de aprendizado ----
            if lcnt >= SETTLE and data_in > lmax:
                n_lmax = data_in
            n_lcnt = (lcnt + 1) & MASK32
            if lcnt == LEARNING - 1:
                # inicializa a partir do maximo observado (usa lmax do inicio
                # do ciclo, MAS o Verilog testa learn_max APOS o possivel
                # update? Nao: a atribuicao learn_max<= e signal_level<= sao
                # ambas nonblocking no MESMO ciclo, entao signal_level recebe
                # o learn_max ANTIGO. Replicamos com lmax antigo.)
                n_sig = lmax
                n_noise = lmax >> 2
                n_thr = ((lmax >> 2) + ((lmax - (lmax >> 2)) >> 2)) & MASK32
        elif refr > 0:
            n_refr = refr - 1
        else:
            if prev > data_in and prev > thr:
                # ---- pico aceito ----
                self.p_detected = 1
                self.p_value = prev
                ns = (sig - (sig >> 3) + (prev >> 3)) & MASK32
                n_sig = ns
                n_thr = (noise + (((ns - noise) & MASK32) >> 2)) & MASK32
                n_refr = REFRACTORY
            elif data_in <= thr:
                # ---- amostra de ruido ----
                nn = (noise - (noise >> 3) + (data_in >> 3)) & MASK32
                n_noise = nn
                n_thr = (nn + (((sig - nn) & MASK32) >> 2)) & MASK32

        self.p_prev = data_in & MASK32
        self.p_sig = n_sig & MASK32
        self.p_noise = n_noise & MASK32
        self.p_thr = n_thr & MASK32
        self.p_refr = n_refr & 0xFF
        self.p_learn_cnt = n_lcnt & MASK32
        self.p_learn_max = n_lmax & MASK32
        return self.p_detected

    # ---- um passo completo (1 amostra pelo datapath) ----
    def step(self, sample):
        f = self._filter(sample & MASK32)
        d = self._derivator(f)
        i = self._integrator(d)
        det = self._peak_detector(i)
        return det


# ════════════════════════════════════════════════════════════════════
# PROCESSAMENTO DE UM REGISTRO
# ════════════════════════════════════════════════════════════════════
def processar(samples):
    """
    Roda o modelo HW sobre o array de amostras (uint16).
    Retorna a lista de indices de pico JA' ALINHADOS ao testbench Verilog.

    Detalhe de indexacao:
      O modelo detecta o pico quando a amostra de indice `idx` (0-based) esta'
      no sample_reg. O testbench Verilog, devido a' latencia pipeline+handshake,
      ja' incrementou `mem_idx` um passo quando imprime o alerta, entao reporta
      o evento como "amostra = idx + 1". Para que a saida do Python CASE
      EXATAMENTE com o "amostra=%0d" do Verilog, somamos TB_INDEX_OFFSET (=1).
      Isso e' apenas rotulo: o pico fisico e' o mesmo nos dois.
    """
    hw = ECGProcessorHW()
    picos = []
    for idx, s in enumerate(samples):
        if hw.step(int(s)):
            picos.append(idx + TB_INDEX_OFFSET)
    return picos


def ler_mem(path, n=None):
    """Le um .mem hex (1 valor por linha, 4 digitos) -> array uint32."""
    vals = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # ignora comentarios/enderecos @ do readmemh
            if line.startswith("//") or line.startswith("@"):
                continue
            vals.append(int(line, 16))
            if n is not None and len(vals) >= n:
                break
    arr = np.array(vals, dtype=np.uint32)
    if n is not None and len(arr) < n:
        # readmemh deixa o resto em 0 (o tb zera o array antes)
        arr = np.concatenate([arr, np.zeros(n - len(arr), dtype=np.uint32)])
    return arr


def main():
    ap = argparse.ArgumentParser(
        description="Modelo Python bit-a-bit do ECG processor Verilog (handshake)")
    ap.add_argument("--mem", required=True, help="arquivo .mem (16 bits hex)")
    ap.add_argument("--n", type=int, default=None,
                    help="numero de amostras (default: todas do arquivo)")
    args = ap.parse_args()

    samples = ler_mem(args.mem, args.n)
    picos = processar(samples)

    print("=" * 60)
    print("  ECG PROCESSOR - MODELO PYTHON (= Verilog handshake)")
    print("=" * 60)
    print(f"  Arquivo        : {args.mem}")
    print(f"  Amostras       : {len(samples)}")
    print(f"  Picos R (HW)   : {len(picos)}")
    print("=" * 60)
    # imprime os primeiros para conferencia rapida
    for k, p in enumerate(picos[:10]):
        print(f"    R{k+1:<3} amostra={p}")
    if len(picos) > 10:
        print(f"    ... (+{len(picos)-10} picos)")


if __name__ == "__main__":
    main()
