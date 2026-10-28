#!/bin/bash
# =============================================================================
# sintetizar.sh  —  atividade real (Xcelium) + sintese logica (Genus)
# -----------------------------------------------------------------------------
# 1) potencia_tb: 10 s do registro 100 a 1 MHz, SPI a 100 kHz -> atividade.tcf
# 2) Genus: le o RTL, sintetiza, aplica o TCF e gera os relatorios em
#    sintese/reports_<nome>/ (area por bloco, timing, potencia, QoR).
# Uso (a partir da raiz do repositorio):
#   LIB=/caminho/NangateOpenCellLibrary_typical.lib ./sintese/sintetizar.sh
#   LIB=... NOME=minha_lib ./sintese/sintetizar.sh
# =============================================================================
[ -n "$LIB" ] && LIB=$(readlink -f "$LIB")   # caminho absoluto antes do cd
cd "$(dirname "$0")" || exit 1
[ -f "$LIB" ] || { echo "defina LIB=<arquivo .lib>"; exit 1; }
NOME=${NOME:-nangate45}
RTL="ecg_processor_top_spi spi_slave arritmia_classifier_v2 classificador_arvore_v2 morfologia
     div_serial ecg_processor_top fsm datapath filter derivator integrator peak_detector ula ram_module"
W=$(mktemp -d)
mkdir -p "$W/LIB" "$W/RTL" "$W/constraints" "$W/xc"

echo "=== 1) atividade de chaveamento (registro 100, 10 s)"
FL=""; for f in $RTL; do FL="$FL ../rtl/$f.v"; done
xrun -q -access +r -xmlibdirpath "$W/xc" -l "$W/xc/xrun.log" potencia_tb.v $FL \
    -input tcf.tcl +REG=100 +N=3600 > /dev/null
grep -E '\*E|\*F|ERRO' "$W/xc/xrun.log" | head -5
cp atividade.tcf "$W/"

echo "=== 2) Genus"
cp "$LIB" "$W/LIB/"
for f in $RTL; do cp ../rtl/$f.v "$W/RTL/"; done
cp constraints_top.sdc "$W/constraints/"
cp genus_script.tcl "$W/"
( cd "$W" && genus -no_gui -execute "set LIB_NOME $(basename "$LIB")" \
      -files genus_script.tcl -log sintese > /dev/null 2>&1 )
grep -E "^(Error|ERROR)" "$W"/sintese.log* | head
mkdir -p "reports_$NOME"
cp "$W"/reports/* "reports_$NOME/"
cat "reports_$NOME/area_resumo.txt"
rm -rf "$W"
