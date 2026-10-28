// ============================================================================
// potencia_tb.v  —  Operacao em TEMPO REAL para estimar potencia
// ----------------------------------------------------------------------------
// Alimenta o ecg_processor_top_spi como num dispositivo real:
//   - clock do sistema: CLK_NS (padrao 1 MHz; 100 kHz no fluxo de baixa potencia)
//   - uma amostra a cada 1/360 s (2.777.778 ns), enviada por SPI (padrao 100 kHz)
//   - registro do MIT-BIH lido de +DIR (padrao ../dados/verilog_mem/)
// e grava a atividade de chaveamento (TCF) do top durante a janela simulada,
// para o Genus calcular a potencia com atividade real (read_tcf).
//
// Rodar: ./sintese/sintetizar.sh ou ./sintese/sintetizar_baixa_potencia.sh;
// ou, a partir de sintese/:
//   xrun -access +r potencia_tb.v ../rtl/ecg_processor_top_spi.v ../rtl/spi_slave.v \
//     ../rtl/arritmia_classifier_v2.v ../rtl/classificador_arvore_v2.v \
//     ../rtl/morfologia.v ../rtl/div_serial.v ../rtl/ecg_processor_top.v \
//     ../rtl/datapath.v ../rtl/filter.v ../rtl/derivator.v ../rtl/integrator.v \
//     ../rtl/peak_detector.v ../rtl/ula.v ../rtl/ram_module.v ../rtl/fsm.v \
//     -input tcf.tcl +REG=100 +N=3600
//   (tcf.tcl abre o TCF, roda ate o $stop do fim, fecha o TCF e sai;
//    saida: atividade.tcf)
//
// N=3600 amostras = 10 s de ECG (~10 M ciclos de clock).
// ============================================================================
`timescale 1ns/1ps

module potencia_tb;

    // ajustaveis no xrun: -defparam potencia_tb.CLK_NS=10000 (100 kHz)
    //                     -defparam potencia_tb.SCLK_MEIO=50000 (SPI a 10 kHz)
    parameter  CLK_NS     = 1000;      // 1 MHz
    localparam AMOSTRA_NS = 2777778;   // 1/360 s
    parameter  SCLK_MEIO  = 5000;      // SPI a 100 kHz

    reg         clk, rst;
    reg         sclk, cs_n, mosi;

    wire        alert_out, done_out, spi_valid, classe_valid;
    wire [31:0] peak_value_out, ram_data_out, final_output, spi_amostra;
    wire [31:0] peak_classificado;
    wire [2:0]  classe_out;

    reg [15:0]  ecg_mem [0:649999];
    reg [1023:0] mem_path, dir_path;
    reg [255:0]  reg_name;
    integer      n_arg, idx, n_cls, n_pico;

    ecg_processor_top_spi dut (
        .clk(clk), .rst(rst),
        .sclk(sclk), .cs_n(cs_n), .mosi(mosi),
        .alert_out(alert_out), .done_out(done_out),
        .peak_value_out(peak_value_out),
        .ram_data_out(ram_data_out),
        .final_output(final_output),
        .spi_amostra(spi_amostra),
        .spi_valid(spi_valid),
        .classe_out(classe_out),
        .classe_valid(classe_valid),
        .peak_classificado(peak_classificado)
    );

    initial clk = 1'b0;
    always #(CLK_NS/2) clk = ~clk;

    always @(posedge clk) begin
        if (alert_out)    n_pico = n_pico + 1;
        if (classe_valid) n_cls  = n_cls + 1;
    end

    // envia uma amostra de 16 bits via SPI (modo 0, MSB primeiro)
    task envia_spi;
        input [15:0] valor;
        integer i;
        begin
            cs_n = 1'b0;
            #(SCLK_MEIO);
            for (i = 15; i >= 0; i = i - 1) begin
                mosi = valor[i];
                #(SCLK_MEIO) sclk = 1'b1;
                #(SCLK_MEIO) sclk = 1'b0;
            end
            #(SCLK_MEIO) cs_n = 1'b1;
        end
    endtask

    initial begin
        rst = 1'b1; sclk = 1'b0; cs_n = 1'b1; mosi = 1'b0;
        n_cls = 0; n_pico = 0;
        if (!$value$plusargs("REG=%s", reg_name)) reg_name = "100";
        if (!$value$plusargs("N=%d", n_arg))      n_arg = 3600;
        if (!$value$plusargs("DIR=%s", dir_path)) dir_path = "../dados/verilog_mem/";
        $sformat(mem_path, "%0s%0s_ecg.mem", dir_path, reg_name);
        $readmemh(mem_path, ecg_mem);

        #(5*CLK_NS) rst = 1'b0;
        for (idx = 0; idx < n_arg; idx = idx + 1) begin
            fork
                envia_spi(ecg_mem[idx]);
                #(AMOSTRA_NS);
            join
        end

        $display("============================================================");
        $display("  potencia_tb: registro %0s, %0d amostras (%0.1f s), clk %0d kHz, SPI %0d kHz",
                 reg_name, n_arg, n_arg / 360.0, 1000000 / CLK_NS, 500000 / SCLK_MEIO);
        $display("  picos detectados: %0d   batimentos classificados: %0d", n_pico, n_cls);
        $display("============================================================");
        $stop;   // volta ao tcf.tcl, que fecha o TCF e sai
    end

endmodule
