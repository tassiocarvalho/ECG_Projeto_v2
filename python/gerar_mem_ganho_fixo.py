#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# gerar_mem_ganho_fixo.py
# -----------------------------------------------------------------------------
# Gera os arquivos NNN_ecg.mem (1 amostra hex de 16 bits por linha, lidos pelo
# $readmemh dos testbenches e pelo pan_tompkins_hw.ler_mem) a partir do ADC
# BRUTO do MIT-BIH, com GANHO FIXO:
#
#       amostra = ADC * 32        (ADC de 11 bits, 0..2047 -> 0..65504)
#
# Por que ganho fixo: normalizar por registro (minimo/maximo do registro
# inteiro) usa informacao futura do sinal e nao existe num dispositivo em
# tempo real. Aqui o ganho e' o mesmo para todos os registros e todas as
# amostras, como num front-end analogico + ADC reais (MIT-BIH: 200 unidades
# de ADC por mV).
#
# Canal: MLII quando existe (no 114 e' o 2o canal); senao o 1o canal
# (102 e 104 nao tem MLII).
#
# Uso:
#   python python/gerar_mem_ganho_fixo.py
#   python python/gerar_mem_ganho_fixo.py --out dados/verilog_mem --ganho 32
# =============================================================================
import argparse
import os

import numpy as np
import wfdb

AQUI = os.path.dirname(os.path.abspath(__file__))
PROJETO = os.path.dirname(AQUI)

RECORDS = [
    "100", "101", "102", "103", "104", "105", "106", "107", "108", "109",
    "111", "112", "113", "114", "115", "116", "117", "118", "119", "121",
    "122", "123", "124", "200", "201", "202", "203", "205", "207", "208",
    "209", "210", "212", "213", "214", "215", "217", "219", "220", "221",
    "222", "223", "228", "230", "231", "232", "233", "234",
]


def main():
    ap = argparse.ArgumentParser(description="Gera .mem com ganho fixo a partir do ADC bruto")
    ap.add_argument("--atr", default=os.path.join(PROJETO, "dados", "mitdb"))
    ap.add_argument("--out", default=os.path.join(PROJETO, "dados", "verilog_mem"))
    ap.add_argument("--ganho", type=int, default=32, help="fator inteiro (32 = ADC de 11 b em 16 b)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    satur = 0
    for rec in RECORDS:
        r = wfdb.rdrecord(os.path.join(args.atr, rec), physical=False)
        k = r.sig_name.index("MLII") if "MLII" in r.sig_name else 0
        adc = r.d_signal[:, k].astype(np.int64)
        x = adc * args.ganho
        satur += int(((x < 0) | (x > 0xFFFF)).sum())
        x = np.clip(x, 0, 0xFFFF)
        with open(os.path.join(args.out, f"{rec}_ecg.mem"), "w") as f:
            f.write("\n".join(f"{v:04X}" for v in x))
            f.write("\n")
        print(f"  {rec}: canal {r.sig_name[k]:<4} ADC [{adc.min():4d}, {adc.max():4d}]  "
              f"-> [{x.min():5d}, {x.max():5d}]  {len(x)} amostras")
    print(f"  amostras saturadas: {satur}")
    print(f"  saida: {args.out}")


if __name__ == "__main__":
    main()
