###############################################################
## genus_baixa_potencia.tcl - ecg_processor_top_spi v2, fluxo de baixa potencia
## ------------------------------------------------------------
## Diferencas para genus_script.tcl (que fica como referencia):
##   - clock gating inserido pela ferramenta (lp_insert_clock_gating);
##   - restricao de mapeamento ajustavel (PERIODO_SINT), folgada para o
##     clock de operacao, o que evita celulas grandes (menos area e fuga);
##   - potencia no clock de operacao (PERIODO_OP) com a atividade real
##     gravada pelo potencia_tb rodando nesse mesmo clock (atividade.tcf).
##
## Variaveis (genus -execute "set VAR valor" -files ...):
##   LIB_NOME      arquivo .lib em ./LIB/
##   PERIODO_SINT  periodo usado no mapeamento, ns      (padrao 100 = 10 MHz)
##   PERIODO_OP    periodo de operacao, ns              (padrao 10000 = 100 kHz)
## Estrutura esperada: ./LIB/, ./RTL/*.v, ./constraints/constraints_top.sdc,
##                     ./atividade.tcf
###############################################################

if {![info exists LIB_NOME]}     { set LIB_NOME slow_vdd1v0_basicCells.lib }
if {![info exists PERIODO_SINT]} { set PERIODO_SINT 100 }
if {![info exists PERIODO_OP]}   { set PERIODO_OP 10000 }

set_db init_lib_search_path ./LIB/
set_db init_hdl_search_path ./RTL/
read_libs $LIB_NOME
## celulas especiais (isolamento/retencao de dominios de energia, sondas) nao
## entram no mapeamento, como nos fluxos abertos de referencia (OpenLane)
foreach padrao {*lpflow* *probe*} {
    set cels [get_db lib_cells $padrao]
    if {[llength $cels]} { set_db $cels .dont_use true }
}

file mkdir reports outputs

foreach f {ecg_processor_top_spi spi_slave arritmia_classifier_v2 classificador_arvore_v2
           morfologia div_serial ecg_processor_top fsm datapath filter derivator
           integrator peak_detector ula ram_module} {
    read_hdl $f.v
}

elaborate ecg_processor_top_spi
check_design -unresolved

read_sdc ./constraints/constraints_top.sdc
create_clock -name clk -period $PERIODO_SINT -waveform [list 0 [expr {$PERIODO_SINT / 2.0}]] [get_ports "clk"]

set_db auto_ungroup none
set_db lp_insert_clock_gating true

set_db syn_generic_effort medium
set_db syn_map_effort     medium
set_db syn_opt_effort     medium

syn_generic
syn_map
syn_opt

## ---------------- relatorios de implementacao ----------------
report_timing        > reports/report_timing.rpt
report_area          > reports/report_area.rpt
report_qor           > reports/report_qor.rpt
report_gates         > reports/report_gates.rpt
report_clock_gating  > reports/report_clock_gating.rpt

set area_total [get_db current_design .area]
set areas {}
foreach {rot padrao} {ram ram_module* cls arritmia_classifier* morf morfologia*} {
    set a 0.0
    foreach inst [get_db hinsts -if ".module.name == $padrao"] {
        set a [expr {$a + [get_db $inst .area]}]
    }
    dict set areas $rot $a
}
set fp [open reports/area_resumo.txt w]
puts $fp [format "area total            : %.3f" $area_total]
puts $fp [format "area da RAM           : %.3f (%.1f%%)" [dict get $areas ram] [expr {100.0 * [dict get $areas ram] / $area_total}]]
puts $fp [format "area sem a RAM        : %.3f" [expr {$area_total - [dict get $areas ram]}]]
puts $fp [format "area do classificador : %.3f" [dict get $areas cls]]
puts $fp [format "area da morfologia    : %.3f" [dict get $areas morf]]
puts $fp [format "periodo de mapeamento : %s ns" $PERIODO_SINT]
close $fp

## ---------------- potencia no clock de operacao ----------------
create_clock -name clk -period $PERIODO_OP -waveform [list 0 [expr {$PERIODO_OP / 2.0}]] [get_ports "clk"]
if {[file exists ./atividade.tcf]} {
    read_tcf -tcf_instance dut ./atividade.tcf
    set origem "atividade real (potencia_tb, atividade.tcf)"
} else {
    set origem "sem estimulo (atividade padrao) - atividade.tcf nao encontrado"
}
report_power                         > reports/report_power_op.rpt
report_power -by_hierarchy -levels 4 > reports/report_power_op_hier.rpt
set fp [open reports/potencia_origem.txt w]
puts $fp "report_power_op: periodo $PERIODO_OP ns, $origem"
close $fp

write_hdl > outputs/ecg_netlist.v
exit
