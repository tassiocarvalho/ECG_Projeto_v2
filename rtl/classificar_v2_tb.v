// ============================================================================
// classificar_v2_tb.v  —  Classificacao v2 completa com entrada por SPI
// ----------------------------------------------------------------------------
// Envia as amostras de um registro pelo SPI ao ecg_processor_top_spi (v2),
// conta as classes e grava (+DUMP=arquivo) "amostra classe" de cada batimento
// classificado, para comparar com o golden model (python/validar_v2.py).
//
// Rodar (Xcelium, a partir da raiz do repositorio; ou ./sim.sh 100):
//   xrun rtl/classificar_v2_tb.v rtl/ecg_processor_top_spi.v rtl/spi_slave.v \
//     rtl/ecg_processor_top.v rtl/datapath.v rtl/filter.v rtl/derivator.v \
//     rtl/integrator.v rtl/peak_detector.v rtl/ula.v rtl/ram_module.v rtl/fsm.v \
//     rtl/morfologia.v rtl/arritmia_classifier_v2.v rtl/classificador_arvore_v2.v \
//     rtl/div_serial.v +REG=100 +N=650000 +DUMP=validacao/dumps/100_rtl.txt
// (+DIR=pasta dos .mem; padrao dados/verilog_mem/)
// ============================================================================
`timescale 1ns/1ps

module classificar_v2_tb;

    reg         clk, rst;
    reg         sclk, cs_n, mosi;
    wire        alert_out, done_out, spi_valid, classe_valid;
    wire [31:0] peak_value_out, ram_data_out, final_output, spi_amostra, peak_classificado;
    wire [2:0]  classe_out;

    reg [15:0]   ecg_mem_raw [0:649999];
    integer      mem_idx, n_arg, fd_dump;
    integer      n_N, n_SVEB, n_VEB, n_F, n_Q;
    reg [1023:0] dir_path, mem_path, dump_path;
    reg [255:0]  reg_name;

    ecg_processor_top_spi dut (
        .clk(clk), .rst(rst),
        .sclk(sclk), .cs_n(cs_n), .mosi(mosi),
        .alert_out(alert_out), .done_out(done_out),
        .peak_value_out(peak_value_out), .ram_data_out(ram_data_out),
        .final_output(final_output),
        .spi_amostra(spi_amostra), .spi_valid(spi_valid),
        .classe_out(classe_out), .classe_valid(classe_valid),
        .peak_classificado(peak_classificado)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (classe_valid && !rst) begin
            case (classe_out)
                3'd0: n_N = n_N + 1;
                3'd1: n_SVEB = n_SVEB + 1;
                3'd2: n_VEB = n_VEB + 1;
                3'd3: n_F = n_F + 1;
                default: n_Q = n_Q + 1;
            endcase
            if (fd_dump != 0) $fwrite(fd_dump, "%0d %0d\n", peak_classificado, classe_out);
        end
    end

    task envia_spi;
        input [15:0] valor;
        integer i;
        begin
            cs_n = 1'b0;
            #30;
            for (i = 15; i >= 0; i = i - 1) begin
                mosi = valor[i];
                #15 sclk = 1'b1;
                #15 sclk = 1'b0;
            end
            #30 cs_n = 1'b1;
            #30;
        end
    endtask

    initial begin
        clk = 0; rst = 1; sclk = 0; cs_n = 1; mosi = 0;
        n_N = 0; n_SVEB = 0; n_VEB = 0; n_F = 0; n_Q = 0; fd_dump = 0;
        if (!$value$plusargs("REG=%s", reg_name)) reg_name = "100";
        if (!$value$plusargs("DIR=%s", dir_path)) dir_path = "dados/verilog_mem/";
        if (!$value$plusargs("N=%d", n_arg))      n_arg = 650000;
        if ($value$plusargs("DUMP=%s", dump_path)) fd_dump = $fopen(dump_path, "w");
        $sformat(mem_path, "%0s%0s_ecg.mem", dir_path, reg_name);
        begin : zera
            integer z;
            for (z = 0; z < 650000; z = z + 1) ecg_mem_raw[z] = 16'd0;
        end
        $readmemh(mem_path, ecg_mem_raw);

        #20 rst = 0;
        #20;
        for (mem_idx = 0; mem_idx < n_arg; mem_idx = mem_idx + 1)
            envia_spi(ecg_mem_raw[mem_idx]);
        begin : drena
            integer dz;
            for (dz = 0; dz < 2000; dz = dz + 1) @(posedge clk);
        end

        $display("============================================================");
        $display("   CLASSIFICACAO v2 - Registro %0s (Verilog + SPI)", reg_name);
        $display("============================================================");
        $display("     N    (Normal)        : %0d", n_N);
        $display("     SVEB (Supraventric.) : %0d", n_SVEB);
        $display("     VEB  (Ventricular)   : %0d", n_VEB);
        $display("     F    (Fusion)        : %0d", n_F);
        $display("     Q    (Unknown)       : %0d", n_Q);
        $display("     TOTAL                : %0d", n_N + n_SVEB + n_VEB + n_F + n_Q);
        $display("============================================================");
        if (fd_dump != 0) $fclose(fd_dump);
        #50 $finish;
    end

endmodule
