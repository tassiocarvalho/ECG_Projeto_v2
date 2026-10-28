#!/bin/bash
# =============================================================================
# sintetizar_baixa_potencia.sh  —  atividade no clock de operacao + Genus (CG)
# -----------------------------------------------------------------------------
# 1) potencia_tb com clock CLK_NS e SPI de meio periodo SCLK_MEIO (10 s do
#    registro 100) -> atividade.tcf numa pasta temporaria
# 2) genus_baixa_potencia.tcl com a biblioteca LIB -> reports_<NOME>/
# Uso (a partir de sintese/):
#   LIB=lib_sky130/sky130_fd_sc_hd__tt_025C_1v80.lib NOME=sky130_cg ./sintetizar_baixa_potencia.sh
# Variaveis: CLK_NS (10000 = 100 kHz), SCLK_MEIO (50000 = SPI 10 kHz), SCRIPT,
#            PERIODO_SINT (100 ns), MEM (pasta dos .mem)
# =============================================================================
[ -n "$LIB" ] && LIB=$(readlink -f "$LIB")   # caminho absoluto antes do cd
cd "$(dirname "$0")" || exit 1
[ -f "$LIB" ] || { echo "defina LIB=<arquivo .lib>"; exit 1; }
NOME=${NOME:-baixa_potencia}
REG=${REG:-100}                # registro usado para a atividade (10 s)
CLK_NS=${CLK_NS:-10000}
SCLK_MEIO=${SCLK_MEIO:-50000}
PERIODO_SINT=${PERIODO_SINT:-100}
SCRIPT=${SCRIPT:-genus_baixa_potencia.tcl}   # ou genus_script.tcl (fluxo original, 100 MHz)
MEM=${MEM:-$(cd ../dados/verilog_mem 2>/dev/null && pwd)/}
RTL="ecg_processor_top_spi spi_slave arritmia_classifier_v2 classificador_arvore_v2 morfologia
     div_serial ecg_processor_top fsm datapath filter derivator integrator peak_detector ula ram_module"
AQUI=$(pwd)
W=$(mktemp -d)
mkdir -p "$W/LIB" "$W/RTL" "$W/constraints" "$W/xc"

echo "=== 1) atividade (registro $REG, 10 s, clk $((1000000 / CLK_NS)) kHz, SPI $((500000 / SCLK_MEIO)) kHz)"
FL=""; for f in $RTL; do FL="$FL $AQUI/../rtl/$f.v"; done
( cd "$W" && xrun -q -access +r -xmlibdirpath "$W/xc" -l "$W/xc/xrun.log" "$AQUI/potencia_tb.v" $FL \
      -defparam potencia_tb.CLK_NS=$CLK_NS -defparam potencia_tb.SCLK_MEIO=$SCLK_MEIO \
      -input "$AQUI/tcf.tcl" +REG=$REG +N=3600 +DIR=$MEM > /dev/null )
grep -E 'potencia_tb|picos|\*E|\*F|ERRO' "$W/xc/xrun.log" | head -6

echo "=== 2) Genus ($(basename "$LIB"), $SCRIPT)"
cp "$LIB" "$W/LIB/"
for f in $RTL; do cp ../rtl/$f.v "$W/RTL/"; done
cp constraints_top.sdc "$W/constraints/"
cp "$SCRIPT" "$W/"
( cd "$W" && genus -no_gui -execute "set LIB_NOME $(basename "$LIB"); set PERIODO_SINT $PERIODO_SINT; set PERIODO_OP $CLK_NS" \
      -files "$SCRIPT" -log sintese > /dev/null 2>&1 )
grep -E "^(Error|ERROR)" "$W"/sintese.log* | head
mkdir -p "reports_$NOME"
cp "$W"/reports/* "reports_$NOME/"
cp "$W/atividade.tcf" "reports_$NOME/atividade.tcf"
cp "$W/sintese.log" "reports_$NOME/genus.log"
cat "reports_$NOME/area_resumo.txt"
rm -rf "$W"
