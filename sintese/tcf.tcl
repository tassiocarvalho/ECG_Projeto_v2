# Grava a atividade de chaveamento do DUT (Xcelium) -> atividade.tcf
dumptcf -scope potencia_tb.dut -output atividade.tcf -overwrite
run
dumptcf -end
exit
