// Derivador Pan-Tompkins, 32 bits, sem pipeline (v2: + saida com sinal)
// Opera apenas quando derivator_en=1 (controlado pela FSM)
// NOTA: sem normalização (não divide por 8) para preservar amplitude
// em sinais ECG de 8 bits expandidos para 32 bits
module derivator (
    input  wire        clk,
    input  wire        rst,
    input  wire        en,
    input  wire [31:0] data_in,
    output reg  [31:0] data_out,
    output reg  [31:0] deriv_out     // v2: derivada COM SINAL (complemento de 2)
);

    reg signed [31:0] x0, x1, x2, x3, x4;
    reg signed [33:0] deriv;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            x0 <= 32'd0; x1 <= 32'd0; x2 <= 32'd0;
            x3 <= 32'd0; x4 <= 32'd0;
            data_out <= 32'd0;
            deriv_out <= 32'd0;
        end else if (en) begin
            x4 <= x3; x3 <= x2; x2 <= x1; x1 <= x0;
            x0 <= $signed(data_in);

            // Fórmula Pan-Tompkins sem normalização final
            // (2x0 + x1 - x3 - 2x4) — valor absoluto
            deriv = (2 * $signed(x0)) + $signed(x1) - $signed(x3) - (2 * $signed(x4));

            // v2: |deriv| < 2^19 (entrada de 16 bits), cabe em 32 bits com sinal
            deriv_out <= deriv[31:0];

            if (deriv < 0)
                data_out <= -deriv;
            else
                data_out <= deriv;
        end
    end

endmodule
