// RAM 256 posições da derivada com sinal (v2: + porta de leitura para a morfologia)
//
// Largura: a derivada d = 2x0 + x1 - x3 - 2x4 é calculada sobre a média de 3
// amostras de 16 bits (0..65535), logo |d| <= 3*65535 = 196605 < 2^18 e cabe
// em DW = 19 bits com sinal. Guarda-se só esses 19 bits e a leitura estende o
// sinal para 32: o valor lido é idêntico ao da RAM de 32 bits.
// Sem reset: a morfologia só lê posições já escritas (amostras com índice
// negativo são forçadas a zero em morfologia.v), então o conteúdo inicial não
// afeta a classificação; dispensar o reset reduz área e fuga.
module ram_module #(
    parameter DW = 19
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        we,
    input  wire [7:0]  addr,
    input  wire [31:0] data_in,
    output wire [31:0] data_out,
    // v2: 2a porta de leitura (assincrona), usada pelo motor de morfologia
    input  wire [7:0]  rd_addr,
    output wire [31:0] rd_data
);

    reg [DW-1:0] mem [255:0];

    wire [DW-1:0] q_a = mem[addr];
    wire [DW-1:0] q_b = mem[rd_addr];
    assign data_out = {{(32-DW){q_a[DW-1]}}, q_a};
    assign rd_data  = {{(32-DW){q_b[DW-1]}}, q_b};

    always @(posedge clk) begin
        if (we)
            mem[addr] <= data_in[DW-1:0];
    end

`ifndef SYNTHESIS
    // a faixa da derivada garante que nada se perde ao guardar DW bits
    always @(posedge clk) begin
        if (!rst && we && ($signed(data_in) > $signed((32'sd1 <<< (DW-1)) - 1) ||
                           $signed(data_in) < -$signed(32'sd1 <<< (DW-1))))
            $display("ERRO ram_module: derivada %0d nao cabe em %0d bits", $signed(data_in), DW);
    end
`endif

endmodule
