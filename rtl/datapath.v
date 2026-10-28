// Datapath - 32 bits, sem pipeline
// Cada módulo só opera quando seu sinal _en estiver ativo (FSM controla)
// Registrador de entrada captura spi_data_in no ciclo READ_DATA (read_en)
// v2: a RAM guarda a DERIVADA COM SINAL de cada amostra (buffer circular das
//     ultimas 256 amostras) e tem uma 2a porta de leitura para a morfologia.
module datapath (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] spi_data_in,

    // Sinais de controle da FSM
    input  wire        read_en,          // captura spi_data_in no estado READ_DATA
    input  wire        filter_en,
    input  wire        derivator_en,
    input  wire        integrator_en,
    input  wire        peak_detector_en,
    input  wire [2:0]  ula_op_code_in,
    input  wire        ram_we,
    input  wire [7:0]  ram_addr_in,

    // Saídas para a FSM
    output wire        peak_detected_out,
    output wire [31:0] peak_value_out,
    output wire [31:0] ram_data_out,
    output wire [31:0] datapath_output,

    // v2: leitura da RAM pelo motor de morfologia
    input  wire [7:0]  ram_rd_addr,
    output wire [31:0] ram_rd_data
);

    // Registrador de entrada: trava o dado quando read_en=1
    reg [31:0] sample_reg;
    always @(posedge clk or posedge rst) begin
        if (rst) sample_reg <= 32'd0;
        else if (read_en) sample_reg <= spi_data_in;
    end

    wire [31:0] filtered_data;
    wire [31:0] derived_data;
    wire [31:0] deriv_signed;     // v2
    wire [31:0] integrated_data;
    wire [31:0] ula_result;

    filter i_filter (
        .clk(clk), .rst(rst),
        .en(filter_en),
        .data_in(sample_reg),       // usa dado registrado, não o wire direto
        .data_out(filtered_data)
    );

    derivator i_derivator (
        .clk(clk), .rst(rst),
        .en(derivator_en),
        .data_in(filtered_data),
        .data_out(derived_data),
        .deriv_out(deriv_signed)
    );

    integrator i_integrator (
        .clk(clk), .rst(rst),
        .en(integrator_en),
        .data_in(derived_data),
        .data_out(integrated_data)
    );

    peak_detector i_peak_detector (
        .clk(clk), .rst(rst),
        .en(peak_detector_en),
        .data_in(integrated_data),
        .peak_detected(peak_detected_out),
        .peak_value(peak_value_out)
    );

    ula i_ula (
        .a(integrated_data),
        .b(peak_value_out),
        .op_code(ula_op_code_in),
        .result(ula_result)
    );

    ram_module i_ram (
        .clk(clk), .rst(rst),
        .we(ram_we),
        .addr(ram_addr_in),
        .data_in(deriv_signed),     // v2: derivada com sinal
        .data_out(ram_data_out),
        .rd_addr(ram_rd_addr),
        .rd_data(ram_rd_data)
    );

    assign datapath_output = ula_result;

endmodule
