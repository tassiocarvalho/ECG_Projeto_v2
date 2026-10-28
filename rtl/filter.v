// Filtro - Média móvel de 3 pontos, 32 bits, sem pipeline
// Opera apenas quando filter_en=1 (controlado pela FSM)
//
// MIGRACAO 8->16 BITS: este modulo NAO muda. O datapath ja' opera em 32 bits
// internamente; a unica diferenca e' que data_in agora carrega uma amostra de
// 16 bits (0..65535) em vez de 8 bits (0..255). A aritmetica e' identica.
module filter (
    input  wire        clk,
    input  wire        rst,
    input  wire        en,
    input  wire [31:0] data_in,
    output reg  [31:0] data_out
);

    reg [31:0] reg0, reg1, reg2;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            reg0     <= 32'd0;
            reg1     <= 32'd0;
            reg2     <= 32'd0;
            data_out <= 32'd0;
        end else if (en) begin
            reg2     <= reg1;
            reg1     <= reg0;
            reg0     <= data_in;
            data_out <= (reg0 + reg1 + reg2) / 3;
        end
    end

endmodule
