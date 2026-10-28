###############################################################
## genus_script.tcl - ecg_processor_top_spi v2 (morfologia + classificador v2)
## ------------------------------------------------------------
## Fluxo:
##   - leitura do RTL (top SPI com morfologia e classificador);
##   - area por modulo (com e sem a RAM);
##   - potencia a 100 MHz (sem estimulo, como antes) e a 1 MHz com a
##     atividade real gravada pelo potencia_tb (atividade.tcf).
##
## Estrutura esperada (pasta de trabalho do Genus):
##   ./LIB/slow_vdd1v0_basicCells.lib
##   ./RTL/*.v                     (os .v de rtl/, sem os *_tb.v)
##   ./constraints/constraints_top.sdc
##   ./atividade.tcf               (opcional; gerado por potencia_tb + tcf.tcl)
## Rodar: genus -files genus_script.tcl -log sintese.log
## Biblioteca alternativa: genus -execute "set LIB_NOME tutorial.lib" -files ...
###############################################################

if {![info exists LIB_NOME]} { set LIB_NOME slow_vdd1v0_basicCells.lib }

set_db init_lib_search_path ./LIB/
set_db init_hdl_search_path ./RTL/
read_libs $LIB_NOME

file mkdir reports outputs

read_hdl ecg_processor_top_spi.v
read_hdl spi_slave.v
read_hdl arritmia_classifier_v2.v
read_hdl classificador_arvore_v2.v
read_hdl morfologia.v
read_hdl div_serial.v
read_hdl ecg_processor_top.v
read_hdl fsm.v
read_hdl datapath.v
read_hdl filter.v
read_hdl derivator.v
read_hdl integrator.v
read_hdl peak_detector.v
read_hdl ula.v
read_hdl ram_module.v

elaborate ecg_processor_top_spi
check_design -unresolved

read_sdc ./constraints/constraints_top.sdc

## preserva a hierarquia (area por bloco)
set_db auto_ungroup none

set_db syn_generic_effort medium
set_db syn_map_effort     medium
set_db syn_opt_effort     medium

syn_generic
syn_map
syn_opt

## ---------------- relatorios a 100 MHz ----------------
report_timing           > reports/report_timing.rpt
report_area             > reports/report_area.rpt
report_qor              > reports/report_qor.rpt
report_gates            > reports/report_gates.rpt
report_power            > reports/report_power_100MHz.rpt
report_power -by_hierarchy -levels 4 > reports/report_power_100MHz_hier.rpt

## ---------------- area sem a RAM ----------------
set area_total [get_db current_design .area]
set area_ram 0.0
foreach inst [get_db hinsts -if {.module.name == ram_module*}] {
    set area_ram [expr {$area_ram + [get_db $inst .area]}]
}
set area_cls 0.0
foreach inst [get_db hinsts -if {.module.name == arritmia_classifier*}] {
    set area_cls [expr {$area_cls + [get_db $inst .area]}]
}
set area_morf 0.0
foreach inst [get_db hinsts -if {.module.name == morfologia*}] {
    set area_morf [expr {$area_morf + [get_db $inst .area]}]
}
set fp [open reports/area_resumo.txt w]
puts $fp [format "area total            : %.3f" $area_total]
puts $fp [format "area da RAM           : %.3f (%.1f%%)" $area_ram [expr {100.0*$area_ram/$area_total}]]
puts $fp [format "area sem a RAM        : %.3f" [expr {$area_total - $area_ram}]]
puts $fp [format "area do classificador : %.3f" $area_cls]
puts $fp [format "area da morfologia    : %.3f" $area_morf]
close $fp

## ---------------- potencia em operacao real: 1 MHz ----------------
## Mantem o netlist mapeado a 100 MHz e so' muda o clock para a analise.
create_clock -name clk -period 1000 -waveform {0 500} [get_ports "clk"]
if {[file exists ./atividade.tcf]} {
    read_tcf -tcf_instance dut ./atividade.tcf
    set origem "atividade real (potencia_tb, atividade.tcf)"
} else {
    set origem "sem estimulo (atividade padrao) - atividade.tcf nao encontrado"
}
report_power            > reports/report_power_1MHz.rpt
report_power -by_hierarchy -levels 4 > reports/report_power_1MHz_hier.rpt
set fp [open reports/potencia_origem.txt w]
puts $fp "report_power_1MHz: $origem"
close $fp

## ---------------- saidas ----------------
write_db ecg_processor_top_spi -to_file design.db
write_hdl > outputs/ecg_netlist.v
write_sdc > outputs/ecg_sdc.sdc
write_sdf -timescale ns -nonegchecks -recrem split -edges check_edge -setuphold split > outputs/delays.sdf

exit
