#!/bin/bash
# =============================================================================
# sim.sh  —  simula o processador (Xcelium) em registros do MIT-BIH
# -----------------------------------------------------------------------------
# Envia as amostras pelo SPI ao top v2 e grava a classe de cada batimento em
# validacao/dumps/NNN_rtl.txt (comparado depois por python/validar_v2.py).
# Uso (a partir da raiz do repositorio):
#   ./sim.sh 100 232 233            registros completos
#   N=20000 ./sim.sh 100            so as primeiras 20000 amostras
#   SAIDA=/tmp ./sim.sh 100         grava o dump em outra pasta
#   ./sim.sh latencia 233           mede ciclos por etapa (medir_latencia_tb)
# =============================================================================
cd "$(dirname "$0")" || exit 1
N=${N:-650000}
SAIDA=${SAIDA:-validacao/dumps}
RTL="rtl/ecg_processor_top_spi.v rtl/spi_slave.v rtl/ecg_processor_top.v rtl/datapath.v \
     rtl/filter.v rtl/derivator.v rtl/integrator.v rtl/peak_detector.v rtl/ula.v \
     rtl/ram_module.v rtl/fsm.v rtl/morfologia.v rtl/arritmia_classifier_v2.v \
     rtl/classificador_arvore_v2.v rtl/div_serial.v"

TB=rtl/classificar_v2_tb.v
if [ "$1" = "latencia" ]; then TB=rtl/medir_latencia_tb.v; shift; fi
[ $# -eq 0 ] && { sed -n 2,12p "$0"; exit 1; }

mkdir -p "$SAIDA"
for R in "$@"; do
    W=$(mktemp -d)
    mkdir -p "$W/lib"
    if [ "$TB" = rtl/classificar_v2_tb.v ]; then
        xrun -q -xmlibdirpath "$W/lib" -l "$W/xrun.log" $TB $RTL \
            +REG=$R +N=$N +DUMP=$SAIDA/${R}_rtl.txt > /dev/null
        echo "[$R] $(grep -E 'TOTAL' "$W/xrun.log" | tr -s ' ')  ->  $SAIDA/${R}_rtl.txt"
    else
        xrun -q -xmlibdirpath "$W/lib" -l "$W/xrun.log" $TB $RTL +REG=$R +N=$N > /dev/null
        sed -n '/LATENCIA/,/====/p' "$W/xrun.log"
    fi
    grep -E '\*E|\*F|ERRO' "$W/xrun.log" | head -5
    rm -rf "$W"
done
