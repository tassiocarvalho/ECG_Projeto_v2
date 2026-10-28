// ============================================================================
// div_serial_tb.v  —  teste do divisor serial (48/32 bits, 1 bit por ciclo)
// ----------------------------------------------------------------------------
// Compara o quociente com a divisao exata (divisor 0 tratado como 1) em:
//   - casos-limite: dividendo 0 e maximo, divisor 0, 1, 2, maximo, dividendo
//     menor, igual e maior que o divisor, potencias de 2;
//   - 20000 pares aleatorios (larguras aleatorias, para cobrir quocientes
//     pequenos e grandes).
// Confere tambem que a latencia (start -> done) e' constante.
// Rodar: xrun rtl/div_serial_tb.v rtl/div_serial.v
// ============================================================================
`timescale 1ns/1ps

module div_serial_tb;

    localparam DW = 48, SW = 32, N_ALEAT = 20000;

    reg           clk = 0, rst = 1, start = 0;
    reg  [DW-1:0] dividendo;
    reg  [SW-1:0] divisor;
    wire [DW-1:0] quociente;
    wire          done, busy;

    div_serial #(.DW(DW), .SW(SW)) dut (
        .clk(clk), .rst(rst), .start(start), .dividendo(dividendo), .divisor(divisor),
        .quociente(quociente), .done(done), .busy(busy));

    always #5 clk = ~clk;

    integer n_testes = 0, n_erros = 0, ciclos, lat_erros = 0, lat_ref = -1, i;
    reg [DW-1:0] esperado;
    reg [63:0]   a64, b64;

    task testa;
        input [DW-1:0] a;
        input [SW-1:0] b;
        begin
            @(negedge clk);
            dividendo = a; divisor = b; start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            ciclos = 1;
            while (!done) begin @(negedge clk); ciclos = ciclos + 1; end
            esperado = a / ((b == 0) ? 1 : b);
            n_testes = n_testes + 1;
            if (quociente !== esperado) begin
                n_erros = n_erros + 1;
                if (n_erros <= 10)
                    $display("ERRO: %0d / %0d -> %0d (esperado %0d)", a, b, quociente, esperado);
            end
            if (lat_ref < 0) lat_ref = ciclos;
            else if (ciclos != lat_ref) lat_erros = lat_erros + 1;
        end
    endtask

    function [63:0] aleat64;
        input integer bits;
        reg [63:0] v;
        begin
            v = {$random, $random};
            aleat64 = (bits >= 64) ? v : (v & ((64'd1 << bits) - 1));
        end
    endfunction

    initial begin
        dividendo = 0; divisor = 0;
        repeat (3) @(negedge clk);
        rst = 0;
        // casos-limite
        testa(0, 0);                  testa(0, 1);              testa(0, {SW{1'b1}});
        testa({DW{1'b1}}, 0);         testa({DW{1'b1}}, 1);     testa({DW{1'b1}}, 2);
        testa({DW{1'b1}}, {SW{1'b1}});
        testa(1, 0);                  testa(1, 1);              testa(1, 2);
        testa(7, 7);                  testa(6, 7);              testa(8, 7);
        testa(256, 3);                testa(48'd196605 << 8, 1); testa(48'd196605 << 8, 196605);
        testa({1'b1, {(DW-1){1'b0}}}, {1'b1, {(SW-1){1'b0}}});
        testa({DW{1'b1}}, {1'b1, {(SW-1){1'b0}}});
        for (i = 0; i < SW; i = i + 1) testa({DW{1'b1}}, 32'd1 << i);
        // aleatorios com larguras aleatorias
        for (i = 0; i < N_ALEAT; i = i + 1) begin
            a64 = aleat64(1 + ({$random} % DW));
            b64 = aleat64({$random} % (SW + 1));
            testa(a64[DW-1:0], b64[SW-1:0]);
        end
        $display("============================================================");
        $display(" div_serial: %0d testes, %0d erros de quociente; latencia %0d ciclos (start -> done), %0d variacoes",
                 n_testes, n_erros, lat_ref, lat_erros);
        $display("============================================================");
        $finish;
    end

endmodule
