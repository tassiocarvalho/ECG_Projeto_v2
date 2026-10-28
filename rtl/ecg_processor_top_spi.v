// ============================================================================
// ecg_processor_top_spi.v  —  Sistema v2 completo (escopo da sintese)
// ----------------------------------------------------------------------------
//   SPI -> registrador de fronteira -> ecg_processor_top (Pan-Tompkins + FSM;
//   a RAM guarda a derivada com sinal das ultimas 256 amostras)
//   -> captura do pico -> morfologia (le a RAM) + arritmia_classifier_v2
//
// Contadores:
//   n_amostras : amostras aceitas pelo nucleo (valid && ready). No alerta da
//                amostra k vale k+1 = indice do pico (convencao do modelo).
//   n_grav     : amostras cuja derivada ja' foi gravada na RAM.
// ============================================================================
module ecg_processor_top_spi (
    input  wire        clk,
    input  wire        rst,

    // ---- entrada SPI (serial) ----
    input  wire        sclk,
    input  wire        cs_n,
    input  wire        mosi,

    // ---- saidas do nucleo ----
    output wire        alert_out,
    output wire        done_out,
    output wire [31:0] peak_value_out,
    output wire [31:0] ram_data_out,
    output wire [31:0] final_output,

    // ---- observabilidade do SPI ----
    output wire [31:0] spi_amostra,
    output wire        spi_valid,

    // ---- classificacao (AAMI: 0=N 1=SVEB 2=VEB 3=F 4=Q) ----
    output wire [2:0]  classe_out,
    output wire        classe_valid,
    output wire [31:0] peak_classificado
);

    // ---- SPI ----
    wire [31:0] spi_data;
    wire        spi_data_valid;
    spi_slave i_spi (
        .clk(clk), .rst(rst),
        .sclk(sclk), .cs_n(cs_n), .mosi(mosi),
        .data_out(spi_data), .data_valid(spi_data_valid)
    );
    assign spi_amostra = spi_data;
    assign spi_valid   = spi_data_valid;

    // ---- registrador de fronteira ----
    reg  [31:0] amostra_reg;
    reg         amostra_valida;
    wire        sys_data_ready;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            amostra_reg <= 32'd0; amostra_valida <= 1'b0;
        end else begin
            if (spi_data_valid) begin
                amostra_reg <= spi_data; amostra_valida <= 1'b1;
            end else if (amostra_valida && sys_data_ready) begin
                amostra_valida <= 1'b0;
            end
        end
    end

    // ---- nucleo ----
    wire [7:0]  ram_rd_addr;
    wire [31:0] ram_rd_data;
    wire        amostra_gravada;
    ecg_processor_top i_core (
        .clk(clk), .rst(rst),
        .data_valid(amostra_valida), .data_ready(sys_data_ready),
        .spi_data_in(amostra_reg),
        .alert_out(alert_out), .done_out(done_out),
        .peak_value_out(peak_value_out),
        .ram_data_out(ram_data_out), .final_output(final_output),
        .ram_rd_addr(ram_rd_addr), .ram_rd_data(ram_rd_data),
        .amostra_gravada(amostra_gravada)
    );

    // ---- contadores ----
    reg [31:0] n_amostras, n_grav;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            n_amostras <= 32'd0; n_grav <= 32'd0;
        end else begin
            if (amostra_valida && sys_data_ready) n_amostras <= n_amostras + 1'b1;
            if (amostra_gravada)                  n_grav     <= n_grav + 1'b1;
        end
    end

    // ---- captura do pico ----
    reg        new_peak;
    reg [31:0] peak_index, peak_valor;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            new_peak <= 1'b0; peak_index <= 32'd0; peak_valor <= 32'd0;
        end else begin
            new_peak <= alert_out;
            if (alert_out) begin
                peak_index <= n_amostras;
                peak_valor <= peak_value_out;
            end
        end
    end

    // ---- morfologia ----
    wire        pre_ok;
    wire [31:0] pre_k, pre_rr_ratio;
    wire        morf_valid;
    wire [31:0] morf_k, morf_dw, morf_sad, morf_dpol;
    morfologia i_morf (
        .clk(clk), .rst(rst),
        .pico_novo(new_peak), .pico_k(peak_index - 1'b1), .n_grav(n_grav),
        .rd_addr(ram_rd_addr), .rd_data(ram_rd_data),
        .pre_ok(pre_ok), .pre_k(pre_k), .pre_rr_ratio(pre_rr_ratio),
        .morf_valid(morf_valid), .morf_k(morf_k),
        .morf_dw(morf_dw), .morf_sad(morf_sad), .morf_dpol(morf_dpol)
    );

    // ---- classificador ----
    arritmia_classifier_v2 i_cls (
        .clk(clk), .rst(rst),
        .new_peak(new_peak), .peak_index(peak_index), .peak_value(peak_valor),
        .morf_valid(morf_valid), .morf_k(morf_k),
        .morf_dw(morf_dw), .morf_sad(morf_sad), .morf_dpol(morf_dpol),
        .pre_ok(pre_ok), .pre_k(pre_k), .pre_rr_ratio(pre_rr_ratio),
        .classe_out(classe_out), .peak_classificado(peak_classificado),
        .classe_valid(classe_valid)
    );

endmodule
