// ============================================================================
// medir_latencia_tb.v  —  mede, no RTL, ciclos de cada etapa por batimento
// ----------------------------------------------------------------------------
// Mesmo estimulo do classificar_v2_tb (amostras por SPI) e monitores sobre os
// estados internos:
//   morfologia : ciclos de CALCULO por pico (varredura, largura, segmento,
//                divisoes; exclui as esperas por amostras e pelo rr_ratio)
//                e ciclos totais entre o pedido e o resultado
//   classificador: ciclos da classificacao (novo pico -> classe_valid, sem
//                a espera pela morfologia) e do pre-calculo (7 divisoes)
//   latencia total: novo pico (deteccao i+1) -> classe_valid do batimento i
// Rodar (a partir da raiz do repositorio; ou ./sim.sh latencia 233):
//   xrun rtl/medir_latencia_tb.v rtl/<demais .v> +REG=233 +N=200000
// ============================================================================
`timescale 1ns/1ps

module medir_latencia_tb;

    reg         clk, rst;
    reg         sclk, cs_n, mosi;
    wire        alert_out, done_out, spi_valid, classe_valid;
    wire [31:0] peak_value_out, ram_data_out, final_output, spi_amostra, peak_classificado;
    wire [2:0]  classe_out;

    reg [15:0]   ecg_mem_raw [0:649999];
    integer      mem_idx, n_arg;
    reg [1023:0] dir_path, mem_path;
    reg [255:0]  reg_name;

    ecg_processor_top_spi dut (
        .clk(clk), .rst(rst), .sclk(sclk), .cs_n(cs_n), .mosi(mosi),
        .alert_out(alert_out), .done_out(done_out),
        .peak_value_out(peak_value_out), .ram_data_out(ram_data_out),
        .final_output(final_output), .spi_amostra(spi_amostra), .spi_valid(spi_valid),
        .classe_out(classe_out), .classe_valid(classe_valid), .peak_classificado(peak_classificado)
    );

    always #5 clk = ~clk;

    // ---------------- monitores ----------------
    integer ciclo = 0;
    always @(posedge clk) ciclo = ciclo + 1;

    // morfologia: estados de calculo (exclui IDLE=0, ESP1=1, ESP2=3, PRE=6)
    wire [3:0] mst = dut.i_morf.st;
    wire morf_calc = !(mst == 4'd0 || mst == 4'd1 || mst == 4'd3 || mst == 4'd6);
    integer m_calc = 0, m_calc_max = 0, m_calc_sum = 0, m_n = 0;
    integer m_ini = 0, m_tot_max = 0, m_tot_sum = 0;
    reg [3:0] mst_ant = 0;
    always @(posedge clk) if (!rst) begin
        if (mst_ant == 4'd0 && mst == 4'd1) begin m_ini = ciclo; m_calc = 0; end
        if (morf_calc) m_calc = m_calc + 1;
        if (mst == 4'd14) begin                       // S_FIM
            m_n = m_n + 1;
            m_calc_sum = m_calc_sum + m_calc;
            if (m_calc > m_calc_max) m_calc_max = m_calc;
            m_tot_sum = m_tot_sum + (ciclo - m_ini);
            if (ciclo - m_ini > m_tot_max) m_tot_max = ciclo - m_ini;
        end
        mst_ant = mst;
    end

    // classificador: classificacao (C_N1..C_CLS = 2..6) e pre-calculo (8..22)
    wire [4:0] cst = dut.i_cls.st;
    integer c_cls = 0, c_cls_max = 0, c_pre = 0, c_pre_max = 0, c_pre_sum = 0, c_n = 0, p_n = 0;
    integer t_pico = 0, lat_max = 0, lat_sum = 0, lat_n = 0;
    reg [4:0] cst_ant = 0;
    always @(posedge clk) if (!rst) begin
        if (dut.new_peak) t_pico = ciclo;
        if (cst >= 5'd2 && cst <= 5'd6) c_cls = c_cls + 1;
        if (cst >= 5'd8 && cst <= 5'd22) c_pre = c_pre + 1;
        if (cst == 5'd6) begin                        // C_CLS
            c_n = c_n + 1;
            if (c_cls > c_cls_max) c_cls_max = c_cls;
            c_cls = 0;
        end
        if (cst == 5'd22) begin                       // P_FIM
            p_n = p_n + 1;
            c_pre_sum = c_pre_sum + c_pre;
            if (c_pre > c_pre_max) c_pre_max = c_pre;
            c_pre = 0;
        end
        if (classe_valid) begin
            lat_n = lat_n + 1;
            lat_sum = lat_sum + (ciclo - t_pico);
            if (ciclo - t_pico > lat_max) lat_max = ciclo - t_pico;
        end
        cst_ant = cst;
    end

    // intervalo entre amostras aceitas (ciclos)
    integer t_am = 0, d_am_min = 1000000, n_am = 0;
    always @(posedge clk) if (!rst && dut.amostra_valida && dut.sys_data_ready) begin
        if (n_am > 0 && ciclo - t_am < d_am_min) d_am_min = ciclo - t_am;
        t_am = ciclo; n_am = n_am + 1;
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
        if (!$value$plusargs("REG=%s", reg_name)) reg_name = "233";
        if (!$value$plusargs("DIR=%s", dir_path)) dir_path = "dados/verilog_mem/";
        if (!$value$plusargs("N=%d", n_arg))      n_arg = 200000;
        $sformat(mem_path, "%0s%0s_ecg.mem", dir_path, reg_name);
        $readmemh(mem_path, ecg_mem_raw);
        #20 rst = 0;
        #20;
        for (mem_idx = 0; mem_idx < n_arg; mem_idx = mem_idx + 1)
            envia_spi(ecg_mem_raw[mem_idx]);
        repeat (2000) @(posedge clk);
        $display("============================================================");
        $display(" LATENCIA (ciclos de relogio) - registro %0s, %0d amostras", reg_name, n_arg);
        $display("  intervalo minimo entre amostras aceitas : %0d ciclos", d_am_min);
        $display("  morfologia, calculo por pico : media %0d  max %0d  (%0d picos)", m_calc_sum / m_n, m_calc_max, m_n);
        $display("  morfologia, pedido->resultado: media %0d  max %0d", m_tot_sum / m_n, m_tot_max);
        $display("  classificador, pre-calculo   : media %0d  max %0d  (%0d)", c_pre_sum / p_n, c_pre_max, p_n);
        $display("  classificador, classificacao : max %0d  (%0d batimentos)", c_cls_max, c_n);
        $display("  novo pico -> classe_valid    : media %0d  max %0d", lat_sum / lat_n, lat_max);
        $display("============================================================");
        $finish;
    end

endmodule
