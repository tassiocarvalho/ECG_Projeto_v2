# -*- coding: utf-8 -*-
# =============================================================================
# baixar_dados.py  —  baixa as bases do PhysioNet e gera as entradas do RTL
# -----------------------------------------------------------------------------
# As bases nao vao no repositorio (licenca ODC-By do PhysioNet e tamanho):
#   dados/mitdb/        MIT-BIH Arrhythmia Database        (~100 MB, obrigatoria)
#   dados/verilog_mem/  NNN_ecg.mem gerados a partir da mitdb (ganho fixo ADC*32)
#   dados/svdb/         MIT-BIH Supraventricular (--svdb)  (~700 MB, externa)
#   dados/incart/       St Petersburg INCART     (--incart) (~830 MB, externa)
# Arquivos ja presentes sao mantidos (o wfdb baixa so o que falta).
# Uso: python python/baixar_dados.py [--svdb] [--incart]
# =============================================================================
import argparse
import os
import subprocess
import sys

import wfdb

AQUI = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(os.path.dirname(AQUI), "dados")


def baixa(base, pasta):
    destino = os.path.join(DADOS, pasta)
    os.makedirs(destino, exist_ok=True)
    print(f"[{base}] baixando para {destino} ...", flush=True)
    wfdb.dl_database(base, destino, overwrite=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--svdb", action="store_true", help="tambem baixa a SVDB (validacao externa)")
    ap.add_argument("--incart", action="store_true", help="tambem baixa a INCART (validacao externa)")
    a = ap.parse_args()
    baixa("mitdb", "mitdb")
    subprocess.run([sys.executable, os.path.join(AQUI, "gerar_mem_ganho_fixo.py")], check=True)
    if a.svdb:
        baixa("svdb", "svdb")
    if a.incart:
        baixa("incartdb", "incart")
    print("pronto")
